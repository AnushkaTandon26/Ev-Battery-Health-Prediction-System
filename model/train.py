# Training script for EV Battery State of Health (SOH) LSTM model
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
import joblib

def generate_synthetic_data(n_samples=2000):
    np.random.seed(42)
    voltage = np.random.uniform(3.0, 4.2, n_samples)
    current = np.random.uniform(-10.0, 10.0, n_samples)
    soc = np.random.uniform(10.0, 95.0, n_samples)
    temp = np.random.uniform(15.0, 45.0, n_samples)
    deg = np.random.uniform(0.01, 0.25, n_samples)
    soh = 100.0 - (deg * 100.0 + (temp - 25.0) * 0.2) + np.random.normal(0, 0.5, n_samples)
    soh = np.clip(soh, 40.0, 100.0)
    df = pd.DataFrame({'voltage': voltage, 'current': current, 'soc': soc, 'temp': temp, 'degradation': deg, 'soh': soh})
    return df

def prepare_features(df):
    features = ['voltage', 'current', 'soc', 'temp', 'degradation']
    scaler = StandardScaler()
    X = scaler.fit_transform(df[features])
    y = df['soh'].values
    return X, y, scaler
