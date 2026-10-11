# Indexes and Schema Validation

## Indexes configured by `init_db_indexes(db)`

| Collection | Index | Purpose |
|---|---|---|
| `users` | unique `email` | Prevent duplicate accounts |
| `products` | unique `(user_id, product_id)` | Unique product identifiers within each user's inventory |
| `products` | `(user_id, category)` | User-scoped category filtering |
| `sales` | unique `(user_id, sale_id)` | Unique transaction IDs per user |
| `sales` | `(user_id, product_id)` | Product sales history |
| `sales` | `(user_id, date DESC)` | User-scoped date sorting |
| `predictions` | unique `(user_id, product_id)` | One current forecast per product and user |
| `alerts` | `(user_id, product_id)` | Product risk lookup |
| `alerts` | `(user_id, risk_level)` | Risk-level filtering |
| `suppliers` | unique `supplier_id` | Unique global supplier identifier |

The setup function creates replacement tenant-scoped indexes before dropping known legacy global unique indexes. If index creation fails, the old global index is not dropped. Existing duplicate data must be investigated before retrying.

## Schema validation

`apply_schema_validation(db)` provides moderate MongoDB JSON Schema validation for `users` and `products`. It is intentionally opt-in: set `MONGO_ENABLE_SCHEMA_VALIDATION=true` only after checking old documents for missing fields or incompatible types. This prevents a default application startup from unexpectedly rejecting existing data.

## Verification

Run `python setup_db.py` with the intended `MONGO_URI` to create/verify indexes. Set `MONGO_ENABLE_SCHEMA_VALIDATION=true` only for a deliberate validation rollout. Use `python scripts/capture_evidence.py` to record actual index names and key definitions.
