import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
import pickle

# --- 1. Load Data ---
try:
    df = pd.read_csv('maternal_health_data.csv')
    print("Success: Dataset loaded!")
except FileNotFoundError:
    print("Error: 'maternal_health_data.csv' not found in this folder.")
    exit()

# --- 2. Preprocessing ---
# This converts 'high risk', 'low risk' into 0, 1, 2 for the computer
le = LabelEncoder()
df['RiskLevel'] = le.fit_transform(df['RiskLevel'])

# Features: Age, SystolicBP, DiastolicBP, BS, BodyTemp, HeartRate
X = df.drop('RiskLevel', axis=1) 
y = df['RiskLevel']

# --- 3. Train Model ---
# Split data: 80% to learn, 20% to test accuracy
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

model = RandomForestClassifier(n_estimators=100)
model.fit(X_train, y_train)

# --- 4. Save Outputs ---
# We save 'maternal_model.pkl' to use in our website later
with open('maternal_model.pkl', 'wb') as f:
    pickle.dump(model, f)

# We save the encoder to remember which number is 'High Risk'
with open('label_encoder.pkl', 'wb') as f:
    pickle.dump(le, f)

print("Success: 'maternal_model.pkl' created in your folder!")
print(f"Model Accuracy: {model.score(X_test, y_test) * 100:.2f}%")