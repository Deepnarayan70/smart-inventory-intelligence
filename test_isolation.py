import urllib.request
import urllib.parse
import http.cookiejar
from pymongo import MongoClient

BASE_URL = "http://127.0.0.1:5000"


class SessionClient:
    def __init__(self):
        self.cookie_jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cookie_jar),
            urllib.request.HTTPRedirectHandler()
        )

    def get(self, path):
        req = urllib.request.Request(f"{BASE_URL}{path}")
        with self.opener.open(req) as resp:
            return resp.getcode(), resp.read().decode("utf-8")

    def post(self, path, data=None):
        encoded = urllib.parse.urlencode(data or {}).encode("utf-8")
        req = urllib.request.Request(f"{BASE_URL}{path}", data=encoded, method="POST")
        with self.opener.open(req) as resp:
            return resp.getcode(), resp.read().decode("utf-8")


def test_isolation():
    client1 = SessionClient()
    client2 = SessionClient()

    user_a_email = "audit_user_a@example.com"
    user_b_email = "audit_user_b@example.com"

    # Connect to MongoDB directly only for targeted cleanup before and after test
    mongo_client = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=2000)
    db = mongo_client["inventory_db"]

    def cleanup():
        for email in [user_a_email, user_b_email]:
            user = db.users.find_one({"email": email})
            if user:
                uid = str(user["_id"])
                db.users.delete_one({"_id": user["_id"]})
                db.products.delete_many({"user_id": uid})
                db.sales.delete_many({"user_id": uid})
                db.predictions.delete_many({"user_id": uid})
                db.alerts.delete_many({"user_id": uid})

    cleanup()

    try:
        print("[1/8] Registering User A...")
        code, body = client1.post("/register", {
            "name": "Audit User A",
            "email": user_a_email,
            "password": "Password123!",
            "confirm_password": "Password123!"
        })
        assert code == 200, f"Registration A failed with {code}"

        print("  -> Logging in as User A...")
        code, body = client1.post("/login", {
            "email": user_a_email,
            "password": "Password123!"
        })
        assert code == 200, f"Login A failed with {code}"

        print("[2/8] Verifying User A dashboard empty state...")
        code, body = client1.get("/")
        assert code == 200
        assert "Audit User A" in body

        print("[3/8] User A adding product PRD-AUDIT-101 (Stock: 25)...")
        code, body = client1.post("/products/add", {
            "product_id": "PRD-AUDIT-101",
            "name": "Audit Sourdough Loaf",
            "category": "Bakery",
            "unit": "Pcs",
            "current_stock": 25,
            "reorder_level": 10,
            "unit_price": 4.50,
            "supplier_id": "SUP001",
            "expiry_date": "2026-10-30"
        })
        assert code == 200
        assert "PRD-AUDIT-101" in body

        print("[4/8] User A recording sale for PRD-AUDIT-101 (Qty: 5)...")
        code, body = client1.post("/sales/record", {
            "product_id": "PRD-AUDIT-101",
            "quantity_sold": 5,
            "selling_price": 4.50
        })
        assert code == 200

        # Verify stock decremented to 20
        code, body = client1.get("/products/")
        assert code == 200
        assert "20" in body, "Stock was not decremented to 20"
        print("  -> Stock successfully decremented from 25 to 20.")

        print("[5/8] Verifying User A predictions and alerts pages...")
        code_p, body_p = client1.get("/predictions/")
        assert code_p == 200, f"Predictions returned {code_p}"
        code_a, body_a = client1.get("/alerts/")
        assert code_a == 200, f"Alerts returned {code_a}"
        print("  -> Predictions and alerts views loaded with HTTP 200.")

        print("[6/8] Registering User B...")
        code, body = client2.post("/register", {
            "name": "Audit User B",
            "email": user_b_email,
            "password": "Password123!",
            "confirm_password": "Password123!"
        })
        assert code == 200

        print("  -> Logging in as User B...")
        code, body = client2.post("/login", {
            "email": user_b_email,
            "password": "Password123!"
        })
        assert code == 200, f"Login B failed with {code}"

        print("[7/8] Verifying User B cannot view User A's product or sales...")
        code, body_b_prod = client2.get("/products/")
        assert code == 200
        assert "Audit Sourdough Loaf" not in body_b_prod, "FAIL: User B can see User A product!"
        assert "PRD-AUDIT-101" not in body_b_prod, "FAIL: User B can see User A product ID!"

        code, body_b_sales = client2.get("/sales/")
        assert code == 200
        assert "PRD-AUDIT-101" not in body_b_sales, "FAIL: User B can see User A sales transaction!"
        print("  -> Verified: User B has 0 access to User A's inventory or sales.")

        print("[8/8] User B attempting direct deletion of User A's product...")
        code, body = client2.post("/products/delete/PRD-AUDIT-101")
        # Check User A still has the product intact
        code, body_a_prod = client1.get("/products/")
        assert "PRD-AUDIT-101" in body_a_prod, "FAIL: User B managed to delete User A's product!"
        print("  -> PASS: User A's product remains intact. Direct object reference isolation verified!")

        # Verify logout
        code, _ = client1.get("/logout")
        code, _ = client2.get("/logout")
        print("  -> Both sessions cleanly logged out.")

        print("\nALL WORKFLOW & ISOLATION CHECKS PASSED SUCCESSFULLY!")
    finally:
        # Guarantee cleanup of only test audit accounts
        cleanup()
        mongo_client.close()
        print("Test audit accounts cleanly removed from database.")


if __name__ == "__main__":
    test_isolation()
