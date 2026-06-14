from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class WebResource(Base):
    __tablename__ = "web_resources"

    url = Column(String(767), primary_key=True)
    domain = Column(String(255))
    title = Column(String(2048))
    html_text = Column(LONGTEXT)
    created_at = Column(DateTime, default=datetime.utcnow)

    #relazione uno-a-uno verso la tabella gold_standard (se elimini la risorsa, si elimina anche il GS)
    gold_standard = relationship("GoldStandard", back_populates="web_resource", uselist=False, cascade="all, delete-orphan")

class GoldStandard(Base):
    __tablename__ = "gold_standard"

    url = Column(String(767), ForeignKey("web_resources.url"), primary_key=True)
    gold_text = Column(LONGTEXT)
    created_at = Column(DateTime, default=datetime.utcnow)

    #relazione inversa verso web_resources
    web_resource = relationship("WebResource", back_populates="gold_standard")