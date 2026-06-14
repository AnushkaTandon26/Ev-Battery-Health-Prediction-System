import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error
import joblib
from backend.database import db, BatteryData
from datetime import datetime, timedelta

def generate_sample_data(n_samples=1000):
    """Generate synthetic training data"""
    np.random.seed(42)
    voltage = np.random.normal(3.7, 0.2, n_samples)
    current = np.random.normal(0, 20, n_samples)
    soc = np.random.uniform(10, 100, n_samples)
    temp = np.random.normal(25, 10, n_samples)
    
    # Synthetic SOH (State of Health 0-100)
    soh = 100 - (abs(current)*0.3 + abs(temp-25)*0.5 + (100-soc)*0.2 + np.random.normal(0,5,n_samples))
    soh = np.clip(soh, 0, 100)
    
    return pd.DataFrame({
        'voltage': voltage,
        'current': current,
        'soc': soc,
        'temperature': temp,
        'SOH': soh
    })

def train_model():
    print("Generating sample data...")
    df = generate_sample_data()
    
    features = ['voltage', 'current', 'soc', 'temperature']
    X = df[features]
    y = df['SOH']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    
    y_pred = model.predict(X_test)
    mse = mean_squared_error(y_test, y_pred)
    print(f"Model trained! Test MSE: {mse:.2f}")
    
    joblib.dump(model, 'model/ev_battery_model.pkl')
    print("Model saved to model/ev_battery_model.pkl")
    
    # Update utils.py to use real model
    print("Ready for production use!")

if __name__ == "__main__":
    train_model()
