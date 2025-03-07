"""
Account Manager for Reddit Account Manager
"""
import csv
import json
import os
import random
import time
from datetime import datetime, timedelta
import sqlite3
import pandas as pd
from cryptography.fernet import Fernet
import schedule

from src.logger import setup_logger
from src.reddit_client import RedditClient
from src.proxy_manager import ProxyManager
from src.engagement_scheduler import EngagementScheduler

logger = setup_logger()

class AccountManager:
    """Manages Reddit accounts and their operations"""
    
    def __init__(self, config):
        """Initialize Account Manager"""
        self.config = config
        self.db_path = self.config.get_data_path(self.config.get("account_management", "database_file"))
        self.encryption_key = self.config.get("account_management", "encryption_key")
        
        if not self.encryption_key:
            self.encryption_key = Fernet.generate_key().decode()
            self.config.set("account_management", "encryption_key", self.encryption_key)
            logger.info("Generated new encryption key")
        
        self.cipher_suite = Fernet(self.encryption_key.encode())
        self.proxy_manager = ProxyManager(config)
        self.engagement_scheduler = EngagementScheduler(config, self)
        
        # Initialize database
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database for account storage"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create accounts table if it doesn't exist
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password_encrypted TEXT,
            email TEXT,
            creation_date TEXT,
            last_login TEXT,
            proxy_id INTEGER,
            user_agent TEXT,
            account_status TEXT,
            karma_post INTEGER DEFAULT 0,
            karma_comment INTEGER DEFAULT 0,
            last_post_date TEXT,
            last_comment_date TEXT,
            total_posts INTEGER DEFAULT 0,
            total_comments INTEGER DEFAULT 0,
            session_data TEXT,
            metadata TEXT
        )
        ''')
        
        # Create proxies table if it doesn't exist
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS proxies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip TEXT,
            port INTEGER,
            username TEXT,
            password_encrypted TEXT,
            protocol TEXT,
            last_used TEXT,
            status TEXT,
            failure_count INTEGER DEFAULT 0
        )
        ''')
        
        # Create activity log table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER,
            activity_type TEXT,
            activity_date TEXT,
            subreddit TEXT,
            post_id TEXT,
            comment_id TEXT,
            status TEXT,
            details TEXT,
            FOREIGN KEY (account_id) REFERENCES accounts (id)
        )
        ''')
        
        conn.commit()
        conn.close()
    
    def initialize(self):
        """Initialize the system"""
        # Create necessary directories
        os.makedirs(self.config.get_data_path(""), exist_ok=True)
        os.makedirs(self.config.get_logs_path(""), exist_ok=True)
        
        # Create example .env file if it doesn't exist
        env_example_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env.example")
        if not os.path.exists(env_example_path):
            with open(env_example_path, "w", encoding="utf-8") as f:
                f.write("""# Reddit API Credentials
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USER_AGENT=RedditAccountManager/1.0.0

# Encryption Key (will be auto-generated if not provided)
ENCRYPTION_KEY=

# Captcha Service (optional)
CAPTCHA_SERVICE=2captcha
CAPTCHA_API_KEY=your_api_key

# Configuration
CONFIG_DIR=./config
""")
            logger.info(f"Created example .env file at {env_example_path}")
        
        # Test database connection
        try:
            conn = sqlite3.connect(self.db_path)
            conn.close()
            logger.info(f"Database initialized at {self.db_path}")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise
        
        logger.info("System initialized successfully")
        return True
    
    def _encrypt(self, text):
        """Encrypt sensitive data"""
        return self.cipher_suite.encrypt(text.encode()).decode()
    
    def _decrypt(self, encrypted_text):
        """Decrypt sensitive data"""
        return self.cipher_suite.decrypt(encrypted_text.encode()).decode()
    
    def register_accounts(self, accounts_file, proxies_file, count=1):
        """Register new Reddit accounts"""
        # Load email addresses
        emails = []
        try:
            with open(accounts_file, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if 'email' in row:
                        emails.append(row['email'])
        except Exception as e:
            logger.error(f"Failed to load emails from {accounts_file}: {e}")
            return False
        
        if not emails:
            logger.error(f"No email addresses found in {accounts_file}")
            return False
        
        # Load proxies
        self.proxy_manager.load_proxies(proxies_file)
        available_proxies = self.proxy_manager.get_available_proxies()
        
        if not available_proxies:
            logger.error(f"No proxies available from {proxies_file}")
            return False
        
        # Register accounts
        successful_registrations = 0
        for i in range(count):
            if i >= len(emails):
                logger.warning(f"Not enough email addresses for {count} accounts")
                break
                
            email = emails[i]
            proxy = self.proxy_manager.get_next_proxy()
            
            if not proxy:
                logger.error("No more proxies available")
                break
            
            # Generate username and password
            username = f"user_{int(time.time())}_{random.randint(1000, 9999)}"
            password = self._generate_password()
            
            # Create Reddit client with proxy
            reddit_client = RedditClient(self.config, proxy)
            
            try:
                # Register account
                logger.info(f"Registering account with username {username} and email {email}")
                success = reddit_client.register_account(username, password, email)
                
                if success:
                    # Save account to database
                    self._save_account(username, password, email, proxy)
                    successful_registrations += 1
                    logger.info(f"Successfully registered account {username}")
                    
                    # Add delay between registrations
                    delay = random.uniform(30, 120)
                    logger.info(f"Waiting {delay:.2f} seconds before next registration")
                    time.sleep(delay)
                else:
                    logger.error(f"Failed to register account with username {username}")
            except Exception as e:
                logger.error(f"Error during account registration: {e}")
        
        logger.info(f"Registration complete. {successful_registrations}/{count} accounts registered successfully")
        return successful_registrations > 0
    
    def _generate_password(self, length=16):
        """Generate a secure random password"""
        chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()-_=+"
        return ''.join(random.choice(chars) for _ in range(length))
    
    def _save_account(self, username, password, email, proxy):
        """Save account to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        encrypted_password = self._encrypt(password)
        now = datetime.now().isoformat()
        
        cursor.execute('''
        INSERT INTO accounts (
            username, password_encrypted, email, creation_date, 
            last_login, proxy_id, user_agent, account_status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            username, encrypted_password, email, now,
            now, proxy['id'], self.config.get("reddit", "user_agent"), "active"
        ))
        
        conn.commit()
        conn.close()
    
    def run_engagement(self, scheduled=False, accounts=None):
        """Run engagement activities for accounts"""
        if scheduled:
            # Set up scheduling
            self.engagement_scheduler.schedule_activities(accounts)
            
            # Run scheduler indefinitely
            logger.info("Running scheduler. Press Ctrl+C to stop.")
            while True:
                schedule.run_pending()
                time.sleep(1)
        else:
            # Run engagement immediately
            self.engagement_scheduler.run_activities(accounts)
    
    def export_accounts(self, export_format="json", output_file="accounts_export"):
        """Export account data to file"""
        conn = sqlite3.connect(self.db_path)
        
        # Get accounts data
        accounts_df = pd.read_sql_query('''
        SELECT id, username, email, creation_date, last_login, 
               proxy_id, account_status, karma_post, karma_comment,
               last_post_date, last_comment_date, total_posts, total_comments
        FROM accounts
        ''', conn)
        
        # Get passwords (decrypted)
        cursor = conn.cursor()
        cursor.execute('SELECT id, password_encrypted FROM accounts')
        passwords = {row[0]: self._decrypt(row[1]) for row in cursor.fetchall()}
        
        # Add passwords to dataframe
        accounts_df['password'] = accounts_df['id'].map(passwords)
        
        # Remove id column
        accounts_df = accounts_df.drop('id', axis=1)
        
        # Export to specified format
        output_path = self.config.get_data_path(f"{output_file}.{export_format}")
        
        if export_format == "json":
            accounts_df.to_json(output_path, orient="records", indent=4)
        elif export_format == "csv":
            accounts_df.to_csv(output_path, index=False)
        
        conn.close()
        logger.info(f"Exported {len(accounts_df)} accounts to {output_path}")
        return output_path
    
    def check_status(self):
        """Check status of all accounts"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT id, username, account_status, last_login, karma_post, karma_comment
        FROM accounts
        ''')
        
        accounts = cursor.fetchall()
        
        logger.info(f"Account Status Report ({len(accounts)} accounts):")
        logger.info(f"{'Username':<20} {'Status':<10} {'Last Login':<20} {'Post Karma':<10} {'Comment Karma':<12}")
        logger.info("-" * 75)
        
        for account in accounts:
            _, username, status, last_login, karma_post, karma_comment = account
            last_login_date = last_login.split("T")[0] if last_login else "Never"
            logger.info(f"{username:<20} {status:<10} {last_login_date:<20} {karma_post:<10} {karma_comment:<12}")
        
        conn.close()
        return accounts
    
    def get_account_details(self, username):
        """Get details for a specific account"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT * FROM accounts WHERE username = ?
        ''', (username,))
        
        account = cursor.fetchone()
        
        if account:
            # Get column names
            columns = [description[0] for description in cursor.description]
            account_dict = dict(zip(columns, account))
            
            # Decrypt password
            if 'password_encrypted' in account_dict:
                account_dict['password'] = self._decrypt(account_dict['password_encrypted'])
                del account_dict['password_encrypted']
            
            conn.close()
            return account_dict
        else:
            conn.close()
            return None
