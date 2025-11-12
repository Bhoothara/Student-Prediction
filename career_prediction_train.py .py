# ==========================================================
# STUDENT CAREER PREDICTION MODEL TRAINING (FINAL VERSION)
# ==========================================================

import pandas as pd
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score, classification_report
import joblib

# ----------------------------------------------------------
# 1️⃣ Load Dataset
# ----------------------------------------------------------
df = pd.read_excel("raw.xlsx")

# ✅ Clean up column names (remove spaces and invisible characters)
df.columns = df.columns.str.strip()

# ----------------------------------------------------------
# 2️⃣ Encode Categorical Columns
# ----------------------------------------------------------
cat_cols = df.select_dtypes(include='object').columns

label_encoders = {}

for col in cat_cols:
    le = LabelEncoder()
    df[col] = le.fit_transform(df[col])
    label_encoders[col] = le  # store encoder for each column

# ----------------------------------------------------------
# 3️⃣ Split Data
# ----------------------------------------------------------
X = df.drop(columns=['Suggested Job Role'])
y = df['Suggested Job Role']

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# ----------------------------------------------------------
# 4️⃣ Train Model (XGBoost)
# ----------------------------------------------------------
xgb_model = XGBClassifier(
    n_estimators=200,
    learning_rate=0.1,
    max_depth=6,
    random_state=42,
    eval_metric='mlogloss'
)

xgb_model.fit(X_train, y_train)

# ----------------------------------------------------------
# 5️⃣ Evaluate Model
# ----------------------------------------------------------
y_pred = xgb_model.predict(X_test)
print("✅ Model Evaluation Results:")
print("Accuracy:", accuracy_score(y_test, y_pred))
print("\nClassification Report:\n", classification_report(y_test, y_pred, zero_division=0))

# ----------------------------------------------------------
# 6️⃣ Save Model
# ----------------------------------------------------------
joblib.dump(xgb_model, "career_prediction_model.pkl")
print("🎯 Model saved as career_prediction_model.pkl")

# ----------------------------------------------------------
# 7️⃣ Save Label Mapping (real names instead of numbers)
# ----------------------------------------------------------
# We can use the encoder for 'Suggested Job Role' to map numbers back to names
role_encoder = label_encoders['Suggested Job Role']
label_mapping = {i: label for i, label in enumerate(role_encoder.classes_)}

joblib.dump(label_mapping, "label_mapping.pkl")
print("✅ Saved label mapping as label_mapping.pkl")

# ----------------------------------------------------------
# 8️⃣ Done!
# ----------------------------------------------------------
print("\n🚀 Training complete! You can now run app.py to use the model.")
