# app/schemas/home.py
from pydantic import BaseModel
from typing import List
from app.schemas.banner import BannerRead
from app.schemas.promotion import PromotionRead
from app.schemas.category import CategoryRead

class HomePageData(BaseModel):
    banners: List[BannerRead]
    promotions: List[PromotionRead]
    categories: List[CategoryRead]