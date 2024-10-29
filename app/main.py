from fastapi import FastAPI
from app.routes import main_router

app = FastAPI()

app.include_router(main_router)
