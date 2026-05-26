"""
Modelo predictivo: features climaticas y temporales -> uso de redes sociales.

Se usa RandomForestRegressor multi-output para capturar relaciones no lineales.
"""
import joblib
import pandas as pd
from pathlib import Path
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_absolute_error

DATA_PATH = Path("data/clima_redes_sociales.csv")
MODEL_PATH = Path("data/model.joblib")
FEATURE_COLS = ["temperatura_c", "humedad_pct", "hora", "dia_semana", "es_fin_semana"]
TARGET_COLS = ["uso_minutos", "posts_publicados", "engagement"]


def train_model():
    if not DATA_PATH.exists():
        import dataset_generator
        dataset_generator.generate_dataset()

    df = pd.read_csv(DATA_PATH)
    X = df[FEATURE_COLS]
    y = df[TARGET_COLS]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = RandomForestRegressor(
        n_estimators=150,
        max_depth=14,
        min_samples_leaf=3,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    metrics = {}
    for i, col in enumerate(TARGET_COLS):
        metrics[col] = {
            "r2": round(float(r2_score(y_test.iloc[:, i], y_pred[:, i])), 4),
            "mae": round(float(mean_absolute_error(y_test.iloc[:, i], y_pred[:, i])), 4),
        }

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({
        "model": model,
        "features": FEATURE_COLS,
        "targets": TARGET_COLS,
        "metrics": metrics,
    }, MODEL_PATH)

    print(f"[OK] Modelo guardado en {MODEL_PATH}")
    for k, v in metrics.items():
        print(f"     {k}: R2={v['r2']}  MAE={v['mae']}")

    return model, metrics


_bundle_cache = None


def load_model():
    global _bundle_cache
    if _bundle_cache is not None:
        return _bundle_cache
    if not MODEL_PATH.exists():
        train_model()
    _bundle_cache = joblib.load(MODEL_PATH)
    return _bundle_cache


def predict(features: dict) -> dict:
    bundle = load_model()
    model = bundle["model"]

    X = pd.DataFrame([{
        "temperatura_c": features["temperatura_c"],
        "humedad_pct": features.get("humedad_pct", 60),
        "hora": features["hora"],
        "dia_semana": features["dia_semana"],
        "es_fin_semana": 1 if features["dia_semana"] >= 5 else 0,
    }])
    pred = model.predict(X)[0]
    return {
        "uso_minutos_predicho": round(float(pred[0]), 2),
        "posts_predichos": int(round(float(pred[1]))),
        "engagement_predicho": int(round(float(pred[2]))),
    }


def compute_correlation() -> dict:
    df = pd.read_csv(DATA_PATH)
    series = df.corr(numeric_only=True)["temperatura_c"].drop("temperatura_c")
    return {k: round(float(v), 4) for k, v in series.items()}


if __name__ == "__main__":
    train_model()
