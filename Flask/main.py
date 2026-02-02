import os
from dotenv import load_dotenv

# Load .env from parent directory
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(os.path.dirname(basedir), '.env'))

# Force DB_HOST to localhost for local execution if it's set to 'db' (common in docker-compose)
# But NOT if we are actually running inside Docker
if os.getenv('RUNNING_IN_DOCKER'):
    # In Docker, we MUST use the service name 'db' regardless of what .env says
    os.environ['DB_HOST'] = 'db'
elif os.getenv('DB_HOST') == 'db':
    # Local execution, if .env says 'db', fallback to localhost
    os.environ['DB_HOST'] = 'localhost'

from app import create_app
app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)