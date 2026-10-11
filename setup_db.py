"""Explicit database setup. Review existing records before running on production."""
import os
from app import create_app
from app.db import get_db, init_db_indexes, apply_schema_validation


def main():
    app = create_app()
    with app.app_context():
        db = get_db()
        db.command("ping")
        init_db_indexes(db)
        print("Tenant-aware indexes verified/created. No documents were deleted.")
        if os.environ.get("MONGO_ENABLE_SCHEMA_VALIDATION", "false").lower() == "true":
            apply_schema_validation(db)
            print("Moderate schema validation enabled for users and products.")
        else:
            print("Schema validation left unchanged (MONGO_ENABLE_SCHEMA_VALIDATION is false).")


if __name__ == "__main__":
    main()
