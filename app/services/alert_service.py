from datetime import datetime
from app.services.ml_service import get_predictions_with_product_details

def get_supplier_map(db):
    """
    Load suppliers dictionary indexed by supplier_id.
    """
    suppliers = list(db.suppliers.find({}, {"_id": 0}))
    return {s["supplier_id"]: s for s in suppliers}

def evaluate_stockout_risk(current_stock, reorder_level, predicted_demand_7d, lead_time_days=2):
    """
    Evaluate Stockout Risk:
    HIGH: Out of stock or current stock is less than demand expected during supplier lead time.
    MEDIUM: Stock is below reorder level or 7-day predicted demand.
    LOW: Stock is near reorder level (within 25%).
    NONE: Stock is healthy.
    """
    daily_demand = predicted_demand_7d / 7.0
    lead_time_demand = daily_demand * lead_time_days

    if current_stock <= 0:
        return "HIGH", "OUT OF STOCK: Current stock is 0 units!", lead_time_demand
    elif current_stock < lead_time_demand:
        return "HIGH", f"HIGH STOCKOUT RISK: Stock ({current_stock}) is below expected demand during lead time ({round(lead_time_demand, 1)} units over {lead_time_days} days).", lead_time_demand
    elif current_stock <= reorder_level or current_stock < predicted_demand_7d:
        return "MEDIUM", f"MODERATE STOCKOUT RISK: Stock ({current_stock}) is below reorder level ({reorder_level}) or 7-day forecast ({round(predicted_demand_7d, 1)}).", lead_time_demand
    elif current_stock <= reorder_level * 1.25:
        return "LOW", f"LOW STOCKOUT RISK: Stock ({current_stock}) is nearing reorder threshold ({reorder_level}).", lead_time_demand
    else:
        return "NONE", "Stock level is sufficient for projected demand.", lead_time_demand

def evaluate_expiry_risk(current_stock, expiry_date_str, predicted_demand_7d):
    """
    Evaluate Expiry / Waste Risk:
    Compares current stock, predicted sales rate, and days remaining until expiry.
    """
    if not expiry_date_str:
        return "NONE", "No expiry date specified.", 0, 0

    today = datetime.now()
    try:
        exp_date = datetime.strptime(expiry_date_str, "%Y-%m-%d")
    except ValueError:
        return "NONE", "Invalid expiry date format.", 0, 0

    days_remaining = (exp_date - datetime(today.year, today.month, today.day)).days
    daily_demand = max(0.1, predicted_demand_7d / 7.0)
    
    # Calculate predicted sales before expiry date
    sales_days = max(0, days_remaining)
    predicted_sales_before_expiry = sales_days * daily_demand
    expected_unsold = max(0.0, current_stock - predicted_sales_before_expiry)

    if days_remaining <= 0:
        return "HIGH", f"EXPIRED FOOD: Expired {abs(days_remaining)} days ago! Immediate removal required.", days_remaining, current_stock
    elif days_remaining <= 3 and expected_unsold > 0:
        return "HIGH", f"HIGH WASTE RISK: Expires in {days_remaining} days! ~{round(expected_unsold, 1)} units likely to remain unsold before expiry.", days_remaining, expected_unsold
    elif days_remaining <= 5 and expected_unsold > 0:
        return "MEDIUM", f"MODERATE WASTE RISK: Expires in {days_remaining} days. ~{round(expected_unsold, 1)} units at risk of waste.", days_remaining, expected_unsold
    elif days_remaining <= 7:
        return "LOW", f"LOW WASTE RISK: Expires in {days_remaining} days; sales velocity is currently adequate.", days_remaining, expected_unsold
    else:
        return "NONE", f"Sufficient shelf life ({days_remaining} days remaining).", days_remaining, 0

def generate_recommendation(current_stock, reorder_level, predicted_demand_7d, stockout_risk, expiry_risk, expected_unsold):
    """
    Generate Actionable Inventory Recommendation.
    """
    if expiry_risk == "HIGH":
        return "DISCOUNT & PROMOTION: Apply 30-50% discount or combo deal to clear stock before expiry and prevent food waste."
    elif stockout_risk == "HIGH":
        return "RESTOCK IMMEDIATELY: Place urgent purchase order with supplier to avoid stocking out."
    elif stockout_risk == "MEDIUM":
        return "REORDER SOON: Stock is below reorder point; schedule next supplier shipment."
    elif expiry_risk == "MEDIUM":
        return "MONITOR & PROMOTE: Feature product prominently on canteen menu counter to accelerate sales."
    elif current_stock > predicted_demand_7d * 3 and current_stock > 30:
        return "REDUCE PURCHASING: Overstocked compared to 7-day demand; lower future reorder quantity."
    else:
        return "OPTIMAL STOCK: Inventory level is healthy and aligned with demand."

