import asyncio
from asgiref.wsgi import WsgiToAsgi
from starlette.middleware.wsgi import WSGIMiddleware

class ASGItoWSGI:
    def __init__(self, app):
        self.asgi_app = app
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.asgi_to_wsgi = WsgiToAsgi(app)

    def __call__(self, environ, start_response):
        return self.asgi_to_wsgi(environ, start_response)

# Beispiel für die Nutzung:
# from app.main import app  # Ihre FastAPI-App
# application = ASGItoWSGI(app)
