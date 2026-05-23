import redis
import os
import logging
from flask import current_app

logger = logging.getLogger(__name__)

class RedisExtension:
    def __init__(self, app=None):
        self.client = None
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        try:
            self.client = redis.from_url(redis_url)
            # Add to flask extensions dictionary
            if not hasattr(app, 'extensions'):
                app.extensions = {}
            app.extensions['redis_client'] = self.client
            logger.info("Redis conectado com sucesso via Application Factory.")
        except Exception as e:
            logger.error(f"Erro ao conectar ao Redis: {e}", exc_info=True)
            self.client = None

redis_client_ext = RedisExtension()
