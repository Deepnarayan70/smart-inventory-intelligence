from datetime import datetime

def get_all_products(db, user_id, search=None, category=None):
    """
    Retrieve products from MongoDB with optional search query and category filter.
    """
    query = {"user_id": user_id}
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"product_id": {"$regex": search, "$options": "i"}}
        ]
    if category:
        query["category"] = category

    products = list(db.products.find(query, {"_id": 0}).sort("product_id", 1))
    return products

def get_product_by_id(db, user_id, product_id):
    """
    Retrieve single product by product_id.
    """
    return db.products.find_one({"product_id": product_id, "user_id": user_id}, {"_id": 0})

def generate_next_product_id(db, user_id):
    """
    Auto-generate unique product ID e.g. PRD013.
    """
    last_product = db.products.find_one({"user_id": user_id}, {"_id": 0, "product_id": 1}, sort=[("product_id", -1)])
    if last_product and last_product.get("product_id", "").startswith("PRD"):
        try:
            num = int(last_product["product_id"].replace("PRD", ""))
            return f"PRD{num + 1:03d}"
        except ValueError:
            pass
    
    count = db.products.count_documents({"user_id": user_id})
    return f"PRD{count + 1:03d}"

def add_product(db, user_id, data):
    """
    Add a new product to MongoDB products collection.
    """
    p_id = data.get("product_id") or generate_next_product_id(db, user_id)
    
    product_doc = {
        "product_id": p_id,
        "name": data.get("name", "").strip(),
        "category": data.get("category", "General"),
        "current_stock": int(data.get("current_stock", 0)),
        "unit_price": float(data.get("unit_price", 0.0)),
        "expiry_date": data.get("expiry_date", ""),
        "reorder_level": int(data.get("reorder_level", 10)),
        "supplier_id": data.get("supplier_id", "SUP001"),
        "unit": data.get("unit", "Packs"),
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "user_id": user_id
    }
    
    db.products.insert_one(product_doc)
    return p_id

def update_product(db, user_id, product_id, data):
    """
    Update existing product record.
    """
    update_doc = {
        "name": data.get("name", "").strip(),
        "category": data.get("category"),
        "current_stock": int(data.get("current_stock", 0)),
        "unit_price": float(data.get("unit_price", 0.0)),
        "expiry_date": data.get("expiry_date"),
        "reorder_level": int(data.get("reorder_level", 10)),
        "supplier_id": data.get("supplier_id"),
        "unit": data.get("unit", "Packs"),
        "updated_at": datetime.now()
    }
    
    # Remove None fields
    update_doc = {k: v for k, v in update_doc.items() if v is not None}
    
    result = db.products.update_one({"product_id": product_id, "user_id": user_id}, {"$set": update_doc})
    return result.modified_count > 0 or result.matched_count > 0

def delete_product(db, user_id, product_id):
    """
    Delete a product and its associated predictions/alerts.
    """
    result = db.products.delete_one({"product_id": product_id, "user_id": user_id})
    db.predictions.delete_many({"product_id": product_id, "user_id": user_id})
    db.alerts.delete_many({"product_id": product_id, "user_id": user_id})
    return result.deleted_count > 0

def get_inventory_summary(db, user_id):
    """Compute inventory KPIs in MongoDB, keeping results scoped to one user."""
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    pipeline = [
        {"$match": {"user_id": user_id}},
        {"$addFields": {
            "_expiryDate": {"$dateFromString": {
                "dateString": {"$ifNull": ["$expiry_date", ""]},
                "onError": None,
                "onNull": None,
            }}
        }},
        {"$group": {
            "_id": None,
            "total_products": {"$sum": 1},
            "total_stock_qty": {"$sum": {"$ifNull": ["$current_stock", 0]}},
            "total_inventory_value": {"$sum": {"$multiply": [
                {"$ifNull": ["$current_stock", 0]}, {"$ifNull": ["$unit_price", 0]}
            ]}},
            "low_stock_count": {"$sum": {"$cond": [
                {"$lte": [{"$ifNull": ["$current_stock", 0]}, {"$ifNull": ["$reorder_level", 10]}]}, 1, 0
            ]}},
            "near_expiry_count": {"$sum": {"$cond": [
                {"$ne": ["$_expiryDate", None]},
                {"$cond": [
                    {"$lte": [{"$dateDiff": {"startDate": today, "endDate": "$_expiryDate", "unit": "day"}}, 3]},
                    1, 0
                ]},
                0
            ]}},
        }},
        {"$project": {"_id": 0, "total_products": 1, "total_stock_qty": 1,
                      "total_inventory_value": {"$round": ["$total_inventory_value", 2]},
                      "low_stock_count": 1, "near_expiry_count": 1}},
    ]
    summary = next(iter(db.products.aggregate(pipeline)), {})
    categories = list(db.products.distinct("category", {"user_id": user_id}))
    return {
        "total_products": int(summary.get("total_products", 0)),
        "total_stock_qty": summary.get("total_stock_qty", 0),
        "total_inventory_value": round(float(summary.get("total_inventory_value", 0)), 2),
        "low_stock_count": int(summary.get("low_stock_count", 0)),
        "near_expiry_count": int(summary.get("near_expiry_count", 0)),
        "categories": categories,
    }
