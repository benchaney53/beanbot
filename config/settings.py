import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class BotConfig:
    """Bot configuration class"""
    
    # Discord Bot Settings
    DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
    DISCORD_GUILD_ID = os.getenv('DISCORD_GUILD_ID')
    DISCORD_CLIENT_ID = os.getenv('DISCORD_CLIENT_ID')
    
    # Google Sheets Settings
    GOOGLE_CREDENTIALS_FILE = os.getenv('GOOGLE_CREDENTIALS_FILE', 'google_credentials.json')
    GOOGLE_SHEET_ID = os.getenv('GOOGLE_SHEET_ID')
    
    # Bot Settings
    COMMAND_PREFIX = os.getenv('COMMAND_PREFIX', '!')
    BOT_NAME = os.getenv('BOT_NAME', 'Bean Bot')
    BOT_VERSION = os.getenv('BOT_VERSION', '1.0.0')
    
    # Dyno Applications Settings
    ANNOUNCEMENT_CHANNEL_ID = os.getenv('ANNOUNCEMENT_CHANNEL_ID')
    APPROVED_ROLE_ID = os.getenv('APPROVED_ROLE_ID')
    PENDING_ROLE_ID = os.getenv('PENDING_ROLE_ID')
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
    @classmethod
    def validate_config(cls):
        """Validate that required configuration is present"""
        required_vars = ['DISCORD_TOKEN', 'GOOGLE_SHEET_ID']
        missing_vars = []
        
        for var in required_vars:
            if not getattr(cls, var):
                missing_vars.append(var)
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        # Check if Google credentials file exists
        if not os.path.exists(cls.GOOGLE_CREDENTIALS_FILE):
            raise FileNotFoundError(f"Google credentials file not found: {cls.GOOGLE_CREDENTIALS_FILE}")
        
        return True
