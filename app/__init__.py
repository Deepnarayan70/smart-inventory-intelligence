from flask import Flask, session, g
from app.config import Config
from app.db import close_db, get_db, init_db_indexes, apply_schema_validation
import os

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    app.teardown_appcontext(close_db)

    # Database setup is opt-in so importing the app never unexpectedly mutates
    # an existing database. Enable explicitly after reviewing the current data.
    if os.environ.get("AUTO_INIT_DB_INDEXES", "false").lower() == "true":
        with app.app_context():
            db = get_db()
            init_db_indexes(db)
            if os.environ.get("MONGO_ENABLE_SCHEMA_VALIDATION", "false").lower() == "true":
                apply_schema_validation(db)


    # Register Blueprints
    from app.routes.auth_routes import auth_bp
    from app.routes.dashboard_routes import dashboard_bp
    from app.routes.product_routes import product_bp
    from app.routes.sales_routes import sales_bp
    from app.routes.predictions_routes import predictions_bp
    from app.routes.alerts_routes import alerts_bp
    from app.routes.api_routes import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(product_bp)
    app.register_blueprint(sales_bp)
    app.register_blueprint(predictions_bp)
    app.register_blueprint(alerts_bp)
    app.register_blueprint(api_bp)

    @app.context_processor
    def inject_user():
        from app.services.auth_service import get_user_by_id
        from app.db import get_db
        user = None
        if 'user_id' in session:
            try:
                db = get_db()
                user = get_user_by_id(db, session['user_id'])
            except Exception:
                pass
        return dict(current_user=user)

    return app
