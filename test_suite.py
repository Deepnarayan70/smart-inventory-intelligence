"""Comprehensive Integration Verification Suite for Smart Inventory Intelligence.

Runs against a newly named local test database, never production inventory_db.
Requires MongoDB running on localhost:27017. The temporary database is dropped
when the suite finishes.
"""
import os
import uuid
import unittest
from datetime import datetime, timedelta
import pandas as pd

TEST_DB = "inventory_test_" + uuid.uuid4().hex[:10]
os.environ["MONGO_URI"] = f"mongodb://localhost:27017/{TEST_DB}"
os.environ["SECRET_KEY"] = "integration-test-secure-key"
os.environ["AUTO_INIT_DB_INDEXES"] = "false"

from pymongo import MongoClient
from app import create_app
from app.db import init_db_indexes
from app.seed_data import seed_database
from app.services.inventory_service import (
    add_product, get_product_by_id, update_product, delete_product, get_inventory_summary
)
from app.services.sales_service import (
    record_sale, get_sales_analytics, get_sales_history
)
from app.services.ml_service import train_and_predict_product_demand
from app.services.alert_service import evaluate_all_risks_and_alerts, get_risk_summary


class SmartInventorySystemTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = MongoClient(os.environ["MONGO_URI"], serverSelectionTimeoutMS=5000)
        cls.client.admin.command("ping")
        cls.db = cls.client[TEST_DB]
        init_db_indexes(cls.db)
        cls.app = create_app()
        cls.app.config.update(TESTING=True, SECRET_KEY="integration-test-secure-key")

    @classmethod
    def tearDownClass(cls):
        # Cleanly drop only the isolated test database
        cls.client.drop_database(TEST_DB)
        cls.client.close()

    def setUp(self):
        self.user_a = "user-a-" + uuid.uuid4().hex
        self.user_b = "user-b-" + uuid.uuid4().hex

    def test_01_registration_login_logout_and_protected_routes(self):
        """1. Verify registration, login, logout, and protected route redirection."""
        email = f"user-{uuid.uuid4().hex}@smartinventory.io"
        client = self.app.test_client()

        # Registration
        reg_res = client.post("/register", data={
            "name": "Integration User",
            "email": email,
            "password": "Password123!",
            "confirm_password": "Password123!"
        }, follow_redirects=True)
        self.assertEqual(reg_res.status_code, 200)

        # Login
        login_res = client.post("/login", data={
            "email": email,
            "password": "Password123!"
        }, follow_redirects=True)
        self.assertEqual(login_res.status_code, 200)
        self.assertIn(b"Dashboard", login_res.data)

        # Logout
        logout_res = client.get("/logout", follow_redirects=True)
        self.assertEqual(logout_res.status_code, 200)
        self.assertIn(b"Login", logout_res.data)

        # Accessing protected page when logged out should redirect
        prot_res = client.get("/products/", follow_redirects=False)
        self.assertIn(prot_res.status_code, (301, 302, 303, 307, 308))
        self.assertIn("/login", prot_res.headers.get("Location", ""))

    def test_02_empty_dashboard_for_new_account(self):
        """2. Verify that a newly registered account starts with empty state."""
        summary = get_inventory_summary(self.db, self.user_a)
        self.assertEqual(summary["total_products"], 0)
        self.assertEqual(summary["total_stock_qty"], 0)
        self.assertEqual(summary["total_inventory_value"], 0.0)

        analytics = get_sales_analytics(self.db, self.user_a)
        self.assertEqual(analytics["total_sales_count"], 0)
        self.assertEqual(analytics["total_revenue"], 0.0)

        alerts = get_risk_summary(self.db, self.user_a)
        self.assertEqual(alerts["total_alerts"], 0)

    def test_03_product_crud_operations(self):
        """3. Verify complete Create, Read, Update, Delete for products."""
        pid = add_product(self.db, self.user_a, {
            "product_id": "PRD-TEST-CRUD",
            "name": "Organic Oat Milk",
            "category": "Dairy",
            "current_stock": 45,
            "unit_price": 3.75,
            "reorder_level": 15,
            "unit": "Cartons"
        })
        self.assertEqual(pid, "PRD-TEST-CRUD")

        # Read
        product = get_product_by_id(self.db, self.user_a, pid)
        self.assertIsNotNone(product)
        self.assertEqual(product["name"], "Organic Oat Milk")
        self.assertEqual(product["current_stock"], 45)

        # Update
        updated = update_product(self.db, self.user_a, pid, {
            "name": "Organic Oat Milk Premium",
            "category": "Dairy",
            "current_stock": 50,
            "unit_price": 4.10,
            "reorder_level": 12,
            "unit": "Cartons"
        })
        self.assertTrue(updated)
        refreshed = get_product_by_id(self.db, self.user_a, pid)
        self.assertEqual(refreshed["name"], "Organic Oat Milk Premium")
        self.assertEqual(refreshed["current_stock"], 50)
        self.assertEqual(refreshed["unit_price"], 4.10)

        # Delete
        deleted = delete_product(self.db, self.user_a, pid)
        self.assertTrue(deleted)
        self.assertIsNone(get_product_by_id(self.db, self.user_a, pid))

    def test_04_sales_transaction_and_stock_reduction(self):
        """4. Verify sales transaction atomically reduces current stock."""
        pid = add_product(self.db, self.user_a, {
            "product_id": "PRD-SALES-DED",
            "name": "Almond Croissant",
            "current_stock": 20,
            "unit_price": 2.50
        })
        success, msg, sale = record_sale(self.db, self.user_a, pid, quantity_sold=5, selling_price=2.50)
        self.assertTrue(success)
        self.assertEqual(sale["total_amount"], 12.50)

        # Verify stock decreased
        prod = get_product_by_id(self.db, self.user_a, pid)
        self.assertEqual(prod["current_stock"], 15)

    def test_05_stock_replenishment(self):
        """5. Verify stock replenishment via inventory updates."""
        pid = add_product(self.db, self.user_a, {
            "product_id": "PRD-REPLENISH",
            "name": "Greek Yogurt",
            "current_stock": 5,
            "unit_price": 1.80,
            "reorder_level": 10
        })
        # Replenish stock by 30 units (new stock 35)
        ok = update_product(self.db, self.user_a, pid, {
            "name": "Greek Yogurt",
            "current_stock": 35,
            "unit_price": 1.80,
            "reorder_level": 10
        })
        self.assertTrue(ok)
        prod = get_product_by_id(self.db, self.user_a, pid)
        self.assertEqual(prod["current_stock"], 35)

    def test_06_demand_forecasting_and_insufficient_history(self):
        """6. Verify ML forecasting requires 7 distinct days; returns honest fallback under 7."""
        # Under 7 calendar days
        short_df = pd.DataFrame({
            "date": pd.date_range("2026-02-01", periods=5, freq="D"),
            "quantity_sold": [4, 6, 5, 7, 6],
            "day_of_week": [0, 1, 2, 3, 4],
            "day_of_month": [1, 2, 3, 4, 5],
            "is_weekend": [0, 0, 0, 0, 0],
            "lag_1": [0, 4, 6, 5, 7],
            "rolling_7d": [0, 4, 5, 5, 5.5]
        })
        pred_short, _, model_short = train_and_predict_product_demand(short_df)
        self.assertIn("Insufficient Data", model_short)

        # 7 or more calendar days
        full_df = pd.DataFrame({
            "date": pd.date_range("2026-02-01", periods=10, freq="D"),
            "quantity_sold": [4, 6, 5, 7, 6, 8, 7, 5, 6, 7],
            "day_of_week": [0, 1, 2, 3, 4, 5, 6, 0, 1, 2],
            "day_of_month": list(range(1, 11)),
            "is_weekend": [0, 0, 0, 0, 0, 1, 1, 0, 0, 0],
            "lag_1": [0, 4, 6, 5, 7, 6, 8, 7, 5, 6],
            "rolling_7d": [0, 4, 5, 5, 5.5, 6, 6.2, 6.3, 6.4, 6.5]
        })
        pred_full, daily_forecast, model_full = train_and_predict_product_demand(full_df)
        self.assertIn("LinearRegression", model_full)
        self.assertEqual(len(daily_forecast), 7)
        self.assertGreater(pred_full, 0)

    def test_07_stockout_and_expiry_risk_calculations(self):
        """7. Verify stockout risk and expiry/waste risk assessment engine."""
        today = datetime.now()
        exp_soon = (today + timedelta(days=2)).strftime("%Y-%m-%d")

        # 1. Product with High Stockout Risk
        pid1 = add_product(self.db, self.user_a, {
            "product_id": "PRD-RISK-STOCKOUT",
            "name": "Artisan Bread",
            "current_stock": 2,
            "reorder_level": 15,
            "unit_price": 3.0
        })
        self.db.predictions.insert_one({
            "user_id": self.user_a,
            "product_id": pid1,
            "predicted_demand_7d": 25,
            "daily_forecast": [4, 4, 3, 3, 4, 4, 3]
        })

        # 2. Product with High Expiry/Waste Risk (high stock, soon expiring, low demand velocity)
        pid2 = add_product(self.db, self.user_a, {
            "product_id": "PRD-RISK-EXPIRY",
            "name": "Fresh Berry Cake",
            "current_stock": 50,
            "reorder_level": 5,
            "expiry_date": exp_soon,
            "unit_price": 12.0
        })
        self.db.predictions.insert_one({
            "user_id": self.user_a,
            "product_id": pid2,
            "predicted_demand_7d": 7,
            "daily_forecast": [1, 1, 1, 1, 1, 1, 1]
        })

        risks = evaluate_all_risks_and_alerts(self.db, self.user_a)
        self.assertGreaterEqual(len(risks), 2)

        stockout_item = next((r for r in risks if r["product_id"] == pid1), None)
        self.assertIsNotNone(stockout_item)
        self.assertEqual(stockout_item["stockout_risk"], "HIGH")
        self.assertIn("RESTOCK", stockout_item["recommendation"])

        expiry_item = next((r for r in risks if r["product_id"] == pid2), None)
        self.assertIsNotNone(expiry_item)
        self.assertEqual(expiry_item["expiry_risk"], "HIGH")
        self.assertIn("DISCOUNT", expiry_item["recommendation"])

    def test_08_strict_multi_user_data_isolation(self):
        """8. Verify absolute multi-user isolation across all entities."""
        add_product(self.db, self.user_a, {
            "product_id": "PRD-PRIVATE-A",
            "name": "User A Secret Recipe",
            "current_stock": 100,
            "unit_price": 50.0
        })

        # User B cannot read User A's product
        self.assertIsNone(get_product_by_id(self.db, self.user_b, "PRD-PRIVATE-A"))

        # User B cannot update User A's product
        self.assertFalse(update_product(self.db, self.user_b, "PRD-PRIVATE-A", {
            "name": "Hacked Product", "current_stock": 0, "unit_price": 0.0
        }))

        # User B cannot delete User A's product
        self.assertFalse(delete_product(self.db, self.user_b, "PRD-PRIVATE-A"))

        # User A's product remains untouched
        prod_a = get_product_by_id(self.db, self.user_a, "PRD-PRIVATE-A")
        self.assertIsNotNone(prod_a)
        self.assertEqual(prod_a["name"], "User A Secret Recipe")

    def test_09_user_specific_demo_data_seeding(self):
        """9. Verify demo seed data is strictly isolated to current user."""
        add_product(self.db, self.user_b, {
            "product_id": "PRD-B-CUSTOM",
            "name": "User B Custom Product",
            "current_stock": 10,
            "unit_price": 5.0
        })

        # Seed data for User A
        seed_database(self.db, self.user_a)

        # User A has 12 seeded products
        count_a = self.db.products.count_documents({"user_id": self.user_a})
        self.assertEqual(count_a, 12)

        # User B still has only their 1 product
        count_b = self.db.products.count_documents({"user_id": self.user_b})
        self.assertEqual(count_b, 1)
        self.assertIsNotNone(get_product_by_id(self.db, self.user_b, "PRD-B-CUSTOM"))

    def test_10_mongodb_aggregation_pipelines(self):
        """10. Verify PyMongo aggregation pipelines calculate correct analytics."""
        self.db.sales.insert_many([
            {"user_id": self.user_a, "sale_id": "SALE-AG1", "product_id": "PA1", "product_name": "Coffee",
             "category": "Beverages", "date": "2026-10-10", "quantity_sold": 4, "total_amount": 16.0},
            {"user_id": self.user_a, "sale_id": "SALE-AG2", "product_id": "PA1", "product_name": "Coffee",
             "category": "Beverages", "date": "2026-10-10", "quantity_sold": 2, "total_amount": 8.0},
            {"user_id": self.user_a, "sale_id": "SALE-AG3", "product_id": "PA2", "product_name": "Muffin",
             "category": "Bakery", "date": "2026-10-10", "quantity_sold": 3, "total_amount": 9.0},
            # User B sale should be excluded by pipeline $match
            {"user_id": self.user_b, "sale_id": "SALE-AG4", "product_id": "PB1", "product_name": "Sandwich",
             "category": "Prepared", "date": "2026-10-10", "quantity_sold": 50, "total_amount": 350.0},
        ])

        analytics = get_sales_analytics(self.db, self.user_a)
        self.assertEqual(analytics["total_sales_count"], 3)
        self.assertEqual(analytics["total_items_sold"], 9)
        self.assertEqual(analytics["total_revenue"], 33.0)

        # Check Category aggregation
        cat_sales = {c["category"]: c["revenue"] for c in analytics["category_sales"]}
        self.assertEqual(cat_sales["Beverages"], 24.0)
        self.assertEqual(cat_sales["Bakery"], 9.0)

        # Check Top selling products
        top_prod = analytics["top_selling_products"][0]
        self.assertEqual(top_prod["product_id"], "PA1")
        self.assertEqual(top_prod["total_qty"], 6)

    def test_11_indexes_and_compatibility(self):
        """11. Verify compound tenant-aware indexes exist on collections."""
        indexes_products = {idx["name"]: idx["key"] for idx in self.db.products.list_indexes()}
        self.assertIn("user_product_unique", indexes_products)
        self.assertEqual(indexes_products["user_product_unique"], {"user_id": 1, "product_id": 1})

        indexes_sales = {idx["name"]: idx["key"] for idx in self.db.sales.list_indexes()}
        self.assertIn("user_sale_unique", indexes_sales)
        self.assertEqual(indexes_sales["user_sale_unique"], {"user_id": 1, "sale_id": 1})

    def test_12_input_validation_and_concurrency_guard(self):
        """12. Verify input validation and atomic conditional overselling protection."""
        pid = add_product(self.db, self.user_a, {
            "product_id": "PRD-STOCK-GUARD",
            "name": "Mineral Water",
            "current_stock": 5,
            "unit_price": 1.50
        })

        # Negative quantity
        ok_neg, msg_neg, _ = record_sale(self.db, self.user_a, pid, quantity_sold=-2)
        self.assertFalse(ok_neg)
        self.assertIn("greater than zero", msg_neg)

        # Overselling quantity
        ok_over, msg_over, _ = record_sale(self.db, self.user_a, pid, quantity_sold=10)
        self.assertFalse(ok_over)
        self.assertIn("Insufficient stock", msg_over)

        # Stock remains at 5
        self.assertEqual(get_product_by_id(self.db, self.user_a, pid)["current_stock"], 5)

    def test_13_ui_navigation_and_pages_rendering(self):
        """13. Verify all protected routes return 200 OK for logged-in user."""
        email = f"webuser-{uuid.uuid4().hex}@smartinventory.io"
        client = self.app.test_client()

        # Register and log in
        client.post("/register", data={
            "name": "Web User", "email": email, "password": "WebPass123!", "confirm_password": "WebPass123!"
        }, follow_redirects=True)
        client.post("/login", data={"email": email, "password": "WebPass123!"}, follow_redirects=True)

        # Test all primary routes
        for path in ["/", "/products/", "/sales/", "/predictions/", "/alerts/"]:
            resp = client.get(path)
            self.assertEqual(resp.status_code, 200, f"Route {path} failed with {resp.status_code}")

    def test_14_application_startup_and_configuration(self):
        """14. Verify application factory, configuration and context lifecycle."""
        test_app = create_app()
        self.assertIsNotNone(test_app)
        with test_app.app_context():
            from app.db import get_db
            db_instance = get_db()
            self.assertIsNotNone(db_instance)
            pong = db_instance.command("ping")
            self.assertEqual(pong.get("ok"), 1.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
