# API Clima vs Redes Sociales — Backend

Servicio REST desarrollado en FastAPI para el análisis predictivo del impacto de variables climáticas sobre métricas de uso de redes sociales. Forma parte del proyecto final del curso 125 — Programación de Páginas Electrónicas y Aplicaciones Móviles, carrera Ingeniería en Ciencia de Datos y Analítica, Universidad Mariano Gálvez de Guatemala.

## Descripción funcional

El backend expone una API HTTP con tres capacidades principales:

1. Autenticación de usuarios mediante JSON Web Tokens firmados con HS256.
2. Predicción multi-output (minutos de uso, publicaciones, engagement) a partir de un modelo de Random Forest entrenado sobre un dataset sintético derivado de hipótesis de estudios de comportamiento digital.
3. Registro y consulta de eventos de telemetría provenientes de la aplicación móvil cliente.

La persistencia de usuarios, eventos y predicciones se realiza sobre MongoDB Atlas. Los artefactos del modelo (CSV de entrenamiento y bundle joblib) se generan en tiempo de build.

## Stack tecnológico

| Componente | Tecnología |
|------------|------------|
| Framework HTTP | FastAPI 0.115 |
| Servidor ASGI | Uvicorn |
| Autenticación | PyJWT + bcrypt |
| Base de datos | MongoDB Atlas (pymongo) |
| Modelo predictivo | scikit-learn (RandomForestRegressor multi-output) |
| Procesamiento de datos | pandas, numpy |
| Hosting | Render.com (plan free) |
| Python | 3.11 |

## Estructura del proyecto

```
backend/
├── main.py                   API y definición de endpoints
├── auth.py                   Hashing de contraseñas y emisión de JWT
├── database.py               Cliente MongoDB y helpers por colección
├── schemas.py                Modelos Pydantic de entrada y salida
├── ml_model.py               Entrenamiento, persistencia y predicción
├── dataset_generator.py      Generación del dataset sintético
├── requirements.txt          Dependencias pineadas
├── render.yaml               Blueprint de despliegue
├── .env.example              Plantilla de variables de entorno
├── .gitignore
└── data/
    ├── clima_redes_sociales.csv    (generado)
    └── model.joblib                (generado)
```

## Prerequisitos

- Python 3.11
- Cuenta en MongoDB Atlas con un cluster M0 aprovisionado
- Cuenta en GitHub
- Cuenta en Render.com

## Instalación local

```bash
python -m venv venv
source venv/bin/activate      # Linux/macOS
venv\Scripts\activate         # Windows

pip install -r requirements.txt
```

## Variables de entorno

Copiar `.env.example` a `.env` y completar:

| Variable | Descripción |
|----------|-------------|
| `MONGO_URI` | Connection string SRV de MongoDB Atlas |
| `MONGO_DB` | Nombre de la base de datos (por defecto `clima_redes`) |
| `JWT_SECRET` | Secreto para firmar tokens, mínimo recomendado 32 caracteres |

## Ejecución

```bash
uvicorn main:app --reload
```

En el primer arranque, si los archivos `data/clima_redes_sociales.csv` y `data/model.joblib` no existen, se generan automáticamente: dataset de 8000 registros y modelo entrenado con un 20% de holdout para evaluación. Las ejecuciones posteriores reutilizan los artefactos persistidos.

Documentación interactiva (OpenAPI / Swagger UI) disponible en `http://localhost:8000/docs`.

## Configuración de MongoDB Atlas

1. Crear un cluster M0 en https://cloud.mongodb.com.
2. En `Database Access`, crear un usuario con privilegios de lectura y escritura.
3. En `Network Access`, agregar la entrada `0.0.0.0/0` para permitir conexiones entrantes desde Render.
4. Desde el botón `Connect > Drivers > Python`, copiar el connection string SRV y reemplazar `<db_password>` por la contraseña real del usuario creado.

## Despliegue en Render

El repositorio incluye `render.yaml` con la definición completa del Blueprint. Procedimiento:

