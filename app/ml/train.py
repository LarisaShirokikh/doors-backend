import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
import joblib
import os

def train_model(data: pd.DataFrame, model_path: str = "app/ml/category_model.pkl"):
    vectorizer = TfidfVectorizer(max_features=5000)
    X = vectorizer.fit_transform(data["description"])
    y = data["category"]

    model = LogisticRegression(max_iter=1000)
    model.fit(X, y)

    joblib.dump({"model": model, "vectorizer": vectorizer}, model_path)
    print(f"Model saved to {model_path}")