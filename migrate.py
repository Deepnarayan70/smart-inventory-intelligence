from app import create_app
from app.db import get_db, init_db_indexes
from app.services.auth_service import create_user, get_user_by_id

def migrate():
    app = create_app()
    with app.app_context():
        db = get_db()
        
        print("Starting Demo Data Migration...")
        
        # 1. Create Demo User if it doesn't exist
        demo_email = "demo@smartinventory.local"
        demo_user = db.users.find_one({"email": demo_email})
        
        if not demo_user:
            print("Creating demo account...")
            success, user_id_str = create_user(db, "Demo User", demo_email, "demo123")
            if not success:
                print(f"Failed to create demo user: {user_id_str}")
                return
            print(f"Created demo account with ID: {user_id_str}")
        else:
            user_id_str = str(demo_user["_id"])
            print(f"Found existing demo account with ID: {user_id_str}")
            
        # 2. Iterate and update collections for missing user_id
        collections = ["products", "sales", "predictions", "alerts"]
        for coll_name in collections:
            collection = db[coll_name]
            result = collection.update_many(
                {"user_id": {"$exists": False}},
                {"$set": {"user_id": user_id_str}}
            )
            print(f"Migrated {result.modified_count} records in '{coll_name}'.")

        # 3. Drop existing potentially conflicting global unique indexes and recreate per-user indexes
        print("Re-initializing indexes...")
        try:
            db.products.drop_index("product_id_1")
            db.sales.drop_index("sale_id_1")
            db.predictions.drop_index("product_id_1")
        except Exception as e:
            print(f"Index drop notice: {e}")
            
        try:
            db.products.create_index([("user_id", 1), ("product_id", 1)], unique=True)
            db.products.create_index([("user_id", 1), ("category", 1)])
            db.sales.create_index([("user_id", 1), ("sale_id", 1)], unique=True)
            db.sales.create_index([("user_id", 1), ("product_id", 1)])
            db.sales.create_index([("user_id", 1), ("date", 1)])
            db.predictions.create_index([("user_id", 1), ("product_id", 1)], unique=True)
            db.alerts.create_index([("user_id", 1), ("product_id", 1)])
        except Exception as e:
            print(f"Index creation error: {e}")

        print("Migration complete.")

if __name__ == "__main__":
    migrate()
