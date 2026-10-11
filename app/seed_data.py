import random
from datetime import datetime, timedelta

def seed_database(db, user_id):
    """
    Populate MongoDB collections with realistic sample data for canteen/food business.
    Clears existing records in products, sales, predictions, alerts FOR THIS USER ONLY.
    Suppliers remain global.
    """
    db.products.delete_many({"user_id": user_id})
    db.sales.delete_many({"user_id": user_id})
    # Cannot just delete suppliers, but we might ensure they exist.
    if db.suppliers.count_documents({}) == 0:
        db.suppliers.delete_many({})
    db.predictions.delete_many({"user_id": user_id})
    db.alerts.delete_many({"user_id": user_id})

    # 1. Insert Suppliers
    suppliers = [
        {
            "supplier_id": "SUP001",
            "name": "Daily Dairy Fresh Ltd",
            "contact_person": "Michael Scott",
            "phone": "+1 555-0192",
            "email": "orders@dairyfresh.com",
            "lead_time_days": 2
        },
        {
            "supplier_id": "SUP002",
            "name": "Apex Bakery & Kitchen",
            "contact_person": "Pam Beesly",
            "phone": "+1 555-0143",
            "email": "supply@apexbakery.com",
            "lead_time_days": 1
        },
        {
            "supplier_id": "SUP003",
            "name": "Metro Green Farm Produce",
            "contact_person": "Dwight Schrute",
            "phone": "+1 555-0188",
            "email": "sales@beetfarms.com",
            "lead_time_days": 3
        },
        {
            "supplier_id": "SUP004",
            "name": "Refresh Drinks Co",
            "contact_person": "Jim Halpert",
            "phone": "+1 555-0122",
            "email": "orders@refreshdrinks.com",
            "lead_time_days": 2
        }
    ]
    if db.suppliers.count_documents({}) == 0:
        db.suppliers.insert_many(suppliers)

    # Today's date reference
    today = datetime.now()

    # 2. Insert Products (Food inventory with expiry & reorder thresholds)
    products = [
        {
            "product_id": "PRD001",
            "name": "Fresh Milk 1L",
            "category": "Dairy",
            "current_stock": 14,
            "unit_price": 3.50,
            "expiry_date": (today + timedelta(days=3)).strftime("%Y-%m-%d"),
            "reorder_level": 25,
            "supplier_id": "SUP001",
            "unit": "Liters",
            "created_at": datetime.now()
        },
        {
            "product_id": "PRD002",
            "name": "Greek Yogurt 200g",
            "category": "Dairy",
            "current_stock": 8,
            "unit_price": 2.20,
            "expiry_date": (today + timedelta(days=2)).strftime("%Y-%m-%d"),
            "reorder_level": 20,
            "supplier_id": "SUP001",
            "unit": "Cups",
            "created_at": datetime.now()
        },
        {
            "product_id": "PRD003",
            "name": "Egg Salad Sandwich",
            "category": "Prepared Food",
            "current_stock": 18,
            "unit_price": 5.50,
            "expiry_date": (today + timedelta(days=1)).strftime("%Y-%m-%d"),
            "reorder_level": 12,
            "supplier_id": "SUP002",
            "unit": "Packs",
            "created_at": datetime.now()
        },
        {
            "product_id": "PRD004",
            "name": "Chicken Pesto Wrap",
            "category": "Prepared Food",
            "current_stock": 4,
            "unit_price": 6.80,
            "expiry_date": (today + timedelta(days=2)).strftime("%Y-%m-%d"),
            "reorder_level": 15,
            "supplier_id": "SUP002",
            "unit": "Packs",
            "created_at": datetime.now()
        },
        {
            "product_id": "PRD005",
            "name": "Chocolate Muffin",
            "category": "Bakery",
            "current_stock": 35,
            "unit_price": 2.80,
            "expiry_date": (today + timedelta(days=4)).strftime("%Y-%m-%d"),
            "reorder_level": 15,
            "supplier_id": "SUP002",
            "unit": "Pieces",
            "created_at": datetime.now()
        },
        {
            "product_id": "PRD006",
            "name": "Butter Croissant",
            "category": "Bakery",
            "current_stock": 5,
            "unit_price": 2.50,
            "expiry_date": (today + timedelta(days=3)).strftime("%Y-%m-%d"),
            "reorder_level": 20,
            "supplier_id": "SUP002",
            "unit": "Pieces",
            "created_at": datetime.now()
        },
        {
            "product_id": "PRD007",
            "name": "Fresh Orange Juice 500ml",
            "category": "Beverages",
            "current_stock": 28,
            "unit_price": 3.20,
            "expiry_date": (today + timedelta(days=6)).strftime("%Y-%m-%d"),
            "reorder_level": 15,
            "supplier_id": "SUP004",
            "unit": "Bottles",
            "created_at": datetime.now()
        },
        {
            "product_id": "PRD008",
            "name": "Cold Brew Coffee",
            "category": "Beverages",
            "current_stock": 45,
            "unit_price": 4.00,
            "expiry_date": (today + timedelta(days=12)).strftime("%Y-%m-%d"),
            "reorder_level": 20,
            "supplier_id": "SUP004",
            "unit": "Bottles",
            "created_at": datetime.now()
        },
        {
            "product_id": "PRD009",
            "name": "Green Garden Salad",
            "category": "Prepared Food",
            "current_stock": 15,
            "unit_price": 5.00,
            "expiry_date": (today + timedelta(days=1)).strftime("%Y-%m-%d"),
            "reorder_level": 10,
            "supplier_id": "SUP003",
            "unit": "Bowls",
            "created_at": datetime.now()
        },
        {
            "product_id": "PRD010",
            "name": "Organic Apple Bag",
            "category": "Produce",
            "current_stock": 22,
            "unit_price": 4.50,
            "expiry_date": (today + timedelta(days=9)).strftime("%Y-%m-%d"),
            "reorder_level": 10,
            "supplier_id": "SUP003",
            "unit": "Packs",
            "created_at": datetime.now()
        },
        {
            "product_id": "PRD011",
            "name": "Tomato Basil Soup",
            "category": "Prepared Food",
            "current_stock": 3,
            "unit_price": 4.20,
            "expiry_date": (today + timedelta(days=2)).strftime("%Y-%m-%d"),
            "reorder_level": 15,
            "supplier_id": "SUP002",
            "unit": "Bowls",
            "created_at": datetime.now()
        },
        {
            "product_id": "PRD012",
            "name": "Berry Granola Parfait",
            "category": "Dairy",
            "current_stock": 19,
            "unit_price": 3.90,
            "expiry_date": (today + timedelta(days=2)).strftime("%Y-%m-%d"),
            "reorder_level": 12,
            "supplier_id": "SUP001",
            "unit": "Cups",
            "created_at": datetime.now()
        }
    ]
    for p in products:
        p["user_id"] = user_id
    
    db.products.insert_many(products)

    # 3. Generate Historical Sales (45 days of daily transactions per product)
    base_demand = {
        "PRD001": 10, # Fresh Milk
        "PRD002": 7,  # Greek Yogurt
        "PRD003": 8,  # Egg Salad Sandwich
        "PRD004": 9,  # Chicken Wrap
        "PRD005": 12, # Chocolate Muffin
        "PRD006": 11, # Croissant
        "PRD007": 10, # Orange Juice
        "PRD008": 15, # Cold Brew
        "PRD009": 6,  # Garden Salad
        "PRD010": 5,  # Apples
        "PRD011": 7,  # Soup
        "PRD012": 8   # Parfait
    }

    price_map = {p["product_id"]: p["unit_price"] for p in products}

    sales_records = []
    sale_counter = 1000

    start_date = today - timedelta(days=45)

    for day_offset in range(45):
        current_date = start_date + timedelta(days=day_offset)
        date_str = current_date.strftime("%Y-%m-%d")
        is_weekend = current_date.weekday() >= 5

        for p_id, avg_qty in base_demand.items():
            # Weekend sales are slightly lower for canteens
            multiplier = 0.5 if is_weekend else 1.2
            noise = random.randint(-2, 3)
            qty = max(1, int(avg_qty * multiplier + noise))

            unit_price = price_map[p_id]
            total_amt = round(qty * unit_price, 2)

            sale_counter += 1
            sales_records.append({
                "sale_id": f"SALE{sale_counter}",
                "product_id": p_id,
                "date": date_str,
                "quantity_sold": qty,
                "selling_price": unit_price,
                "total_amount": total_amt,
                "created_at": current_date,
                "user_id": user_id
            })

    db.sales.insert_many(sales_records)
    print(f"Database successfully seeded: {len(products)} products, {len(suppliers)} suppliers, {len(sales_records)} sales records.")
