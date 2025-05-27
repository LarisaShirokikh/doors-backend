# app/models/product_video.py
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class ProductVideo(Base):
    __tablename__ = "product_videos"

    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    description = Column(String, nullable=False)
    price = Column(Integer, nullable=False)
    video_url = Column(String, nullable=False)

    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    product = relationship("Product", back_populates="product_video_items")