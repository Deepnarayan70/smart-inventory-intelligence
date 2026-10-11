import os
from pymongo import MongoClient, ASCENDING, DESCENDING
from flask import g


def get_db():
    """Get or create the PyMongo database connection for the current request."""
    if "db_client" not in g:
        mongo_uri = os.environ.get("MONGO_URI", "mongodb://localhost:27017/inventory_db")
        g.db_client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        db_name = "inventory_db"
        # Prefer an explicitly configured database path; support query parameters.
        path = mongo_uri.split("?", 1)[0].rsplit("/", 1)[-1]
        if path:
            db_name = path
        g.db = g.db_client[db_name]
    return g.db


def close_db(e=None):
    """Close the request-scoped MongoDB client."""
    db_client = g.pop("db_client", None)
    if db_client is not None:
        db_client.close()


def _ensure_index(collection, keys, *, unique=False, name):
    """Reuse an equivalent existing index rather than creating a duplicate key pattern."""
    expected = list(keys)
    for index in collection.list_indexes():
        actual = [(field, direction) for field, direction in index.get("key", {}).items()]
        if actual == expected and bool(index.get("unique", False)) == bool(unique):
            return index.get("name")
    return collection.create_index(expected, unique=unique, name=name)


def init_db_indexes(db):
    """Create tenant-aware indexes before removing legacy global unique indexes.

    This function does not delete documents. If a compound unique index cannot be
    created because existing data contains duplicates, MongoDB raises an error and
    the legacy index is deliberately retained.
    """
    _ensure_index(db.users, [("email", ASCENDING)], unique=True, name="email_unique")

    # Create the replacement indexes first. This is important: never remove a
    # working constraint until its tenant-scoped replacement exists.
    _ensure_index(db.products, [("user_id", ASCENDING), ("product_id", ASCENDING)], unique=True, name="user_product_unique")
    _ensure_index(db.products, [("user_id", ASCENDING), ("category", ASCENDING)], name="user_category")

    _ensure_index(db.sales, [("user_id", ASCENDING), ("sale_id", ASCENDING)], unique=True, name="user_sale_unique")
    _ensure_index(db.sales, [("user_id", ASCENDING), ("product_id", ASCENDING)], name="user_product_sales")
    _ensure_index(db.sales, [("user_id", ASCENDING), ("date", DESCENDING)], name="user_date_desc")

    _ensure_index(db.predictions, [("user_id", ASCENDING), ("product_id", ASCENDING)], unique=True, name="user_prediction_unique")
    _ensure_index(db.alerts, [("user_id", ASCENDING), ("product_id", ASCENDING)], name="user_product_alerts")
    _ensure_index(db.alerts, [("user_id", ASCENDING), ("risk_level", ASCENDING)], name="user_risk_level")
    _ensure_index(db.suppliers, [("supplier_id", ASCENDING)], unique=True, name="supplier_unique")

    # Remove only known legacy global unique indexes, and only after the new
    # tenant-scoped constraints above were created successfully.
    for collection, legacy_name in (
        (db.products, "product_id_1"),
        (db.sales, "sale_id_1"),
        (db.predictions, "product_id_1"),
    ):
        existing_names = {idx.get("name") for idx in collection.list_indexes()}
        if legacy_name in existing_names:
            collection.drop_index(legacy_name)


def apply_schema_validation(db):
    """Enable moderate JSON-schema validation for core collections.

    Opt in explicitly after reviewing legacy documents by setting
    MONGO_ENABLE_SCHEMA_VALIDATION=true. Existing documents are not rewritten.
    """
    product_validator = {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["user_id", "product_id", "name", "current_stock", "unit_price"],
            "properties": {
                "user_id": {"bsonType": "string"},
                "product_id": {"bsonType": "string"},
                "name": {"bsonType": "string"},
                "category": {"bsonType": "string"},
                "current_stock": {"bsonType": ["int", "long", "double", "decimal"]},
                "unit_price": {"bsonType": ["int", "long", "double", "decimal"]},
                "reorder_level": {"bsonType": ["int", "long", "double"]},
                "expiry_date": {"bsonType": ["string", "null"]},
            },
        }
    }
    user_validator = {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["name", "email", "password_hash"],
            "properties": {
                "name": {"bsonType": "string"},
                "email": {"bsonType": "string"},
                "password_hash": {"bsonType": "string"},
            },
        }
    }
    existing_collections = set(db.list_collection_names())
    for name, validator in (("products", product_validator), ("users", user_validator)):
        if name not in existing_collections:
            db.create_collection(name)
        db.command({
            "collMod": name,
            "validator": validator,
            "validationLevel": "moderate",
            "validationAction": "error",
        })
