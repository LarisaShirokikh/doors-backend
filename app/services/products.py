from app.ml.classifier import CategoryClassifier
from app.schemas.product import ProductCreate

classifier = CategoryClassifier()

async def auto_categorize_product(product: ProductCreate) -> str:
    return classifier.predict(product.description)