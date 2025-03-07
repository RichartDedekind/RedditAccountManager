"""
Engagement Scheduler for Reddit Account Manager
"""
import json
import random
import time
from datetime import datetime, timedelta
import sqlite3
import schedule
from threading import Thread

from src.logger import setup_logger
from src.reddit_client import RedditClient

logger = setup_logger()

class EngagementScheduler:
    """Schedules and executes Reddit engagement activities"""
    
    def __init__(self, config, account_manager):
        """Initialize Engagement Scheduler"""
        self.config = config
        self.account_manager = account_manager
        self.db_path = self.config.get_data_path(self.config.get("account_management", "database_file"))
        self.running_threads = {}
    
    def schedule_activities(self, accounts=None):
        """Schedule activities for accounts"""
        # Clear existing schedules
        schedule.clear()
        
        # Schedule daily account status update
        schedule.every().day.at("04:00").do(self.account_manager.check_status)
        
        # Schedule proxy rotation
        rotation_frequency = self.config.get("proxy", "rotation_frequency")
        schedule.every(rotation_frequency).hours.do(self.account_manager.proxy_manager.rotate_proxies)
        
        # Schedule engagement activities
        self._schedule_engagement(accounts)
        
        logger.info("Scheduled all activities")
    
    def _schedule_engagement(self, specific_accounts=None):
        """Schedule engagement activities for accounts"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get active accounts
        if specific_accounts:
            placeholders = ', '.join(['?'] * len(specific_accounts))
            cursor.execute(f'''
            SELECT id, username, password_encrypted
            FROM accounts
            WHERE username IN ({placeholders}) AND account_status = 'active'
            ''', specific_accounts)
        else:
            cursor.execute('''
            SELECT id, username, password_encrypted
            FROM accounts
            WHERE account_status = 'active'
            ''')
        
        accounts = cursor.fetchall()
        conn.close()
        
        if not accounts:
            logger.warning("No active accounts found for scheduling")
            return
        
        # Schedule activities for each account
        for account in accounts:
            account_id, username, password_encrypted = account
            
            # Schedule posts
            post_config = self.config.get("engagement", "post_frequency")
            min_hours = post_config.get("min_hours", 12)
            max_hours = post_config.get("max_hours", 48)
            
            # Random time for first post
            first_post_hours = random.uniform(1, min_hours)
            
            # Schedule first post
            schedule.every(first_post_hours).hours.do(
                self._create_post_job, account_id, username
            )
            
            # Schedule comments
            comment_config = self.config.get("engagement", "comment_frequency")
            min_comment_hours = comment_config.get("min_hours", 4)
            max_comment_hours = comment_config.get("max_hours", 24)
            
            # Random time for first comment
            first_comment_hours = random.uniform(0.5, min_comment_hours)
            
            # Schedule first comment
            schedule.every(first_comment_hours).hours.do(
                self._create_comment_job, account_id, username
            )
            
            logger.info(f"Scheduled activities for account {username}")
    
    def _create_post_job(self, account_id, username):
        """Create a job for posting"""
        # Get account details
        account_details = self.account_manager.get_account_details(username)
        if not account_details:
            logger.error(f"Account details not found for {username}")
            return schedule.CancelJob
        
        # Check if within activity hours
        if not self._is_within_activity_hours():
            logger.info(f"Outside activity hours, skipping post for {username}")
            return
        
        # Get proxy
        proxy = self.account_manager.proxy_manager.get_next_proxy()
        if not proxy:
            logger.error("No proxy available for posting")
            return
        
        # Create Reddit client
        reddit_client = RedditClient(self.config, proxy)
        
        # Login
        success, session_data = reddit_client.login(username, account_details['password'])
        if not success:
            logger.error(f"Failed to login as {username}")
            return
        
        # Select random subreddit from targets
        target_subreddits = self.config.get("engagement", "target_subreddits")
        subreddit = random.choice(target_subreddits)
        
        # Create post content
        title = self._generate_post_title(subreddit)
        content = self._generate_post_content(subreddit)
        
        # Submit post
        post_id = reddit_client.submit_post(subreddit, title, content)
        
        if post_id:
            # Update account data
            self._log_activity(account_id, "post", subreddit, post_id, None, "success")
            
            # Update last post date
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
            UPDATE accounts 
            SET last_post_date = ?, total_posts = total_posts + 1
            WHERE id = ?
            ''', (datetime.now().isoformat(), account_id))
            conn.commit()
            conn.close()
        
        # Schedule next post
        post_config = self.config.get("engagement", "post_frequency")
        min_hours = post_config.get("min_hours", 12)
        max_hours = post_config.get("max_hours", 48)
        variance = post_config.get("variance_percent", 20) / 100
        
        base_hours = random.uniform(min_hours, max_hours)
        variance_hours = base_hours * variance * random.choice([-1, 1])
        next_post_hours = max(min_hours, base_hours + variance_hours)
        
        logger.info(f"Next post for {username} scheduled in {next_post_hours:.2f} hours")
        
        # Return the next schedule time
        return next_post_hours
    
    def _create_comment_job(self, account_id, username):
        """Create a job for commenting"""
        # Get account details
        account_details = self.account_manager.get_account_details(username)
        if not account_details:
            logger.error(f"Account details not found for {username}")
            return schedule.CancelJob
        
        # Check if within activity hours
        if not self._is_within_activity_hours():
            logger.info(f"Outside activity hours, skipping comment for {username}")
            return
        
        # Get proxy
        proxy = self.account_manager.proxy_manager.get_next_proxy()
        if not proxy:
            logger.error("No proxy available for commenting")
            return
        
        # Create Reddit client
        reddit_client = RedditClient(self.config, proxy)
        
        # Login
        success, session_data = reddit_client.login(username, account_details['password'])
        if not success:
            logger.error(f"Failed to login as {username}")
            return
        
        # Select random subreddit from targets
        target_subreddits = self.config.get("engagement", "target_subreddits")
        subreddit = random.choice(target_subreddits)
        
        # Get trending posts
        trending_posts = reddit_client.get_trending_posts(subreddit, limit=20)
        
        if trending_posts:
            # Select random post
            post = random.choice(trending_posts)
            
            # Generate comment
            comment_text = self._generate_comment(post)
            
            # Submit comment
            comment_id = reddit_client.submit_comment(post['id'], comment_text)
            
            if comment_id:
                # Update account data
                self._log_activity(account_id, "comment", subreddit, post['id'], comment_id, "success")
                
                # Update last comment date
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('''
                UPDATE accounts 
                SET last_comment_date = ?, total_comments = total_comments + 1
                WHERE id = ?
                ''', (datetime.now().isoformat(), account_id))
                conn.commit()
                conn.close()
        
        # Schedule next comment
        comment_config = self.config.get("engagement", "comment_frequency")
        min_hours = comment_config.get("min_hours", 4)
        max_hours = comment_config.get("max_hours", 24)
        variance = comment_config.get("variance_percent", 30) / 100
        
        base_hours = random.uniform(min_hours, max_hours)
        variance_hours = base_hours * variance * random.choice([-1, 1])
        next_comment_hours = max(min_hours, base_hours + variance_hours)
        
        logger.info(f"Next comment for {username} scheduled in {next_comment_hours:.2f} hours")
        
        # Return the next schedule time
        return next_comment_hours
    
    def _is_within_activity_hours(self):
        """Check if current time is within configured activity hours"""
        activity_hours = self.config.get("engagement", "activity_hours")
        start_hour = activity_hours.get("start", 8)
        end_hour = activity_hours.get("end", 23)
        
        current_hour = datetime.now().hour
        
        return start_hour <= current_hour <= end_hour
    
    def _log_activity(self, account_id, activity_type, subreddit, post_id, comment_id, status, details=None):
        """Log activity to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO activity_log (
            account_id, activity_type, activity_date, subreddit, 
            post_id, comment_id, status, details
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            account_id, activity_type, datetime.now().isoformat(),
            subreddit, post_id, comment_id, status, json.dumps(details) if details else None
        ))
        
        conn.commit()
        conn.close()
    
    def run_activities(self, accounts=None):
        """Run engagement activities immediately"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get active accounts
        if accounts:
            placeholders = ', '.join(['?'] * len(accounts))
            cursor.execute(f'''
            SELECT id, username, password_encrypted
            FROM accounts
            WHERE username IN ({placeholders}) AND account_status = 'active'
            ''', accounts)
        else:
            cursor.execute('''
            SELECT id, username, password_encrypted
            FROM accounts
            WHERE account_status = 'active'
            ''')
        
        accounts = cursor.fetchall()
        conn.close()
        
        if not accounts:
            logger.warning("No active accounts found for engagement")
            return
        
        # Run activities for each account
        for account in accounts:
            account_id, username, _ = account
            
            # Start engagement in separate thread
            thread = Thread(target=self._run_account_engagement, args=(account_id, username))
            thread.daemon = True
            thread.start()
            
            self.running_threads[username] = thread
            
            # Add delay between account activations
            time.sleep(random.uniform(5, 15))
    
    def _run_account_engagement(self, account_id, username):
        """Run engagement for a single account"""
        logger.info(f"Starting engagement for {username}")
        
        # Determine number of actions based on config
        max_actions = self.config.get("engagement", "max_daily_actions")
        num_actions = random.randint(max(1, max_actions // 2), max_actions)
        
        # Determine ratio of posts to comments
        post_ratio = 0.3  # 30% posts, 70% comments
        num_posts = max(1, int(num_actions * post_ratio))
        num_comments = num_actions - num_posts
        
        logger.info(f"Planning {num_posts} posts and {num_comments} comments for {username}")
        
        # Execute posts
        for i in range(num_posts):
            if not self._is_within_activity_hours():
                logger.info(f"Outside activity hours, pausing engagement for {username}")
                break
                
            self._create_post_job(account_id, username)
            
            # Random delay between posts
            delay = random.uniform(30 * 60, 120 * 60)  # 30-120 minutes
            logger.info(f"Waiting {delay/60:.2f} minutes before next action for {username}")
            time.sleep(delay)
        
        # Execute comments
        for i in range(num_comments):
            if not self._is_within_activity_hours():
                logger.info(f"Outside activity hours, pausing engagement for {username}")
                break
                
            self._create_comment_job(account_id, username)
            
            # Random delay between comments
            delay = random.uniform(15 * 60, 60 * 60)  # 15-60 minutes
            logger.info(f"Waiting {delay/60:.2f} minutes before next action for {username}")
            time.sleep(delay)
        
        logger.info(f"Completed engagement for {username}")
    
    def _generate_post_title(self, subreddit):
        """Generate a post title based on subreddit"""
        # This would ideally use more sophisticated content generation
        # For now, using simple templates
        
        templates = {
            "AskReddit": [
                "What's the most surprising thing you've learned about {}?",
                "How do you deal with {} in your daily life?",
                "What's your best advice for someone struggling with {}?",
                "What's your favorite {} and why?",
                "If you could change one thing about {}, what would it be?"
            ],
            "todayilearned": [
                "TIL that {} can actually {}",
                "TIL about {}, which changed how I view {}",
                "TIL {} was originally designed for {}",
                "TIL the history of {} dates back to {}",
                "TIL that scientists discovered {} can {}"
            ],
            "default": [
                "Interesting thoughts about {}",
                "My experience with {}",
                "Let's discuss {}",
                "What do you think about {}?",
                "Has anyone else noticed {} recently?"
            ]
        }
        
        # Get templates for subreddit or use default
        subreddit_templates = templates.get(subreddit, templates["default"])
        
        # Select random template
        template = random.choice(subreddit_templates)
        
        # Fill in template with relevant topics
        topics = [
            "technology", "science", "politics", "movies", "books",
            "music", "food", "travel", "sports", "gaming",
            "education", "career", "relationships", "health", "finance"
        ]
        
        # Format template with random topics
        if template.count("{}") == 1:
            return template.format(random.choice(topics))
        elif template.count("{}") == 2:
            return template.format(random.choice(topics), random.choice(topics))
        else:
            return template
    
    def _generate_post_content(self, subreddit):
        """Generate post content based on subreddit"""
        # This would ideally use more sophisticated content generation
        # For now, using simple templates
        
        paragraphs = [
            "I've been thinking about this topic for a while now and wanted to get some other perspectives. What do you all think?",
            "This is something I've noticed recently and I'm curious if others have had similar experiences.",
            "I've been researching this topic and found some interesting information that I thought was worth sharing.",
            "I'm relatively new to this subject, so I'd appreciate any insights or advice from those with more experience.",
            "I've seen a lot of discussion about this lately, but I feel like some important points are being overlooked."
        ]
        
        # Select 1-3 random paragraphs
        num_paragraphs = random.randint(1, 3)
        selected_paragraphs = random.sample(paragraphs, num_paragraphs)
        
        # Join paragraphs with newlines
        return "\n\n".join(selected_paragraphs)
    
    def _generate_comment(self, post):
        """Generate a comment based on post"""
        # This would ideally use more sophisticated content generation
        # For now, using simple templates
        
        templates = [
            "I completely agree with this. In my experience, {}.",
            "Interesting perspective. Have you considered {}?",
            "This reminds me of {}. Anyone else see the similarity?",
            "Great point! I'd also add that {}.",
            "I've been thinking about this too. My take is that {}.",
            "Thanks for sharing this. It made me realize that {}.",
            "I had a similar experience with {}.",
            "I see what you're saying, but I think {} is also worth considering.",
            "This is exactly what I needed to read today. Especially the part about {}.",
            "I've been following this topic for a while, and {}."
        ]
        
        # Select random template
        template = random.choice(templates)
        
        # Generate random topic based on post title
        topics = [
            "it depends on the specific circumstances",
            "there are multiple factors to consider",
            "personal experience plays a big role",
            "research suggests different outcomes",
            "cultural context matters significantly",
            "technological advances are changing this rapidly",
            "historical precedents show similar patterns",
            "individual preferences vary widely",
            "professional advice often contradicts popular opinion",
            "social media has transformed how we view this"
        ]
        
        # Format template with random topic
        return template.format(random.choice(topics))
