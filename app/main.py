import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.routes import main_router
from config import BASE_DIR, STATIC_DIR, TEMPLATES_DIR, logger

app = FastAPI()

# Absoluten Pfad für statische Dateien festlegen
static_path = os.path.join(BASE_DIR, "app", "static")
if not os.path.exists(static_path):
    logger.error(f"Static path does not exist: {static_path}")
    raise RuntimeError(f"Static path does not exist: {static_path}")
else:
    logger.info(f"Mounting static files from: {static_path}")

# Mounten der statischen Dateien
app.mount("/static", StaticFiles(directory=static_path), name="static")
logger.info("Static files mounted successfully.")

# Inkludieren des Routers nach dem Mounten der statischen Dateien
app.include_router(main_router)
