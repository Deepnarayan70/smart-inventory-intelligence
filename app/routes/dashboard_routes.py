from flask import Blueprint, render_template, session
from app.routes.auth_routes import login_required
from app.db import get_db
from app.services.inventory_service import get_inventory_summary
from app.services.sales_service import get_sales_analytics
from app.services.alert_service import get_risk_summary

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@login_required
def dashboard():
    db = get_db()
    user_id = session['user_id']
    
    inv_summary = get_inventory_summary(db, user_id)
    sales_analytics = get_sales_analytics(db, user_id)
    risk_summary = get_risk_summary(db, user_id)

    # Get recent sales
    recent_sales = list(db.sales.find({"user_id": user_id}, {"_id": 0}).sort("created_at", -1).limit(5))

    return render_template(
        'dashboard.html',
        inv=inv_summary,
        sales=sales_analytics,
        risk=risk_summary,
        recent_sales=recent_sales
    )
