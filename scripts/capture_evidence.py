"""Capture sanitized MongoDB evidence, collection statistics, and aggregation analytics.

Performs read-only inspection of the active database specified in MONGO_URI.
Writes sanitized evidence to report-support/generated/live_mongodb_evidence.json.
Never modifies any documents, indexes, or collections.
"""
import json
import os
import sys
from pathlib import Path
from datetime import datetime

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from bson import json_util
from pymongo import MongoClient

from app.services.sales_service import get_sales_analytics
from app.services.inventory_service import get_inventory_summary

COLLECTIONS = ["users", "products", "sales", "suppliers", "predictions", "alerts"]
SENSITIVE_FIELDS = {"password", "password_hash", "email", "phone", "contact_person"}


def sanitize(document):
    """Sanitize sensitive fields and identifiers for evidence documentation."""
    if not document:
        return None
    clean = {}
    for key, value in document.items():
        if key == "_id":
            continue
        if key in SENSITIVE_FIELDS:
            clean[key] = "<redacted>"
        elif key == "user_id":
            clean[key] = "<redacted-user-id>"
        else:
            clean[key] = value
    return clean


def main():
    uri = os.environ.get("MONGO_URI", "mongodb://localhost:27017/inventory_db")
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    db_name = uri.split("?", 1)[0].rsplit("/", 1)[-1] or "inventory_db"
    db = client[db_name]
    output_dir = Path(__file__).resolve().parents[1] / "report-support" / "generated"
    output_dir.mkdir(parents=True, exist_ok=True)

    evidence = {
        "captured_at": datetime.now().isoformat(timespec="seconds"),
        "database_name": db_name,
        "collections": {},
        "analytics": {},
        "note": "User identifiers and direct contact fields are redacted. Capture is strictly read-only.",
    }
    for name in COLLECTIONS:
        coll = db[name]
        evidence["collections"][name] = {
            "document_count": coll.count_documents({}),
            "indexes": [
                {"name": idx.get("name"), "key": dict(idx.get("key", {})), "unique": idx.get("unique", False)}
                for idx in coll.list_indexes()
            ],
            "sample_document": sanitize(coll.find_one({})),
        }

    product = db.products.find_one({"user_id": {"$exists": True}}, {"user_id": 1})
    sale = db.sales.find_one({"user_id": {"$exists": True}}, {"user_id": 1})
    user_id = (product or sale or {}).get("user_id")
    if user_id is not None:
        evidence["analytics"] = {
            "sample_user_scope": "<redacted-user-id>",
            "inventory_summary": get_inventory_summary(db, user_id),
            "sales_analytics": get_sales_analytics(db, user_id),
        }
    else:
        evidence["analytics"] = {"note": "No user-scoped products or sales available in database."}

    output_path = output_dir / "live_mongodb_evidence.json"
    output_path.write_text(json_util.dumps(evidence, indent=2), encoding="utf-8")
    print(f"Read-only evidence successfully saved to: {output_path}")
    print("Database inspection complete. No records were modified.")
    client.close()


if __name__ == "__main__":
    main()
