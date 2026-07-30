"""ASGI entrypoint for TaskHub."""

from taskhub.application import create_app

app = create_app()
