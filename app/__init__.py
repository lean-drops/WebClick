from quart import Quart

from app.routes import main


def create_app():
    app = Quart(__name__)
    app.register_blueprint(main)
    return app
