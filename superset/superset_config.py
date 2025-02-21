import os
from dotenv import load_dotenv

load_dotenv()

# Database configurations (make sure these match your docker-compose settings)
SQLALCHEMY_DATABASE_URI = os.getenv('SUPERSET_DATABASE_URL', 'postgresql://user:password@localhost:5432/superset')
SQLALCHEMY_TRACK_MODIFICATIONS = False

# SECRET_KEY setup from environment variable
SECRET_KEY = os.getenv('SUPERSET_SECRET_KEY', 'default_secret_key')
print(SECRET_KEY)  # Use env variable here

SUPERSET_DATA_DIR = os.getenv('SUPERSET_DATA_DIR', '/app/superset_data')

# Flask configurations
FLASK_ENV = os.getenv('FLASK_ENV', 'production')

# Enable CSRF protection
WTF_CSRF_ENABLED = True

# Other optional configurations
CACHE_CONFIG = {
    'CACHE_TYPE': 'redis',  # You can use a different cache type if needed
    'CACHE_DEFAULT_TIMEOUT': 300,
}

# Logging configurations
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        },
    },
    'handlers': {
        'file': {
            'class': 'logging.FileHandler',
            'filename': '/app/superset/superset.log',
            'formatter': 'default',
        },
    },
    'loggers': {
        'superset': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Uncomment to enable user authentication
# AUTH_TYPE = 1
# AUTH_USER_REGISTRATION = True