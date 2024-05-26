from quart import Quart

from app.main.routes import main


def create_app():
    app = Quart(__name__)
    app.register_blueprint(main)
    return app
