# app/models/promotion.py
from sqlalchemy import Column, Integer, String, Text
from app.core.database import Base

class Promotion(Base):
    __tablename__ = "promotions"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    image = Column(String, nullable=False)
    url = Column(String, nullable=True)