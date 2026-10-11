from flask import Blueprint, jsonify, session
from app.routes.auth_routes import login_required
from app.db import get_db
from app.seed_data import seed_database
from app.services.sales_service import get_sales_analytics
from app.services.ml_service import get_predictions_with_product_details
from app.services.alert_service import evaluate_all_risks_and_alerts

api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/seed', methods=['POST'])
@login_required
def trigger_seed():
    db = get_db()
    user_id = session['user_id']
    try:
        seed_database(db, user_id)
        return jsonify({"success": True, "message": "Demo sample canteen data seeded successfully!"}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@api_bp.route('/charts/dashboard')
@login_required
def dashboard_chart_data():
    db = get_db()
    user_id = session['user_id']
    sales_analytics = get_sales_analytics(db, user_id)
    predictions = get_predictions_with_product_details(db, user_id)
    risks = evaluate_all_risks_and_alerts(db, user_id)

    # 1. Daily sales trend (last 30 days)
    trends = sales_analytics["daily_trends"][-30:]
    dates = [t["date"] for t in trends]
    revenues = [t["revenue"] for t in trends]
    quantities = [t["quantity"] for t in trends]

    # 2. Categories breakdown
    cat_sales = sales_analytics["category_sales"]
    cat_labels = [c["category"] for c in cat_sales]
    cat_revenues = [c["revenue"] for c in cat_sales]

    # 3. Product Stock vs 7-day Predicted Demand
    prod_names = [p["product_name"] for p in predictions[:10]]
    current_stocks = [p["current_stock"] for p in predictions[:10]]
    predicted_demands = [p["predicted_demand_7d"] for p in predictions[:10]]

    # 4. Risk breakdown
    stockout_high = sum(1 for r in risks if r["stockout_risk"] == "HIGH")
    stockout_med = sum(1 for r in risks if r["stockout_risk"] == "MEDIUM")
    expiry_high = sum(1 for r in risks if r["expiry_risk"] == "HIGH")
    expiry_med = sum(1 for r in risks if r["expiry_risk"] == "MEDIUM")
    healthy = sum(1 for r in risks if r["stockout_risk"] == "NONE" and r["expiry_risk"] == "NONE")

    return jsonify({
        "sales_trend": {
            "dates": dates,
            "revenues": revenues,
            "quantities": quantities
        },
        "categories": {
            "labels": cat_labels,
            "revenues": cat_revenues
        },
        "stock_vs_demand": {
            "labels": prod_names,
            "current_stock": current_stocks,
            "predicted_demand": predicted_demands
        },
        "risk_summary": {
            "labels": ["Stockout High", "Stockout Medium", "Expiry High", "Expiry Medium", "Optimal Stock"],
            "data": [stockout_high, stockout_med, expiry_high, expiry_med, healthy]
        }
    })
