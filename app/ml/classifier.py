import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

class CategoryClassifier:
    def __init__(self, model_path: str = "app/ml/category_model.pkl"):
        self.model_path = model_path
        self.model = None
        self.vectorizer = None

    def load_model(self):
        data = joblib.load(self.model_path)
        self.model = data["model"]
        self.vectorizer = data["vectorizer"]

    def predict(self, description: str) -> str:
        if not self.model or not self.vectorizer:
            self.load_model()
        vec = self.vectorizer.transform([description])
        return self.model.predict(vec)[0]