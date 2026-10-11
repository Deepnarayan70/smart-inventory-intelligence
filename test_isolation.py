import requests

BASE_URL = "http://localhost:5000"

def test_isolation():
    session1 = requests.Session()
    session2 = requests.Session()
    
    # 1. Register User A
    print("Registering User A...")
    res = session1.post(f"{BASE_URL}/register", data={
        "name": "User A", "email": "userA@test.com", "password": "password123", "confirm_password": "password123"
    })
    
    # 2. Register User B
    print("Registering User B...")
    res = session2.post(f"{BASE_URL}/register", data={
        "name": "User B", "email": "userB@test.com", "password": "password123", "confirm_password": "password123"
    })
    
    # 3. User A Adds a Product
    print("User A adding product P_A_001...")
    res = session1.post(f"{BASE_URL}/products/add", data={
        "product_id": "P_A_001",
        "name": "User A Product",
        "category": "Snacks",
        "unit": "Packs",
        "current_stock": 100,
        "reorder_level": 10,
        "unit_price": 5.00,
        "supplier_id": "SUP-001"
    })
    
    # 4. User B gets their products (should be 0)
    print("Fetching User B products...")
    res = session2.get(f"{BASE_URL}/products/")
    html = res.text
    if "User A Product" in html:
        print("FAIL: User B can see User A's product!")
    else:
        print("PASS: User B cannot see User A's product. Isolation works!")

    # 5. User B tries to delete User A's product directly via POST
    print("User B attempting to delete User A product via direct API call...")
    res = session2.post(f"{BASE_URL}/products/delete/P_A_001")
    
    # Verify User A's product still exists
    res = session1.get(f"{BASE_URL}/products/")
    html = res.text
    if "User A Product" in html:
        print("PASS: User A's product was NOT deleted by User B. Direct object reference isolation works!")
    else:
        print("FAIL: User B managed to delete User A's product.")

if __name__ == "__main__":
    test_isolation()