def evaluate_all_risks_and_alerts(db, user_id):
    """
    Run risk evaluation engine on all products and update MongoDB alerts collection.
    """
    items = get_predictions_with_product_details(db, user_id)
    suppliers = get_supplier_map(db)

    # Clear old alerts for this user
    db.alerts.delete_many({"user_id": user_id})

    risk_analysis = []
    alerts_to_insert = []

    for item in items:
        p_id = item["product_id"]
        product_doc = db.products.find_one({"product_id": p_id, "user_id": user_id}, {"_id": 0})
        if not product_doc:
            continue

        supplier_id = product_doc.get("supplier_id", "SUP001")
        supplier = suppliers.get(supplier_id, {})
        lead_time = supplier.get("lead_time_days", 2)
        expiry_date = product_doc.get("expiry_date", "")

        stockout_risk, stockout_msg, lead_demand = evaluate_stockout_risk(
            item["current_stock"], item["reorder_level"], item["predicted_demand_7d"], lead_time
        )

        expiry_risk, expiry_msg, days_rem, expected_unsold = evaluate_expiry_risk(
            item["current_stock"], expiry_date, item["predicted_demand_7d"]
        )

        rec = generate_recommendation(
            item["current_stock"], item["reorder_level"], item["predicted_demand_7d"],
            stockout_risk, expiry_risk, expected_unsold
        )

        analysis_row = {
            "product_id": p_id,
            "product_name": item["product_name"],
            "category": item["category"],
            "current_stock": item["current_stock"],
            "reorder_level": item["reorder_level"],
            "expiry_date": expiry_date,
            "days_to_expiry": days_rem,
            "predicted_demand_7d": item["predicted_demand_7d"],
            "supplier_name": supplier.get("name", "Standard Supplier"),
            "lead_time_days": lead_time,
            "stockout_risk": stockout_risk,
            "stockout_message": stockout_msg,
            "expiry_risk": expiry_risk,
            "expiry_message": expiry_msg,
            "expected_unsold": round(expected_unsold, 1),
            "recommendation": rec
        }
        risk_analysis.append(analysis_row)

        # Create Mongo alert documents if risk is HIGH or MEDIUM
        if stockout_risk in ["HIGH", "MEDIUM"]:
            alerts_to_insert.append({
                "product_id": p_id,
                "product_name": item["product_name"],
                "alert_type": "STOCKOUT_RISK",
                "risk_level": stockout_risk,
                "message": stockout_msg,
                "recommendation": rec,
                "created_at": datetime.now(),
                "user_id": user_id
            })
        if expiry_risk in ["HIGH", "MEDIUM"]:
            alerts_to_insert.append({
                "product_id": p_id,
                "product_name": item["product_name"],
                "alert_type": "EXPIRY_RISK",
                "risk_level": expiry_risk,
                "message": expiry_msg,
                "recommendation": rec,
                "created_at": datetime.now(),
                "user_id": user_id
            })

    if alerts_to_insert:
        db.alerts.insert_many(alerts_to_insert)

    return risk_analysis

def get_risk_summary(db, user_id):
    """
    Get aggregated alert counts for dashboard display.
    """
    risk_list = evaluate_all_risks_and_alerts(db, user_id)
    
    high_stockout = sum(1 for r in risk_list if r["stockout_risk"] == "HIGH")
    med_stockout = sum(1 for r in risk_list if r["stockout_risk"] == "MEDIUM")
    
    high_expiry = sum(1 for r in risk_list if r["expiry_risk"] == "HIGH")
    med_expiry = sum(1 for r in risk_list if r["expiry_risk"] == "MEDIUM")

    return {
        "stockout_high": high_stockout,
        "stockout_medium": med_stockout,
        "expiry_high": high_expiry,
        "expiry_medium": med_expiry,
        "total_alerts": high_stockout + med_stockout + high_expiry + med_expiry,
        "details": risk_list
    }
