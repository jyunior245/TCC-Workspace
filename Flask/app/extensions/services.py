from app.services.ai_service import HealthAgent
from app.services.voice_service import VoiceService

class ServiceRegistry:
    def __init__(self):
        self.health_agent = None
        self.voice_service = None

    def init_app(self, app):
        
        self.health_agent = HealthAgent()
        self.voice_service = VoiceService(init_pygame=False)
        
        if not hasattr(app, 'extensions'):
            app.extensions = {}
        app.extensions['services'] = self

service_registry = ServiceRegistry()
