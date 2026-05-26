"""
Esquemas Pydantic para validacion de requests y responses.
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


# === Auth ===
class RegisterIn(BaseModel):
    username: str = Field(min_length=3, max_length=40)
    email: str
    password: str = Field(min_length=4, max_length=100)


class LoginIn(BaseModel):
    username: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str


# === Prediccion ===
class PredictIn(BaseModel):
    temperatura_c: float = Field(ge=-20, le=50, description="Temperatura en grados Celsius")
    humedad_pct: float = Field(default=60, ge=0, le=100, description="Humedad relativa")
    hora: int = Field(ge=0, le=23, description="Hora del dia 0-23")
    dia_semana: int = Field(ge=0, le=6, description="0=Lunes, 6=Domingo")


class PredictOut(BaseModel):
    uso_minutos_predicho: float
    posts_predichos: int
    engagement_predicho: int
    interpretacion: str


# === Analitica ===
class EventIn(BaseModel):
    event_type: str = Field(description="screen_view, prediction, login, button_tap, etc.")
    screen: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EventOut(BaseModel):
    id: str
    username: str
    event_type: str
    screen: Optional[str]
    metadata: Dict[str, Any]
    timestamp: datetime
