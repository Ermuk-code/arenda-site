"""
ASGI config for arenda_site project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'arenda_site.settings')

django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter
from arenda_site.middleware import JWTAuthMiddleware
from chats.routing import websocket_urlpatterns as chat_websocket_urlpatterns
from notifications.routing import websocket_urlpatterns as notification_websocket_urlpatterns

websocket_urlpatterns = [
    *chat_websocket_urlpatterns,
    *notification_websocket_urlpatterns,
]


application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": JWTAuthMiddleware(
        URLRouter(websocket_urlpatterns)
    ),
})
