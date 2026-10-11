from flask import Blueprint, render_template, redirect, url_for, flash, session
from app.routes.auth_routes import login_required
from app.db import get_db
from app.services.ml_service import get_predictions_with_product_details, run_all_predictions

predictions_bp = Blueprint('predictions', __name__, url_prefix='/predictions')

@predictions_bp.route('/')
@login_required
def list_predictions():
    db = get_db()
    user_id = session['user_id']
    items = get_predictions_with_product_details(db, user_id)
    return render_template('predictions.html', items=items)

@predictions_bp.route('/run', methods=['POST'])
@login_required
def handle_run_predictions():
    db = get_db()
    user_id = session['user_id']
    try:
        results = run_all_predictions(db, user_id)
        flash(f"Scikit-learn demand prediction models retrained and updated for {len(results)} products!", "success")
    except Exception as e:
        flash(f"Error training models: {str(e)}", "danger")

    return redirect(url_for('predictions.list_predictions'))
