from datetime import datetime
from app.services.inventory_service import get_product_by_id


def record_sale(db, user_id, product_id, quantity_sold, selling_price=None, sale_date=None):
    """Record a sale and atomically reserve stock for this user's product."""
    try:
        quantity_sold = int(quantity_sold)
    except (TypeError, ValueError):
        return False, "Quantity sold must be a valid whole number.", None
    if quantity_sold <= 0:
        return False, "Quantity sold must be greater than zero.", None

    product = get_product_by_id(db, user_id, product_id)
    if not product:
        return False, f"Product '{product_id}' not found.", None

    unit_price = float(selling_price) if selling_price is not None else float(product.get("unit_price", 0.0))
    if unit_price < 0:
        return False, "Selling price cannot be negative.", None
    total_amount = round(quantity_sold * unit_price, 2)
    sale_date = sale_date or datetime.now().strftime("%Y-%m-%d")

    # Conditional $inc prevents two concurrent requests from overselling stock.
    stock_update = db.products.update_one(
        {"product_id": product_id, "user_id": user_id, "current_stock": {"$gte": quantity_sold}},
        {"$inc": {"current_stock": -quantity_sold}, "$set": {"updated_at": datetime.now()}},
    )
    if stock_update.modified_count != 1:
        refreshed = get_product_by_id(db, user_id, product_id)
        if not refreshed:
            return False, f"Product '{product_id}' not found.", None
        available = refreshed.get("current_stock", 0)
        return False, f"Insufficient stock! Available: {available}, Requested: {quantity_sold}.", None

    # Preserve the existing human-readable sale ID convention.
    last_sale = db.sales.find_one(
        {"user_id": user_id}, {"_id": 0, "sale_id": 1}, sort=[("sale_id", -1)]
    )
    sale_num = 1001
    if last_sale and str(last_sale.get("sale_id", "")).startswith("SALE"):
        try:
            sale_num = int(last_sale["sale_id"].replace("SALE", "")) + 1
        except ValueError:
            pass
    sale_id = f"SALE{sale_num}"
    sale_record = {
        "sale_id": sale_id,
        "product_id": product_id,
        "product_name": product.get("name"),
        "category": product.get("category", "General"),
        "date": sale_date,
        "quantity_sold": quantity_sold,
        "selling_price": unit_price,
        "total_amount": total_amount,
        "created_at": datetime.now(),
        "user_id": user_id,
    }
    try:
        db.sales.insert_one(sale_record)
    except Exception:
        # Compensate stock if the sale document could not be written. For strict
        # cross-document atomicity, deploy MongoDB as a replica set and use a txn.
        db.products.update_one(
            {"product_id": product_id, "user_id": user_id},
            {"$inc": {"current_stock": quantity_sold}, "$set": {"updated_at": datetime.now()}},
        )
        raise

    sale_record.pop("_id", None)
    updated_product = get_product_by_id(db, user_id, product_id)
    new_stock = updated_product.get("current_stock", 0) if updated_product else max(0, product.get("current_stock", 0) - quantity_sold)
    return True, f"Sale recorded successfully! New stock for {product.get('name')}: {new_stock}.", sale_record


def get_sales_history(db, user_id, product_id=None, limit=200):
    """Get this user's sales records ordered by date descending."""
    query = {"user_id": user_id}
    if product_id:
        query["product_id"] = product_id
    return list(db.sales.find(query, {"_id": 0}).sort([("date", -1), ("created_at", -1)]).limit(limit))


def get_sales_analytics(db, user_id):
    """Calculate sales KPIs using server-side MongoDB aggregation pipelines."""
    match_user = {"$match": {"user_id": user_id}}
    totals_pipeline = [
        match_user,
        {"$group": {"_id": None,
                    "total_sales_count": {"$sum": 1},
                    "total_items_sold": {"$sum": {"$ifNull": ["$quantity_sold", 0]}},
                    "total_revenue": {"$sum": {"$ifNull": ["$total_amount", 0]}}}},
        {"$project": {"_id": 0, "total_sales_count": 1, "total_items_sold": 1, "total_revenue": {"$round": ["$total_revenue", 2]}}},
    ]
    daily_pipeline = [
        match_user,
        {"$group": {"_id": {"$ifNull": ["$date", "Unknown"]},
                    "revenue": {"$sum": {"$ifNull": ["$total_amount", 0]}},
                    "quantity": {"$sum": {"$ifNull": ["$quantity_sold", 0]}}}},
        {"$sort": {"_id": 1}},
        {"$project": {"_id": 0, "date": "$_id", "revenue": {"$round": ["$revenue", 2]}, "quantity": 1}},
    ]
    category_pipeline = [
        match_user,
        {"$group": {"_id": {"$ifNull": ["$category", "General"]},
                    "revenue": {"$sum": {"$ifNull": ["$total_amount", 0]}},
                    "quantity": {"$sum": {"$ifNull": ["$quantity_sold", 0]}}}},
        {"$sort": {"revenue": -1}},
        {"$project": {"_id": 0, "category": "$_id", "revenue": {"$round": ["$revenue", 2]}, "quantity": 1}},
    ]
    top_products_pipeline = [
        match_user,
        {"$group": {"_id": "$product_id", "name": {"$first": {"$ifNull": ["$product_name", "$product_id"]}},
                    "total_qty": {"$sum": {"$ifNull": ["$quantity_sold", 0]}},
                    "total_revenue": {"$sum": {"$ifNull": ["$total_amount", 0]}}}},
        {"$sort": {"total_qty": -1, "total_revenue": -1}},
        {"$limit": 5},
        {"$project": {"_id": 0, "product_id": "$_id", "name": 1, "total_qty": 1, "total_revenue": {"$round": ["$total_revenue", 2]}}},
    ]

    totals = next(iter(db.sales.aggregate(totals_pipeline)), {})
    return {
        "total_sales_count": int(totals.get("total_sales_count", 0)),
        "total_items_sold": int(totals.get("total_items_sold", 0)),
        "total_revenue": round(float(totals.get("total_revenue", 0)), 2),
        "daily_trends": list(db.sales.aggregate(daily_pipeline)),
        "category_sales": list(db.sales.aggregate(category_pipeline)),
        "top_selling_products": list(db.sales.aggregate(top_products_pipeline)),
    }
