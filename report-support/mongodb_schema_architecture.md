# MongoDB Schema and Architecture Evidence

**Project:** Smart Inventory Intelligence & Food-Waste Prevention System  
**Database expected by the application:** `inventory_db` (the actual database name is derived from `MONGO_URI`).

> This is source-code-derived schema documentation. Generate actual counts, indexes, representative documents, and analytics with `python scripts/capture_evidence.py` after verifying `MONGO_URI`.

## Collections

| Collection | Purpose | Main fields visible in application source | Relationship strategy |
|---|---|---|---|
| `users` | Login identities | `_id` (ObjectId), `name`, `email`, `password_hash`, `created_at` | Other collections refer to the user's stringified ObjectId through `user_id`. Password hashes must never appear in evidence. |
| `products` | Food inventory | `product_id`, `name`, `category`, `current_stock`, `unit_price`, `expiry_date`, `reorder_level`, `supplier_id`, `unit`, `user_id` | References supplier by `supplier_id`; product documents are scoped to a user. |
| `sales` | Sales history | `sale_id`, `product_id`, `date`, `quantity_sold`, `selling_price`, `total_amount`, `created_at`, `user_id` | References product by `product_id` and copies selected product details to preserve transaction context. |
| `suppliers` | Supplier and lead-time data | `supplier_id`, `name`, `contact_person`, `phone`, `email`, `lead_time_days` | Global supplier records are referenced by `supplier_id` in product records. |
| `predictions` | Seven-day demand forecast | `product_id`, `prediction_date`, `predicted_demand_7d`, `daily_forecast`, `model_used`, `confidence_note`, `updated_at`, `user_id` | One current prediction per user/product in the current service implementation; it is updated with `upsert=True`. |
| `alerts` | Stockout and expiry risk | `product_id`, `category`, stock/risk values, recommendation fields, `user_id` | User/product-scoped risk records. |

## BSON types

The source uses strings for identifiers and dates formatted as `YYYY-MM-DD`, numeric values for stock/price/quantity, arrays for seven-day forecasts, datetimes for audit timestamps, and MongoDB ObjectIds for user `_id`. Exact live types must be verified from `report-support/generated/live_mongodb_evidence.json`.

## Why references plus selective denormalization?

- Suppliers are shared lookup records, so products store `supplier_id` instead of duplicating all supplier contact details.
- Sales preserve `product_id` and copy `product_name`/`category` when recorded, so historical summaries remain interpretable after product metadata changes.
- Forecasts and alerts are separate documents because they are recalculated independently of core product records.
- `user_id` is included in user-owned records and queries to prevent cross-account data access.
