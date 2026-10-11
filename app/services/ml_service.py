import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor

def prepare_sales_features(sales_list, product_id, max_days=60):
    """
    Data Processing Step:
    Extract daily sales time series for a specific product, reindex missing dates with 0,
    and engineer lag/date features for ML training.
    """
    if not sales_list:
        return pd.DataFrame()

    df = pd.DataFrame(sales_list)
    if "date" not in df.columns or "quantity_sold" not in df.columns:
        return pd.DataFrame()

    # Convert date and aggregate daily totals for product
    df["date"] = pd.to_datetime(df["date"])
    df = df.groupby("date")["quantity_sold"].sum().reset_index()

    # Reindex date range to ensure contiguous daily records
    min_date = df["date"].min()
    max_date = df["date"].max()
    full_range = pd.date_range(start=min_date, end=max_date, freq="D")
    
    df = df.set_index("date").reindex(full_range, fill_value=0).reset_index()
    df.rename(columns={"index": "date"}, inplace=True)

    # Feature Engineering
    df["day_of_week"] = df["date"].dt.dayofweek
    df["day_of_month"] = df["date"].dt.day
    df["is_weekend"] = df["day_of_week"].apply(lambda x: 1 if x >= 5 else 0)
    df["lag_1"] = df["quantity_sold"].shift(1).fillna(0)
    df["rolling_7d"] = df["quantity_sold"].shift(1).rolling(window=7, min_periods=1).mean().fillna(0)

    return df

def train_and_predict_product_demand(df, forecast_days=7):
    """
    Model Training & Prediction Step:
    Train Scikit-Learn Linear Regression model on historical sales features
    and generate predictions for next forecast_days.
    """
    if len(df) < 7:
        # Fallback to simple mean if insufficient data
        avg_demand = max(1.0, float(df["quantity_sold"].mean())) if len(df) > 0 else 5.0
        daily_forecast = [round(avg_demand, 1)] * forecast_days
        return round(sum(daily_forecast), 1), daily_forecast, "Simple Historical Average (Insufficient Data)"

    X = df[["day_of_week", "day_of_month", "is_weekend", "lag_1", "rolling_7d"]]
    y = df["quantity_sold"]

    # Train Scikit-learn Linear Regression Model
    model = LinearRegression()
    model.fit(X, y)

    # Forecasting next forecast_days iteratively
    last_date = df["date"].max()
    last_qty = float(df["quantity_sold"].iloc[-1])
    recent_7 = list(df["quantity_sold"].tail(7))

    daily_forecast = []
    current_date = last_date
    current_lag = last_qty

    for _ in range(forecast_days):
        current_date += timedelta(days=1)
        day_of_week = current_date.dayofweek
        day_of_month = current_date.day
        is_weekend = 1 if day_of_week >= 5 else 0
        rolling_7d = np.mean(recent_7) if recent_7 else current_lag

        feat = pd.DataFrame([{
            "day_of_week": day_of_week,
            "day_of_month": day_of_month,
            "is_weekend": is_weekend,
            "lag_1": current_lag,
            "rolling_7d": rolling_7d
        }])

        pred_qty = float(model.predict(feat)[0])
        pred_qty = max(0.0, round(pred_qty, 1))

        daily_forecast.append(pred_qty)
        current_lag = pred_qty
        recent_7.pop(0)
        recent_7.append(pred_qty)

    predicted_demand_7d = round(sum(daily_forecast), 1)
    model_name = "Scikit-Learn LinearRegression (Lags + DayOfWeek)"
    
    return predicted_demand_7d, daily_forecast, model_name

def predict_demand_for_product(db, user_id, product_id):
    """
    End-to-End Prediction Service for a single product.
    Updates MongoDB predictions collection.
    """
    sales_cursor = db.sales.find({"product_id": product_id, "user_id": user_id}, {"_id": 0, "date": 1, "quantity_sold": 1})
    sales_list = list(sales_cursor)

    if not sales_list:
        predicted_demand_7d = 10.0
        daily_forecast = [1.5, 1.5, 1.5, 1.5, 1.5, 1.0, 1.5]
        model_name = "Default Benchmark (No Sales Recorded Yet)"
    else:
        df = prepare_sales_features(sales_list, product_id)
        predicted_demand_7d, daily_forecast, model_name = train_and_predict_product_demand(df, forecast_days=7)

    today_str = datetime.now().strftime("%Y-%m-%d")
    
    pred_doc = {
        "product_id": product_id,
        "prediction_date": today_str,
        "predicted_demand_7d": predicted_demand_7d,
        "daily_forecast": daily_forecast,
        "model_used": model_name,
        "confidence_note": "Calculated using continuous daily sales features",
        "updated_at": datetime.now(),
        "user_id": user_id
    }

    db.predictions.update_one(
        {"product_id": product_id, "user_id": user_id},
        {"$set": pred_doc},
        upsert=True
    )

    return pred_doc

def run_all_predictions(db, user_id):
    """
    Run demand prediction models for all products in database.
    """
    products = list(db.products.find({"user_id": user_id}, {"_id": 0, "product_id": 1}))
    results = []
    for p in products:
        res = predict_demand_for_product(db, user_id, p["product_id"])
        results.append(res)
    return results

def get_predictions_with_product_details(db, user_id):
    """
    Get prediction data joined with product details for display.
    """
    products = list(db.products.find({"user_id": user_id}, {"_id": 0}))
    predictions_map = {p["product_id"]: p for p in db.predictions.find({"user_id": user_id}, {"_id": 0})}

    combined = []
    for p in products:
        p_id = p["product_id"]
        pred = predictions_map.get(p_id)
        if not pred:
            pred = predict_demand_for_product(db, user_id, p_id)
        
        combined.append({
            "product_id": p_id,
            "product_name": p["name"],
            "category": p["category"],
            "current_stock": p["current_stock"],
            "unit_price": p["unit_price"],
            "reorder_level": p["reorder_level"],
            "predicted_demand_7d": pred.get("predicted_demand_7d", 0.0),
            "daily_forecast": pred.get("daily_forecast", []),
            "model_used": pred.get("model_used", "N/A"),
            "updated_at": pred.get("updated_at")
        })

    return combined
