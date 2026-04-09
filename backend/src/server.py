from pydantic import BaseModel
from fastapi import FastAPI, HTTPException

# formato delle informazioni estratte dal parser
class ParseResponse(BaseModel):
    url: str
    domain: str
    title: str
    html_text: str
    parsed_text: str
    