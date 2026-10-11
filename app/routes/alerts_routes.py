from flask import Blueprint, render_template, request, session
from app.routes.auth_routes import login_required
from app.db import get_db
from app.services.alert_service import evaluate_all_risks_and_alerts, get_risk_summary

alerts_bp = Blueprint('alerts', __name__, url_prefix='/alerts')

@alerts_bp.route('/')
@login_required
def list_alerts():
    db = get_db()
    user_id = session['user_id']
    risk_type = request.args.get('filter', 'all')
    
    risk_list = evaluate_all_risks_and_alerts(db, user_id)
    
    if risk_type == 'stockout':
        filtered = [r for r in risk_list if r['stockout_risk'] in ['HIGH', 'MEDIUM']]
    elif risk_type == 'expiry':
        filtered = [r for r in risk_list if r['expiry_risk'] in ['HIGH', 'MEDIUM']]
    else:
        filtered = risk_list

    risk_summary = get_risk_summary(db, user_id)

    return render_template(
        'alerts.html',
        risks=filtered,
        summary=risk_summary,
        filter=risk_type
    )
