# Architecture Diagrams

## System architecture

```mermaid
flowchart TD
  U[User / Browser] --> F[Flask Routes and Templates]
  F --> S[Inventory, Sales, ML and Alert Services]
  S --> M[(MongoDB Collections)]
  S --> ML[scikit-learn Demand Forecasting]
  ML --> M
  F --> C[Chart.js Dashboard]
```

## Document relationships

```mermaid
erDiagram
  USERS ||--o{ PRODUCTS : owns
  USERS ||--o{ SALES : owns
  USERS ||--o{ PREDICTIONS : owns
  USERS ||--o{ ALERTS : owns
  SUPPLIERS ||--o{ PRODUCTS : supplies
  PRODUCTS ||--o{ SALES : referenced_by
  PRODUCTS ||--o| PREDICTIONS : forecasted_by
  PRODUCTS ||--o{ ALERTS : monitored_by
```

These diagrams describe relationships implemented or implied by the source code; they are not an ER-enforced relational schema.

## Sale data flow

```mermaid
flowchart LR
  R[Sale request] --> V[Validate quantity and product ownership]
  V --> D{Stock >= quantity?}
  D -- No --> E[Return insufficient-stock message]
  D -- Yes --> A[Atomic conditional $inc stock decrement]
  A --> I[Insert sale document]
  I --> P[Refresh product forecast]
  P --> O[Show success and updated stock]
```
