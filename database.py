"""
Conexion a MongoDB Atlas.

Variables de entorno requeridas:
    MONGO_URI : Connection string (mongodb+srv://...)
    MONGO_DB  : Nombre de la base de datos (default: clima_redes)
"""
import os
from pymongo import MongoClient

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("MONGO_DB", "clima_redes")

_client = None


def get_client() -> MongoClient:
    global _client
    if _client is None:
        _client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    return _client


def get_db():
    return get_client()[DB_NAME]


def users_col():
    return get_db()["users"]


def events_col():
    return get_db()["analytics_events"]


def predictions_col():
    return get_db()["predictions"]


def ping() -> bool:
    try:
        get_db().command("ping")
        return True
    except Exception as e:
        print(f"[WARN] Mongo ping fallo: {e}")
        return False
