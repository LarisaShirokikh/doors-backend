from fastapi import APIRouter
from app.api.v1.manufacturers.router import router as manufacturers_router
from app.api.v1.catalogs.router import router as catalogs_router
from app.api.v1.categories.router import router as categories_router
from app.api.v1.import_r.router import router as import_r_router
from app.api.v1.import_l.router import router as import_l_router
from app.api.v1.products.router import router as products_router
from app.api.v1.home.router import router as home_router
from app.api.v1.tips.router import router as tips_router


api_router = APIRouter()

# Подключение эндпоинтов API
api_router.include_router(products_router, prefix="/products", tags=["products"])
api_router.include_router(categories_router, prefix="/categories", tags=["categories"])
api_router.include_router(catalogs_router, prefix="/catalogs", tags=["catalogs"])
api_router.include_router(manufacturers_router, prefix="/manufacturers", tags=["manufacturers"])
api_router.include_router(import_r_router, prefix="/import_r_router", tags=["import_r_router"])
api_router.include_router(import_l_router, prefix="/import_l_router", tags=["import_l_router"])
api_router.include_router(home_router, prefix="/home", tags=["home"])
api_router.include_router(tips_router, prefix="/tips", tags=["tips"])