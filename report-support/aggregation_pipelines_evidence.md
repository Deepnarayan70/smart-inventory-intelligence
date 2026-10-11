# MongoDB Aggregation Pipelines

The sales and inventory summary services now use PyMongo `aggregate()` pipelines rather than loading all sales/products into Python to compute totals. The user scope is the first `$match` stage.

## Sales analytics

### Total sales KPIs

```python
[
  {"$match": {"user_id": user_id}},
  {"$group": {
    "_id": None,
    "total_sales_count": {"$sum": 1},
    "total_items_sold": {"$sum": {"$ifNull": ["$quantity_sold", 0]}},
    "total_revenue": {"$sum": {"$ifNull": ["$total_amount", 0]}}
  }},
  {"$project": {
    "_id": 0,
    "total_sales_count": 1,
    "total_items_sold": 1,
    "total_revenue": {"$round": ["$total_revenue", 2]}
  }}
]
```

### Daily trend

`$match` by user → `$group` by date with `$sum` revenue and quantity → `$sort` chronologically → `$project` a clean result shape.

### Category breakdown

`$match` by user → `$group` by category → `$sort` by revenue descending → `$project` category, revenue, and quantity.

### Top five products

`$match` by user → `$group` by product ID and sum quantity/revenue → `$sort` by quantity then revenue → `$limit: 5` → `$project` display fields.

## Inventory summary

`$match` by user → `$addFields` parses `expiry_date` with `$dateFromString` → `$group` calculates product count, total stock, inventory value (`$multiply` and `$sum`), low-stock count (`$cond`), and near-expiry count → `$project` rounds the value. Distinct categories are retrieved with a user-scoped `distinct()` query.

## Evidence status

The pipelines above are present in `app/services/sales_service.py` and `app/services/inventory_service.py`. Actual result rows and live index state should be captured by `python scripts/capture_evidence.py`; do not present example or empty output as production data.
