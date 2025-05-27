from fastapi import APIRouter

from app.api.v1.catalogs.router import router as catalogs_router
from app.api.v1.categories.router import router as categories_router
from app.api.v1.import_r.router import router as import_r_router
from app.api.v1.import_l.router import router as import_l_router
from app.api.v1.products.router import router as products_router
from app.api.v1.brands.router import router as brands_router
from app.api.v1.videos.router import router as video_router
from app.api.v1.search.router import router as search_router
from app.api.v1.analytics.router import router as analytics_router


api_router = APIRouter()

# Подключение эндпоинтов API
api_router.include_router(products_router, prefix="/products", tags=["products"])
api_router.include_router(categories_router, prefix="/categories", tags=["categories"])
api_router.include_router(catalogs_router, prefix="/catalogs", tags=["catalogs"])
api_router.include_router(import_r_router, prefix="/import_r_router", tags=["import_r_router"])
api_router.include_router(import_l_router, prefix="/import_l_router", tags=["import_l_router"])
api_router.include_router(brands_router, prefix="/brands", tags=["brands"])
api_router.include_router(video_router, prefix="/videos", tags=["videos"])
api_router.include_router(search_router, prefix="/search", tags=["search"])
api_router.include_router(analytics_router, prefix="/analytics", tags=["analytics"])