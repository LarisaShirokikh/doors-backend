# app/models/tip.py
from sqlalchemy import Column, Integer, String, Text
from app.core.database import Base

class Tip(Base):
    __tablename__ = "tips"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    image = Column(String(255), nullable=True)
    content = Column(Text, nullable=True)