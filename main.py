"""
API Clima vs Redes Sociales
Proyecto Final - Programacion de Paginas Electronicas y Aplicaciones Moviles
Luis Chali - UMG 2026
"""
# Cargar variables de entorno desde .env si existe (solo para dev local)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from contextlib import asynccontextmanager
from pathlib import Path
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware

from database import users_col, events_col, predictions_col, ping
from auth import hash_password, verify_password, create_token, current_user
from schemas import RegisterIn, LoginIn, TokenOut, PredictIn, PredictOut, EventIn
import ml_model


# ===== Ciclo de vida =====
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: garantizar dataset + modelo
    if not Path("data/clima_redes_sociales.csv").exists():
        print("[startup] Dataset ausente, generando...")
        import dataset_generator
        dataset_generator.generate_dataset()
    if not Path("data/model.joblib").exists():
        print("[startup] Modelo ausente, entrenando...")
        ml_model.train_model()
    ml_model.load_model()
    print("[startup] Backend listo")
    yield
    # Shutdown
    print("[shutdown] Cerrando backend")


app = FastAPI(
    title="API Clima vs Redes Sociales",
    description=(
        "API para analisis predictivo del uso de redes sociales en funcion "
        "de variables climaticas (temperatura, humedad) y temporales (hora, dia)."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS abierto para la app web React y app movil Android
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===== Health =====
@app.get("/", tags=["health"])
def root():
    return {
        "service": "API Clima vs Redes Sociales",
        "version": "1.0.0",
        "status": "online",
        "mongo_connected": ping(),
        "docs": "/docs",
    }


# ===== Auth =====
@app.post("/auth/register", response_model=TokenOut, tags=["auth"])
def register(payload: RegisterIn):
    if users_col().find_one({"username": payload.username}):
        raise HTTPException(status_code=400, detail="El usuario ya existe")
    users_col().insert_one({
        "username": payload.username,
        "email": payload.email,
        "password_hash": hash_password(payload.password),
        "created_at": datetime.now(timezone.utc),
    })
    return TokenOut(access_token=create_token(payload.username), username=payload.username)


@app.post("/auth/login", response_model=TokenOut, tags=["auth"])
def login(payload: LoginIn):
    user = users_col().find_one({"username": payload.username})
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Credenciales invalidas")
    return TokenOut(access_token=create_token(payload.username), username=payload.username)


# ===== Prediccion =====
@app.post("/predict", response_model=PredictOut, tags=["model"])
def predict(payload: PredictIn, user: str = Depends(current_user)):
    result = ml_model.predict(payload.model_dump())

    minutos = result["uso_minutos_predicho"]
    if minutos < 30:
        interp = "Uso bajo esperado. Condiciones agradables, probable actividad al aire libre."
    elif minutos < 70:
        interp = "Uso moderado esperado. Comportamiento tipico de consumo digital."
    else:
        interp = "Uso alto esperado. Temperatura extrema u hora pico de consumo digital."

    result["interpretacion"] = interp

    # Log de la prediccion (best-effort, no rompe si Mongo no esta disponible)
    try:
        predictions_col().insert_one({
            "username": user,
            "input": payload.model_dump(),
            "output": result,
            "timestamp": datetime.now(timezone.utc),
        })
    except Exception as e:
        print(f"[WARN] No se pudo registrar prediccion en Mongo: {e}")

    return PredictOut(**result)


@app.get("/correlation", tags=["model"])
def correlation():
    """Correlacion de Pearson entre temperatura y metricas de uso."""
    return {
        "descripcion": (
            "Correlacion lineal (Pearson) entre temperatura y metricas de redes sociales. "
            "Una correlacion baja NO implica ausencia de relacion: la relacion real es no-lineal "
            "(curva en U), capturada por el modelo de Random Forest."
        ),
        "correlaciones": ml_model.compute_correlation(),
    }


@app.get("/model/info", tags=["model"])
def model_info():
    bundle = ml_model.load_model()
    return {
        "tipo_modelo": "RandomForestRegressor (multi-output)",
        "features": bundle["features"],
        "targets": bundle["targets"],
        "metricas": bundle["metrics"],
    }


# ===== Analitica =====
@app.post("/analytics/log", tags=["analytics"])
def log_event(event: EventIn, user: str = Depends(current_user)):
    doc = {
        "username": user,
        "event_type": event.event_type,
        "screen": event.screen,
        "metadata": event.metadata,
        "timestamp": datetime.now(timezone.utc),
    }
    res = events_col().insert_one(doc)
    return {"id": str(res.inserted_id), "ok": True}


@app.get("/analytics/summary", tags=["analytics"])
def analytics_summary():
    """Resumen agregado de uso de la app movil. Publico para alimentar el dashboard web."""
    col = events_col()

    total = col.count_documents({})
    unique_users = len(col.distinct("username"))

    by_type = list(col.aggregate([
        {"$group": {"_id": "$event_type", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]))

    by_screen = list(col.aggregate([
        {"$match": {"screen": {"$ne": None}}},
        {"$group": {"_id": "$screen", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]))

    by_day = list(col.aggregate([
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$timestamp"}},
            "count": {"$sum": 1},
        }},
        {"$sort": {"_id": 1}},
        {"$limit": 30},
    ]))

    return {
        "total_eventos": total,
        "usuarios_unicos": unique_users,
        "por_tipo": [{"tipo": x["_id"], "count": x["count"]} for x in by_type],
        "por_pantalla": [{"pantalla": x["_id"], "count": x["count"]} for x in by_screen],
        "por_dia": [{"fecha": x["_id"], "count": x["count"]} for x in by_day],
    }


@app.get("/analytics/events", tags=["analytics"])
def analytics_events(
    limit: int = Query(50, ge=1, le=500),
    skip: int = Query(0, ge=0),
):
    cursor = events_col().find().sort("timestamp", -1).skip(skip).limit(limit)
    items = []
    for doc in cursor:
        items.append({
            "id": str(doc["_id"]),
            "username": doc["username"],
            "event_type": doc["event_type"],
            "screen": doc.get("screen"),
            "metadata": doc.get("metadata", {}),
            "timestamp": doc["timestamp"].isoformat(),
        })
    return {"items": items, "total_devueltos": len(items), "limit": limit, "skip": skip}


# ===== Datos historicos (para graficos del dashboard) =====
@app.get("/data/insights", tags=["data"])
def data_insights():
    """Insights agregados del dataset historico para visualizacion en el dashboard."""
    import pandas as pd
    df = pd.read_csv("data/clima_redes_sociales.csv")

    df["rango_temp"] = pd.cut(
        df["temperatura_c"],
        bins=[-10, 5, 15, 22, 28, 35, 50],
        labels=["Muy frio (<5C)", "Frio (5-15C)", "Agradable (15-22C)",
                "Calido (22-28C)", "Caluroso (28-35C)", "Muy caluroso (>35C)"],
    )

    avg_by_temp = df.groupby("rango_temp", observed=True)["uso_minutos"].mean().round(2).to_dict()
    avg_by_hour = df.groupby("hora")["uso_minutos"].mean().round(2).to_dict()
    avg_by_dow = df.groupby("dia_semana")["uso_minutos"].mean().round(2).to_dict()

    dias_nombre = ["Lunes", "Martes", "Miercoles", "Jueves", "Viernes", "Sabado", "Domingo"]

    return {
        "total_muestras": len(df),
        "uso_promedio_por_rango_temp": [
            {"rango": k, "uso_minutos": v} for k, v in avg_by_temp.items()
        ],
        "uso_promedio_por_hora": [
            {"hora": int(k), "uso_minutos": v} for k, v in avg_by_hour.items()
        ],
        "uso_promedio_por_dia": [
            {"dia": dias_nombre[int(k)], "uso_minutos": v} for k, v in avg_by_dow.items()
        ],
    }


@app.get("/data/scatter", tags=["data"])
def data_scatter(sample: int = Query(500, ge=50, le=2000)):
    """Muestra de pares (temperatura, uso) para grafico de dispersion."""
    import pandas as pd
    df = pd.read_csv("data/clima_redes_sociales.csv").sample(sample, random_state=42)
    return {
        "puntos": [
            {"temperatura": float(row.temperatura_c), "uso_minutos": float(row.uso_minutos)}
            for row in df.itertuples()
        ]
    }
