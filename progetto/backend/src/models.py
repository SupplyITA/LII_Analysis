from sqlalchemy import Column, String, DateTime, ForeignKey, Float, Integer
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

class Evaluation(Base):
    __tablename__ = "evaluations"
    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String(767), ForeignKey("web_resources.url"))
    precision_score = Column(Float)
    recall_score = Column(Float)
    f1_score = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

class JudgeEvaluation(Base):
    __tablename__ = "judge_evaluations"
    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String(767), ForeignKey("web_resources.url"))
    model_name = Column(String(255))
    score = Column(Integer) # quello da 1 a 5 restituito da llm judge
    feedback = Column(LONGTEXT)
    created_at = Column(DateTime, default=datetime.utcnow)
