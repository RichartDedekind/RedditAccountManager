"""
Configuration management for Reddit Account Manager
"""
import os
from datetime import datetime, timedelta
import json
from pathlib import Path
from dotenv import load_dotenv

class Config:
    """Configuration class for Reddit Account Manager"""
    
    def __init__(self, config_file=None):
        """Initialize configuration"""
        # Load environment variables
        load_dotenv()
        
        # Set default config file path
        self.config_dir = Path(os.getenv("CONFIG_DIR", os.path.join(os.path.dirname(os.path.dirname(__file__)), "config")))
        self.config_file = config_file or os.path.join(self.config_dir, "config.json")
        
        # Create config directory if it doesn't exist
        os.makedirs(self.config_dir, exist_ok=True)
        
        # Load configuration
        self.config = self._load_config()
        
    def _load_config(self):
        """Load configuration from file or create default"""
        if os.path.exists(self.config_file):
            with open(self.config_file, "r", encoding="utf-8") as f:
                return json.load(f)
        else:
            # Default configuration
            default_config = {
                "app": {
                    "version": "1.0.0",
                    "data_dir": os.path.join(os.path.dirname(os.path.dirname(__file__)), "data"),
                    "logs_dir": os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs"),
                },
                "reddit": {
                    "client_id": os.getenv("REDDIT_CLIENT_ID", ""),
                    "client_secret": os.getenv("REDDIT_CLIENT_SECRET", ""),
                    "user_agent": os.getenv("REDDIT_USER_AGENT", "RedditAccountManager/1.0.0"),
                },
                "account_management": {
                    "database_file": "accounts.db",
                    "encryption_key": os.getenv("ENCRYPTION_KEY", ""),
                    "max_accounts_per_proxy": 3,
                },
                "engagement": {
                    "post_frequency": {
                        "min_hours": 12,
                        "max_hours": 48,
                        "variance_percent": 20
                    },
                    "comment_frequency": {
                        "min_hours": 4,
                        "max_hours": 24,
                        "variance_percent": 30
                    },
                    "target_subreddits": [
                        "AskReddit",
                        "pics",
                        "funny",
                        "todayilearned",
                        "worldnews",
                        "science"
                    ],
                    "activity_hours": {
                        "start": 8,  # 8 AM
                        "end": 23,   # 11 PM
                    },
                    "weekday_bias": {
                        "monday": 0.8,
                        "tuesday": 0.9,
                        "wednesday": 1.0,
                        "thursday": 1.0,
                        "friday": 1.2,
                        "saturday": 1.5,
                        "sunday": 1.3
                    },
                    "max_daily_actions": 10,
                    "natural_typing_delay": {
                        "enabled": True,
                        "min_cpm": 180,  # Characters per minute
                        "max_cpm": 400
                    }
                },
                "proxy": {
                    "rotation_frequency": 24,  # hours
                    "test_url": "https://www.reddit.com",
                    "timeout": 10,  # seconds
                },
                "security": {
                    "captcha_service": os.getenv("CAPTCHA_SERVICE", ""),
                    "captcha_api_key": os.getenv("CAPTCHA_API_KEY", ""),
                    "use_random_user_agents": True,
                    "session_timeout": 3600,  # seconds
                }
            }
            
            # Create directories
            os.makedirs(default_config["app"]["data_dir"], exist_ok=True)
            os.makedirs(default_config["app"]["logs_dir"], exist_ok=True)
            
            # Save default configuration
            self.save_config(default_config)
            
            return default_config
    
    def save_config(self, config=None):
        """Save configuration to file"""
        if config:
            self.config = config
            
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=4)
    
    def get(self, section, key=None):
        """Get configuration value"""
        if key:
            return self.config.get(section, {}).get(key)
        return self.config.get(section, {})
    
    def set(self, section, key, value):
        """Set configuration value"""
        if section not in self.config:
            self.config[section] = {}
        
        self.config[section][key] = value
        self.save_config()
        
    def get_data_path(self, filename):
        """Get path to a data file"""
        data_dir = self.config["app"]["data_dir"]
        return os.path.join(data_dir, filename)
    
    def get_logs_path(self, filename):
        """Get path to a log file"""
        logs_dir = self.config["app"]["logs_dir"]
        return os.path.join(logs_dir, filename)
