"""
Generador de dataset sintético: Temperatura vs Uso de Redes Sociales.

Basado en hipótesis de estudios reales sobre comportamiento digital:
- Temperaturas extremas (muy frías o muy calientes) -> mayor uso (gente adentro)
- Temperaturas agradables (18-25°C) -> menor uso (gente afuera)
- Horario nocturno (19-23h) -> pico de uso
- Fin de semana -> patrones diferentes a días laborales
- Combinación de efecto lineal moderado + efecto no lineal (curva en U)
"""
import numpy as np
import pandas as pd
from pathlib import Path

OUTPUT_PATH = Path("data/clima_redes_sociales.csv")


def generate_dataset(n_samples: int = 8000, seed: int = 42, output_path: Path = OUTPUT_PATH) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    # === Features ===
    temperatures = rng.uniform(-5, 40, n_samples)
    hours = rng.integers(0, 24, n_samples)
    days_of_week = rng.integers(0, 7, n_samples)  # 0=Lunes, 6=Domingo
    is_weekend = (days_of_week >= 5).astype(int)
    humidity = rng.uniform(20, 95, n_samples)

    # === Efectos sobre el uso ===
    # Curva en U centrada en 22°C (punto de mayor comodidad afuera)
    temp_nonlinear = ((temperatures - 22) ** 2) * 0.10
    # Pequeño efecto lineal: hace más calor -> ligero aumento (AC, quedarse adentro)
    temp_linear = (temperatures - 22) * 0.35

    # Pico nocturno alrededor de las 21h
    hour_effect = 28 * np.exp(-((hours - 21) ** 2) / 18)
    # Pico secundario por la mañana (8h)
    hour_effect += 7 * np.exp(-((hours - 8) ** 2) / 4)

    # Fin de semana: más tiempo libre
    weekend_effect = is_weekend * rng.uniform(5, 18, n_samples)

    # Humedad alta tiende a aumentar permanencia en interior
    humidity_effect = (humidity - 60) * 0.05

    # === Target principal: minutos de uso ===
    usage_minutes = (
        22  # baseline
        + temp_nonlinear
        + temp_linear
        + hour_effect
        + weekend_effect
        + humidity_effect
        + rng.normal(0, 7, n_samples)  # ruido
    )
    usage_minutes = np.clip(usage_minutes, 0, 240)

    # === Targets derivados ===
    posts = usage_minutes * 0.08 + rng.normal(0, 1.5, n_samples)
    posts = np.clip(posts, 0, 30).astype(int)

    engagement = usage_minutes * 1.6 + posts * 3 + rng.normal(0, 10, n_samples)
    engagement = np.clip(engagement, 0, 600).astype(int)

    df = pd.DataFrame({
        "temperatura_c": temperatures.round(2),
        "humedad_pct": humidity.round(1),
        "hora": hours,
        "dia_semana": days_of_week,
        "es_fin_semana": is_weekend,
        "uso_minutos": usage_minutes.round(1),
        "posts_publicados": posts,
        "engagement": engagement,
    })

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)

    print(f"[OK] Dataset generado: {output_path}")
    print(f"     Filas: {len(df)}")
    print(f"     Correlacion Pearson temperatura <-> uso: {df['temperatura_c'].corr(df['uso_minutos']):.4f}")
    print(f"     (Pearson baja porque la relacion es no-lineal en forma de U)")
    return df


if __name__ == "__main__":
    generate_dataset()
