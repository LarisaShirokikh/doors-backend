# app/models/banner.py
from sqlalchemy import Column, Integer, String
from app.core.database import Base

class Banner(Base):
    __tablename__ = "banners"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    image = Column(String, nullable=False)
    url = Column(String, nullable=True)