# Backend — Clima vs Redes Sociales

API FastAPI para el proyecto final de Programación de Páginas Electrónicas y Aplicaciones Móviles.
**Contexto:** análisis del impacto de la temperatura del clima en el uso de redes sociales.

---

## 📦 Estructura

```
backend/
├── main.py                  # API FastAPI (endpoints)
├── auth.py                  # JWT + bcrypt
├── database.py              # Conexión MongoDB Atlas
├── schemas.py               # Pydantic models
├── ml_model.py              # Entrenamiento y predicción
├── dataset_generator.py     # Genera CSV sintético
├── requirements.txt
├── render.yaml              # Configuración Render.com
├── .env.example
└── data/
    ├── clima_redes_sociales.csv   (generado)
    └── model.joblib                (generado)
```

---

## 🚀 Correr en local

### 1. Crear entorno virtual e instalar dependencias

```bash
python -m venv venv

# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Configurar variables de entorno

Copia `.env.example` a `.env` y completa:
- `MONGO_URI` — connection string de MongoDB Atlas (ver más abajo)
- `JWT_SECRET` — un string aleatorio largo

En Windows PowerShell, antes de correr:
```powershell
$env:MONGO_URI="mongodb+srv://..."
$env:JWT_SECRET="mi-secreto-super-largo"
```

En bash:
```bash
export MONGO_URI="mongodb+srv://..."
export JWT_SECRET="mi-secreto-super-largo"
```

### 3. Levantar el servidor

```bash
uvicorn main:app --reload
```

En el primer arranque genera automáticamente el dataset (~8000 filas) y entrena el modelo (~30 segundos). Las próximas veces ya están cacheados.

Abrir: **http://localhost:8000/docs** → Swagger UI interactivo.

---

## 🗄️ Configurar MongoDB Atlas (gratis)

1. Ir a https://cloud.mongodb.com → registrarse
2. Crear un **Cluster M0 (Free)** — región más cercana
3. **Database Access** → crear usuario con password
4. **Network Access** → Add IP → `0.0.0.0/0` (allow from anywhere)
5. **Connect** → Drivers → Python → copiar el connection string
6. Reemplazar `<password>` por la password real del usuario que creaste
7. Pegar en tu `.env` como `MONGO_URI`

---

## ☁️ Desplegar en Render.com

### Opción A — con render.yaml (recomendado)

1. Subir esta carpeta a un repositorio de GitHub
2. Ir a https://render.com → New → Blueprint
3. Conectar el repo → Render detecta `render.yaml`
4. Te pedirá rellenar el `MONGO_URI` (porque tiene `sync: false`) — pégalo
5. Deploy automático

### Opción B — manual

1. https://render.com → New → Web Service
2. Conectar repo
3. Configurar:
   - **Build Command:** `pip install -r requirements.txt && python dataset_generator.py && python ml_model.py`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Environment Variables:**
     - `MONGO_URI` = tu connection string
     - `MONGO_DB` = `clima_redes`
     - `JWT_SECRET` = string aleatorio largo
4. Deploy

Te queda una URL pública estilo: `https://clima-redes-api.onrender.com`

> ⚠️ **Nota Render free:** la instancia se "duerme" tras 15 min sin tráfico y tarda ~30s en despertar al primer request. Para la demo, hacer un request de "calentamiento" antes de empezar.

---

## 🧪 Probar la API

### Con el Swagger UI
Abrir `/docs` y probar interactivamente todos los endpoints.

### Con curl

**1. Registrar usuario**
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"luis","email":"luis@umg.edu","password":"1234"}'
```

Respuesta:
```json
{"access_token":"eyJhbGc...", "token_type":"bearer", "username":"luis"}
```

**2. Login (si ya existe el usuario)**
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"luis","password":"1234"}'
```

**3. Predicción** (usar el token del paso anterior)
```bash
TOKEN="eyJhbGc..."
curl -X POST http://localhost:8000/predict \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"temperatura_c":35,"humedad_pct":70,"hora":21,"dia_semana":5}'
```

**4. Correlaciones**
```bash
curl http://localhost:8000/correlation
```

**5. Insights del dataset**
```bash
curl http://localhost:8000/data/insights
```

**6. Registrar evento (analítica)**
```bash
curl -X POST http://localhost:8000/analytics/log \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"event_type":"screen_view","screen":"prediction","metadata":{"source":"test"}}'
```

**7. Resumen de analítica**
```bash
curl http://localhost:8000/analytics/summary
```

---

## 📋 Endpoints disponibles

| Método | Endpoint | Auth | Descripción |
|--------|----------|------|-------------|
| GET    | `/`                    | No  | Health check |
| POST   | `/auth/register`       | No  | Registrar usuario |
| POST   | `/auth/login`          | No  | Iniciar sesión |
| POST   | `/predict`             | Sí  | Predecir uso de redes |
| GET    | `/correlation`         | No  | Correlaciones Pearson |
| GET    | `/model/info`          | No  | Info y métricas del modelo |
| POST   | `/analytics/log`       | Sí  | Registrar evento de la app móvil |
| GET    | `/analytics/summary`   | No  | Resumen agregado de eventos |
| GET    | `/analytics/events`    | No  | Listado paginado de eventos |
| GET    | `/data/insights`       | No  | Insights del dataset histórico |
| GET    | `/data/scatter`        | No  | Muestra para gráfico de dispersión |

---

## 🧠 Sobre el modelo

- **Tipo:** RandomForestRegressor (multi-output)
- **Features:** temperatura, humedad, hora, día de la semana, es fin de semana
- **Targets:** minutos de uso, posts publicados, engagement
- **Métricas típicas tras entrenar:** R² > 0.80 para uso_minutos
- **Hallazgo clave:** la correlación lineal (Pearson) temperatura ↔ uso es **baja**, porque la relación real es **no-lineal en forma de U** (más uso en extremos térmicos). El Random Forest captura este patrón que un modelo lineal no podría.

Este hallazgo es excelente para vender la presentación ejecutiva: "Un análisis lineal habría concluido que no hay relación. Nuestro modelo no lineal demuestra que sí la hay, y la cuantifica."
