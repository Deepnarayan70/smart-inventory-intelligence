from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.routes.auth_routes import login_required
from app.db import get_db
from app.services.inventory_service import get_all_products
from app.services.sales_service import record_sale, get_sales_history, get_sales_analytics
from app.services.ml_service import predict_demand_for_product

sales_bp = Blueprint('sales', __name__, url_prefix='/sales')

@sales_bp.route('/')
@login_required
def list_sales():
    db = get_db()
    user_id = session['user_id']
    product_filter = request.args.get('product_id', '').strip()
    
    sales_list = get_sales_history(db, user_id, product_id=product_filter if product_filter else None)
    products = get_all_products(db, user_id)
    analytics = get_sales_analytics(db, user_id)

    return render_template(
        'sales.html',
        sales=sales_list,
        products=products,
        analytics=analytics,
        selected_product=product_filter
    )

@sales_bp.route('/record', methods=['POST'])
@login_required
def handle_record_sale():
    db = get_db()
    user_id = session['user_id']
    product_id = request.form.get('product_id')
    qty = request.form.get('quantity_sold')
    price = request.form.get('selling_price')
    sale_date = request.form.get('date')

    success, msg, sale_rec = record_sale(
        db,
        user_id,
        product_id=product_id,
        quantity_sold=qty,
        selling_price=price if price else None,
        sale_date=sale_date if sale_date else None
    )

    if success:
        # Re-run prediction after sale
        predict_demand_for_product(db, user_id, product_id)
        flash(msg, "success")
    else:
        flash(msg, "danger")

    return redirect(url_for('sales.list_sales'))
