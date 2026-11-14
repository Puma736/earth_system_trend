# NASA Space

## Frontend

Requiere Node.js y npm.

```powershell
cd front
npm install
npm run dev
```

Abre <http://localhost:3000>.

## Backend (FastAPI)

Requiere Python 3.10 o superior.

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

La API queda disponible en <http://localhost:8000>. La ruta `/health` verifica que esté en funcionamiento y la documentación interactiva está en `/docs`.
