import os
from dotenv import load_dotenv

# Load .env from parent directory
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(os.path.dirname(basedir), '.env'))

# Force DB_HOST to localhost for local execution if it's set to 'db' (common in docker-compose)
# But NOT if we are actually running inside Docker
in_docker = os.path.exists('/.dockerenv')
if os.getenv('RUNNING_IN_DOCKER') and in_docker:
    # In Docker, we MUST use the service name 'db'
    os.environ['DB_HOST'] = 'db'
elif os.getenv('DB_HOST') == 'db' or not os.getenv('DB_HOST'):
    # Local execution: use localhost
    os.environ['DB_HOST'] = 'localhost'

print(f"[DB] main.py DB_HOST={os.getenv('DB_HOST')} user={os.getenv('POSTGRES_USER')} db={os.getenv('DATABASE_NAME')}")

from app import create_app
app = create_app()

if __name__ == '__main__':
    enable_https = os.getenv('ENABLE_HTTPS') == '1'
    cert_file = os.getenv('SSL_CERT_FILE')
    key_file = os.getenv('SSL_KEY_FILE')
    if enable_https and cert_file and key_file and os.path.exists(cert_file) and os.path.exists(key_file):
        print(f"[HTTPS] Ativado com cert={cert_file} key={key_file}")
        app.run(host='0.0.0.0', port=5000, debug=True, ssl_context=(cert_file, key_file))
    else:
        app.run(host='0.0.0.0', port=5000, debug=True)