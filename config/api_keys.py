import os
from dotenv import load_dotenv

load_dotenv()

# Coda Configuration
CODA_API_KEY = os.getenv('CODA_API_KEY')
CODA_BASE_URL = 'https://coda.io/apis/v1'

# Slack Configuration
SLACK_BOT_TOKEN = os.getenv('SLACK_BOT_TOKEN')
SLACK_CHANNEL = os.getenv('SLACK_CHANNEL', '#nux-experiments')

# Mode Analytics Configuration
MODE_API_KEY = os.getenv('MODE_API_KEY')
MODE_WORKSPACE = os.getenv('MODE_WORKSPACE', 'doordash')

# Portkey AI Configuration
PORTKEY_API_KEY = os.getenv('PORTKEY_API_KEY')

# Dynamic Values Configuration
DYNAMIC_VALUES_SECRET_KEY = os.getenv('DYNAMIC_VALUES_SECRET_KEY')

# Snowflake Configuration
SNOWFLAKE_CONFIG = {
    'account': os.getenv('SNOWFLAKE_ACCOUNT'),
    'user': os.getenv('SNOWFLAKE_USER'),
    'password': os.getenv('SNOWFLAKE_PASSWORD'),
    'warehouse': os.getenv('SNOWFLAKE_WAREHOUSE'),
    'database': os.getenv('SNOWFLAKE_DATABASE', 'proddb'),
    'schema': os.getenv('SNOWFLAKE_SCHEMA', 'public'),
}

# Database Configuration
DATABASE_URL = os.getenv('DATABASE_URL')

# Application Configuration
ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
TIMEZONE = os.getenv('TIMEZONE', 'America/Los_Angeles')

# Validation
def validate_required_env_vars():
    required_vars = [
        'CODA_API_KEY',
        'SLACK_BOT_TOKEN', 
        'DATABASE_URL'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing_vars)}. "
            f"Please check your .env file."
        )

if __name__ == "__main__":
    validate_required_env_vars()
    print("✅ All required environment variables are set!")
