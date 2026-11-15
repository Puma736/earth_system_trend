# app/main.py
from fastapi import FastAPI
from .database import Base, engine
from .routers import tasks

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Task Manager API", version="1.0.0")
app.include_router(tasks.router)


@app.get("/health")
def health():
    return {"status": "ok"}
