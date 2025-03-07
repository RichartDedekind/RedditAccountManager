"""
Reddit Client for Reddit Account Manager
"""
import json
import random
import time
from datetime import datetime
import praw
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

from src.logger import setup_logger

logger = setup_logger()

class RedditClient:
    """Client for interacting with Reddit"""
    
    def __init__(self, config, proxy=None):
        """Initialize Reddit Client"""
        self.config = config
        self.proxy = proxy
        self.client_id = self.config.get("reddit", "client_id")
        self.client_secret = self.config.get("reddit", "client_secret")
        self.user_agent = self.config.get("reddit", "user_agent")
        
        # Initialize session
        self.session = None
        self.driver = None
    
    def register_account(self, username, password, email):
        """Register a new Reddit account"""
        logger.info(f"Registering new account: {username}")
        
        try:
            # Use Selenium for registration
            self._init_selenium()
            
            # Navigate to Reddit signup page
            self.driver.get("https://www.reddit.com/register/")
            time.sleep(random.uniform(2, 4))
            
            # Fill in email
            email_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "regEmail"))
            )
            self._type_with_human_delay(email_field, email)
            
            # Click continue
            continue_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Continue')]")
            continue_button.click()
            time.sleep(random.uniform(2, 4))
            
            # Fill in username
            username_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "regUsername"))
            )
            self._type_with_human_delay(username_field, username)
            
            # Fill in password
            password_field = self.driver.find_element(By.ID, "regPassword")
            self._type_with_human_delay(password_field, password)
            
            # Click sign up
            signup_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Sign Up')]")
            signup_button.click()
            
            # Handle CAPTCHA if present
            if self._is_captcha_present():
                self._solve_captcha()
            
            # Wait for registration to complete
            time.sleep(random.uniform(5, 10))
            
            # Check if registration was successful
            if "https://www.reddit.com/verification" in self.driver.current_url or "https://www.reddit.com/" in self.driver.current_url:
                logger.info(f"Account {username} registered successfully")
                
                # Save cookies/session data
                cookies = self.driver.get_cookies()
                session_data = json.dumps(cookies)
                
                # Close driver
                self._close_selenium()
                
                return True
            else:
                logger.error(f"Failed to register account {username}")
                self._close_selenium()
                return False
                
        except Exception as e:
            logger.error(f"Error during account registration: {e}")
            self._close_selenium()
            return False
    
    def _init_selenium(self):
        """Initialize Selenium WebDriver"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        
        # Add proxy if provided
        if self.proxy:
            if self.proxy.get('username') and self.proxy.get('password'):
                proxy_auth = f"{self.proxy['username']}:{self.proxy['password']}"
                chrome_options.add_argument(f"--proxy-server={self.proxy['protocol']}://{self.proxy['ip']}:{self.proxy['port']}")
                chrome_options.add_argument(f"--proxy-auth={proxy_auth}")
            else:
                chrome_options.add_argument(f"--proxy-server={self.proxy['protocol']}://{self.proxy['ip']}:{self.proxy['port']}")
        
        # Initialize WebDriver
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
    
    def _close_selenium(self):
        """Close Selenium WebDriver"""
        if self.driver:
            self.driver.quit()
            self.driver = None
    
    def _type_with_human_delay(self, element, text):
        """Type text with human-like delays"""
        min_cpm = self.config.get("engagement", "natural_typing_delay", {}).get("min_cpm", 180)
        max_cpm = self.config.get("engagement", "natural_typing_delay", {}).get("max_cpm", 400)
        
        # Calculate delay between keystrokes (in seconds)
        cpm = random.uniform(min_cpm, max_cpm)
        delay_per_char = 60 / cpm
        
        for char in text:
            element.send_keys(char)
            time.sleep(delay_per_char * random.uniform(0.8, 1.2))
    
    def _is_captcha_present(self):
        """Check if CAPTCHA is present on the page"""
        try:
            # Check for reCAPTCHA
            recaptcha = self.driver.find_elements(By.XPATH, "//iframe[contains(@src, 'recaptcha')]")
            if recaptcha:
                return True
            
            # Check for hCaptcha
            hcaptcha = self.driver.find_elements(By.XPATH, "//iframe[contains(@src, 'hcaptcha')]")
            if hcaptcha:
                return True
            
            return False
        except:
            return False
    
    def _solve_captcha(self):
        """Solve CAPTCHA using configured service"""
        captcha_service = self.config.get("security", "captcha_service")
        captcha_api_key = self.config.get("security", "captcha_api_key")
        
        if not captcha_service or not captcha_api_key:
            logger.warning("CAPTCHA service not configured")
            return False
        
        # Implementation depends on the specific CAPTCHA service
        # This is a placeholder for integration with services like 2captcha or Anti-Captcha
        logger.info(f"Attempting to solve CAPTCHA using {captcha_service}")
        
        # Wait for manual intervention (in real implementation, this would be automated)
        logger.warning("CAPTCHA solving not implemented - waiting for timeout")
        time.sleep(30)
        
        return False
    
    def login(self, username, password):
        """Login to Reddit account"""
        logger.info(f"Logging in as {username}")
        
        try:
            # Use Selenium for login
            self._init_selenium()
            
            # Navigate to Reddit login page
            self.driver.get("https://www.reddit.com/login/")
            time.sleep(random.uniform(2, 4))
            
            # Fill in username
            username_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "loginUsername"))
            )
            self._type_with_human_delay(username_field, username)
            
            # Fill in password
            password_field = self.driver.find_element(By.ID, "loginPassword")
            self._type_with_human_delay(password_field, password)
            
            # Click login
            login_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Log In')]")
            login_button.click()
            
            # Handle CAPTCHA if present
            if self._is_captcha_present():
                self._solve_captcha()
            
            # Wait for login to complete
            time.sleep(random.uniform(5, 10))
            
            # Check if login was successful
            if "https://www.reddit.com/" in self.driver.current_url:
                logger.info(f"Logged in as {username} successfully")
                
                # Save cookies/session data
                cookies = self.driver.get_cookies()
                session_data = json.dumps(cookies)
                
                # Initialize PRAW with session
                self._init_praw(username, password, cookies)
                
                return True, session_data
            else:
                logger.error(f"Failed to log in as {username}")
                self._close_selenium()
                return False, None
                
        except Exception as e:
            logger.error(f"Error during login: {e}")
            self._close_selenium()
            return False, None
    
    def _init_praw(self, username, password, cookies=None):
        """Initialize PRAW Reddit client"""
        try:
            self.reddit = praw.Reddit(
                client_id=self.client_id,
                client_secret=self.client_secret,
                user_agent=self.user_agent,
                username=username,
                password=password
            )
            
            # Verify credentials
            username = self.reddit.user.me().name
            logger.info(f"PRAW initialized for user {username}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize PRAW: {e}")
            return False
    
    def submit_post(self, subreddit_name, title, content=None, url=None):
        """Submit a post to a subreddit"""
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            
            if url:
                submission = subreddit.submit(title, url=url)
                logger.info(f"Submitted link post to r/{subreddit_name}: {submission.id}")
            else:
                submission = subreddit.submit(title, selftext=content or "")
                logger.info(f"Submitted text post to r/{subreddit_name}: {submission.id}")
            
            return submission.id
        except Exception as e:
            logger.error(f"Failed to submit post to r/{subreddit_name}: {e}")
            return None
    
    def submit_comment(self, post_id, comment_text):
        """Submit a comment on a post"""
        try:
            submission = self.reddit.submission(id=post_id)
            comment = submission.reply(comment_text)
            logger.info(f"Submitted comment on post {post_id}: {comment.id}")
            return comment.id
        except Exception as e:
            logger.error(f"Failed to submit comment on post {post_id}: {e}")
            return None
    
    def get_account_info(self):
        """Get information about the logged-in account"""
        try:
            user = self.reddit.user.me()
            
            info = {
                "username": user.name,
                "karma_post": user.link_karma,
                "karma_comment": user.comment_karma,
                "created_utc": user.created_utc,
                "is_mod": user.is_mod,
                "is_gold": user.is_gold
            }
            
            return info
        except Exception as e:
            logger.error(f"Failed to get account info: {e}")
            return None
    
    def get_trending_posts(self, subreddit_name, limit=10):
        """Get trending posts from a subreddit"""
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            trending_posts = []
            
            for post in subreddit.hot(limit=limit):
                trending_posts.append({
                    "id": post.id,
                    "title": post.title,
                    "score": post.score,
                    "num_comments": post.num_comments,
                    "url": post.url,
                    "created_utc": post.created_utc
                })
            
            return trending_posts
        except Exception as e:
            logger.error(f"Failed to get trending posts from r/{subreddit_name}: {e}")
            return []
