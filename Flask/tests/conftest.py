import pytest
import sys
from unittest.mock import MagicMock

# Mock de bibliotecas externas para evitar erros de DLL (Windows) ou de pacotes ausentes no venv local
sys.modules['weasyprint'] = MagicMock()
sys.modules['flask_weasyprint'] = MagicMock()
sys.modules['redis'] = MagicMock()

from flask import Flask

@pytest.fixture
def app():
    """Cria e configura uma nova instância do app para cada teste."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret'
    return app

@pytest.fixture
def client(app):
    """Cria um cliente de teste para o app."""
    return app.test_client()

@pytest.fixture
def mock_db_session(mocker):
    """Mocks de sessão do banco de dados SQLAlchemy."""
    return mocker.patch('app.extensions.sql_alchemy.db.session')

@pytest.fixture
def mock_auth_admin(mocker):
    """Mocks de auth_admin do Firebase."""
    return mocker.patch('app.extensions.firebase_config.auth_admin')