1. Push del repositorio a GitHub.
2. En Render: `Add new > Blueprint > Connect repository`.
3. Render detecta el `render.yaml` y solicita los valores de las variables marcadas con `sync: false`. Pegar el connection string en `MONGO_URI`.
4. Las variables `JWT_SECRET` se autogenera, `MONGO_DB` y `PYTHON_VERSION` quedan definidas por el Blueprint.
5. Confirmar y aplicar.

El comando de build instala dependencias, ejecuta el generador del dataset y entrena el modelo, dejando los artefactos disponibles antes del start. Duración aproximada del primer deploy: 5 a 8 minutos.

El plan free de Render suspende la instancia tras 15 minutos sin tráfico. El primer request posterior a la suspensión tarda aproximadamente 30 segundos en responder mientras el servicio se reactiva.

## Endpoints

| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| GET    | `/`                    | No | Health check y estado de la conexión a MongoDB |
| POST   | `/auth/register`       | No | Registro de usuario |
| POST   | `/auth/login`          | No | Autenticación y emisión de token |
| POST   | `/predict`             | Sí | Predicción de uso, publicaciones y engagement |
| GET    | `/correlation`         | No | Coeficientes de correlación Pearson |
| GET    | `/model/info`          | No | Metadatos del modelo y métricas de validación |
| POST   | `/analytics/log`       | Sí | Registro de evento de telemetría |
| GET    | `/analytics/summary`   | No | Agregados por tipo de evento, pantalla y fecha |
| GET    | `/analytics/events`    | No | Listado paginado de eventos |
| GET    | `/data/insights`       | No | Agregados del dataset por rango térmico, hora y día |
| GET    | `/data/scatter`        | No | Muestra para gráfico de dispersión |

## Pruebas

### Registro y obtención de token

```bash
curl -X POST https://<host>/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"luis","email":"luis@umg.edu","password":"1234"}'
```

Respuesta:

```json
{"access_token":"eyJhbGc...","token_type":"bearer","username":"luis"}
```

### Predicción

```bash
curl -X POST https://<host>/predict \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"temperatura_c":35,"humedad_pct":70,"hora":21,"dia_semana":5}'
```

### Correlaciones

```bash
curl https://<host>/correlation
```

### Registro de evento de telemetría

```bash
curl -X POST https://<host>/analytics/log \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"event_type":"screen_view","screen":"prediction","metadata":{}}'
```

## Modelo predictivo

- Algoritmo: `RandomForestRegressor` multi-output (scikit-learn).
- Hiperparámetros: 150 estimadores, profundidad máxima 14, mínimo 3 muestras por hoja, semilla fija 42.
- Features: temperatura (°C), humedad relativa (%), hora del día (0–23), día de la semana (0=Lunes, 6=Domingo), indicador binario de fin de semana.
- Targets: minutos de uso diario, número de publicaciones, engagement total (suma de likes y comentarios).
- Métricas sobre conjunto de validación (20% holdout):
  - `uso_minutos`: R² ≈ 0.87, MAE ≈ 6.2 minutos.
  - `engagement`: R² ≈ 0.80, MAE ≈ 14.7 interacciones.
  - `posts_publicados`: R² ≈ 0.50 (variable con mayor componente estocástico).

Observación metodológica: la correlación lineal (Pearson) entre temperatura y minutos de uso es de magnitud moderada (~0.33 en valor absoluto), debido a que la relación subyacente es no lineal y de forma cuasi-cuadrática con mínimo cercano a la temperatura de confort (22 °C). Un modelo lineal subestima esta dependencia; el ensamble de árboles la captura adecuadamente.

## Dataset

Dataset sintético de 8000 observaciones generado de manera determinística (semilla fija = 42) a partir de un modelo paramétrico que combina:

- Componente no lineal de temperatura centrada en 22 °C, representando la zona de confort térmico.
- Componente lineal moderado, asociado al uso de climatización en interiores.
- Patrón circadiano con pico nocturno alrededor de las 21h y pico matutino secundario.
- Efecto incremental en fines de semana.
- Efecto marginal de humedad relativa.
- Ruido gaussiano residual.

La generación es reproducible. La especificación completa se encuentra en `dataset_generator.py`.

## Autor

Luis Chali — Ingeniería en Ciencia de Datos y Analítica
Universidad Mariano Gálvez de Guatemala, 2026
