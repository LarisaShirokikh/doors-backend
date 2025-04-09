from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.docs import get_swagger_ui_html

from app.api.v1.router import api_router
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="API для интернет-магазина дверей",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Включение API роутеров
app.include_router(api_router, prefix="/api/v1")

# Подключение статических файлов
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/media", StaticFiles(directory="media"), name="media")

@app.get("/")
async def root():
    """
    Корневой эндпоинт, возвращающий информацию о приложении
    """
    return {
        "app_name": settings.PROJECT_NAME,
        "version": "1.0.0",
        "api_docs": "/docs",
        "status": "online"
    }

@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    """
    Кастомная страница Swagger UI
    """
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - API Documentation",
        swagger_js_url="/static/swagger-ui-bundle.js",
        swagger_css_url="/static/swagger-ui.css",
    )

@app.get("/health")
async def health_check():
    """
    Эндпоинт для проверки работоспособности сервиса
    """
    return {"status": "healthy"}