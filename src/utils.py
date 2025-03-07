"""
Utility functions for Reddit Account Manager
"""
import os
import random
import string
import time
import json
from datetime import datetime, timedelta
import re
from pathlib import Path

from src.logger import setup_logger

logger = setup_logger()

def generate_random_username(prefix="user", length=8):
    """
    Generate a random username
    
    Args:
        prefix (str): Prefix for username
        length (int): Length of random part
        
    Returns:
        str: Generated username
    """
    timestamp = int(time.time())
    random_chars = ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))
    return f"{prefix}_{timestamp}_{random_chars}"

def generate_secure_password(length=16, include_special=True):
    """
    Generate a secure random password
    
    Args:
        length (int): Password length
        include_special (bool): Include special characters
        
    Returns:
        str: Generated password
    """
    chars = string.ascii_letters + string.digits
    if include_special:
        chars += "!@#$%^&*()-_=+"
    
    # Ensure at least one uppercase, one lowercase, one digit, and one special char
    password = [
        random.choice(string.ascii_uppercase),
        random.choice(string.ascii_lowercase),
        random.choice(string.digits)
    ]
    
    if include_special:
        password.append(random.choice("!@#$%^&*()-_=+"))
    
    # Fill the rest of the password
    password.extend(random.choice(chars) for _ in range(length - len(password)))
    
    # Shuffle the password
    random.shuffle(password)
    
    return ''.join(password)

def human_readable_time(seconds):
    """
    Convert seconds to human readable time format
    
    Args:
        seconds (float): Time in seconds
        
    Returns:
        str: Human readable time string
    """
    if seconds < 60:
        return f"{seconds:.1f} seconds"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f} minutes"
    else:
        hours = seconds / 3600
        return f"{hours:.1f} hours"

def add_random_delay(base_seconds, variance_percent=20):
    """
    Add random delay to base time
    
    Args:
        base_seconds (float): Base time in seconds
        variance_percent (float): Variance percentage
        
    Returns:
        float: Time with random variance
    """
    variance = base_seconds * (variance_percent / 100)
    return base_seconds + random.uniform(-variance, variance)

def is_valid_email(email):
    """
    Check if email is valid
    
    Args:
        email (str): Email to check
        
    Returns:
        bool: True if valid, False otherwise
    """
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))

def is_valid_proxy(proxy_dict):
    """
    Check if proxy configuration is valid
    
    Args:
        proxy_dict (dict): Proxy configuration
        
    Returns:
        bool: True if valid, False otherwise
    """
    required_fields = ["ip", "port", "protocol"]
    return all(field in proxy_dict and proxy_dict[field] for field in required_fields)

def format_timestamp(timestamp=None, format_str="%Y-%m-%d %H:%M:%S"):
    """
    Format timestamp to string
    
    Args:
        timestamp (float, optional): Unix timestamp. Defaults to current time.
        format_str (str, optional): Format string. Defaults to "%Y-%m-%d %H:%M:%S".
        
    Returns:
        str: Formatted timestamp
    """
    if timestamp is None:
        dt = datetime.now()
    else:
        dt = datetime.fromtimestamp(timestamp)
    
    return dt.strftime(format_str)

def parse_timestamp(timestamp_str, format_str="%Y-%m-%d %H:%M:%S"):
    """
    Parse timestamp string to datetime
    
    Args:
        timestamp_str (str): Timestamp string
        format_str (str, optional): Format string. Defaults to "%Y-%m-%d %H:%M:%S".
        
    Returns:
        datetime: Parsed datetime
    """
    return datetime.strptime(timestamp_str, format_str)

def ensure_dir_exists(directory):
    """
    Ensure directory exists, create if it doesn't
    
    Args:
        directory (str): Directory path
        
    Returns:
        str: Directory path
    """
    os.makedirs(directory, exist_ok=True)
    return directory

def load_json_file(file_path, default=None):
    """
    Load JSON file
    
    Args:
        file_path (str): Path to JSON file
        default (any, optional): Default value if file doesn't exist. Defaults to None.
        
    Returns:
        dict: Loaded JSON data
    """
    if not os.path.exists(file_path):
        return default if default is not None else {}
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load JSON file {file_path}: {e}")
        return default if default is not None else {}

def save_json_file(file_path, data, indent=4):
    """
    Save data to JSON file
    
    Args:
        file_path (str): Path to JSON file
        data (dict): Data to save
        indent (int, optional): JSON indentation. Defaults to 4.
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        directory = os.path.dirname(file_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
            
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent)
        return True
    except Exception as e:
        logger.error(f"Failed to save JSON file {file_path}: {e}")
        return False

def get_weekday_bias():
    """
    Get activity bias based on current weekday
    
    Returns:
        float: Activity bias multiplier
    """
    weekday = datetime.now().strftime('%A').lower()
    
    # Default bias values
    bias = {
        'monday': 0.8,
        'tuesday': 0.9,
        'wednesday': 1.0,
        'thursday': 1.0,
        'friday': 1.2,
        'saturday': 1.5,
        'sunday': 1.3
    }
    
    return bias.get(weekday, 1.0)

def get_hour_bias():
    """
    Get activity bias based on current hour
    
    Returns:
        float: Activity bias multiplier
    """
    hour = datetime.now().hour
    
    # Higher activity during peak hours
    if 8 <= hour <= 10:  # Morning
        return 1.2
    elif 12 <= hour <= 14:  # Lunch
        return 1.3
    elif 19 <= hour <= 22:  # Evening
        return 1.5
    elif 0 <= hour <= 5:  # Late night
        return 0.5
    else:
        return 1.0

def calculate_activity_score():
    """
    Calculate activity score based on time factors
    
    Returns:
        float: Activity score (0.0-1.0)
    """
    weekday_bias = get_weekday_bias()
    hour_bias = get_hour_bias()
    
    # Random factor for natural variation
    random_factor = random.uniform(0.8, 1.2)
    
    # Calculate score (normalize to 0.0-1.0 range)
    score = min(1.0, (weekday_bias * hour_bias * random_factor) / 2.5)
    
    return score
