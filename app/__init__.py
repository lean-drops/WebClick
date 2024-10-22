from flask import Flask
from app.routes import main

def create_app():
    app = Flask(__name__)  # Ändere Quart zu Flask
    app.register_blueprint(main)
    return app
