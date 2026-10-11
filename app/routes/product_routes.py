from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from app.routes.auth_routes import login_required
from app.db import get_db
from app.services.inventory_service import (
    get_all_products, get_product_by_id, add_product, update_product, delete_product, generate_next_product_id
)
from app.services.ml_service import predict_demand_for_product

product_bp = Blueprint('product', __name__, url_prefix='/products')

@product_bp.route('/')
@login_required
def list_products():
    db = get_db()
    user_id = session['user_id']
    search = request.args.get('search', '').strip()
    category = request.args.get('category', '').strip()

    products = get_all_products(db, user_id, search=search, category=category)
    suppliers = list(db.suppliers.find({}, {"_id": 0}))
    categories = list(db.products.distinct("category", {"user_id": user_id}))
    next_pid = generate_next_product_id(db, user_id)

    return render_template(
        'products.html',
        products=products,
        suppliers=suppliers,
        categories=categories,
        search=search,
        selected_category=category,
        next_pid=next_pid
    )

@product_bp.route('/add', methods=['POST'])
@login_required
def handle_add_product():
    db = get_db()
    user_id = session['user_id']
    data = request.form.to_dict()
    try:
        p_id = add_product(db, user_id, data)
        # Generate initial prediction for new product
        predict_demand_for_product(db, user_id, p_id)
        flash(f"Product '{data.get('name')}' ({p_id}) added successfully!", "success")
    except Exception as e:
        flash(f"Error adding product: {str(e)}", "danger")

    return redirect(url_for('product.list_products'))

@product_bp.route('/edit/<product_id>', methods=['POST'])
@login_required
def handle_edit_product(product_id):
    db = get_db()
    user_id = session['user_id']
    data = request.form.to_dict()
    try:
        updated = update_product(db, user_id, product_id, data)
        if updated:
            predict_demand_for_product(db, user_id, product_id)
            flash(f"Product '{product_id}' updated successfully!", "success")
        else:
            flash(f"No changes made to product '{product_id}'.", "info")
    except Exception as e:
        flash(f"Error updating product: {str(e)}", "danger")

    return redirect(url_for('product.list_products'))

@product_bp.route('/delete/<product_id>', methods=['POST'])
@login_required
def handle_delete_product(product_id):
    db = get_db()
    user_id = session['user_id']
    try:
        deleted = delete_product(db, user_id, product_id)
        if deleted:
            flash(f"Product '{product_id}' deleted successfully.", "warning")
        else:
            flash(f"Product '{product_id}' not found.", "danger")
    except Exception as e:
        flash(f"Error deleting product: {str(e)}", "danger")

    return redirect(url_for('product.list_products'))
