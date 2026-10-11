# CRUD and Multi-User Isolation Verification

Run the integration suite against a local MongoDB server:

```bash
python test_suite.py
```

The suite creates an isolated test database (e.g. `inventory_test_a1b2c3d4e5`), executes 14 end-to-end integration scenarios, and drops only that temporary test database upon completion. It never touches production data or `inventory_db`.

## Verified Scenarios

1. User registration, login session, logout, and protected route enforcement.
2. Empty initial state on newly created accounts.
3. Complete product CRUD operations (Create, Read, Update, Delete).
4. Atomic sales transaction with stock decrement.
5. Stock replenishment workflow.
6. Machine learning demand forecasting with insufficient history fallback (< 7 days) and linear regression (>= 7 days).
7. Stockout risk and expiry/waste risk assessment calculations.
8. Strict multi-user data isolation (User A cannot view, mutate, or delete User B's records).
9. User-scoped demo dataset seeding without cross-tenant interference.
10. MongoDB native aggregation pipelines for KPIs, daily trends, category distribution, and top products.
11. Verification of compound tenant-scoped indexes on collections.
12. Input validation and atomic overselling prevention via conditional `$inc`.
13. Frontend UI navigation and HTTP 200 response verification for all core views.
14. Application factory startup, configuration lifecycle, and database connectivity ping.

**Verification Status:** All 14 test scenarios pass with 100% success against local MongoDB.
