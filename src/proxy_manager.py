"""
Proxy Manager for Reddit Account Manager
"""
import csv
import json
import random
import time
from datetime import datetime, timedelta
import sqlite3
import requests
from fake_useragent import UserAgent

from src.logger import setup_logger

logger = setup_logger()

class ProxyManager:
    """Manages proxies for Reddit account operations"""
    
    def __init__(self, config):
        """Initialize Proxy Manager"""
        self.config = config
        self.db_path = self.config.get_data_path(self.config.get("account_management", "database_file"))
        self.rotation_frequency = self.config.get("proxy", "rotation_frequency")
        self.test_url = self.config.get("proxy", "test_url")
        self.timeout = self.config.get("proxy", "timeout")
        self.use_random_user_agents = self.config.get("security", "use_random_user_agents")
        self.user_agent_generator = UserAgent() if self.use_random_user_agents else None
    
    def load_proxies(self, proxies_file):
        """Load proxies from CSV file"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            with open(proxies_file, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Check if proxy already exists
                    cursor.execute(
                        'SELECT id FROM proxies WHERE ip = ? AND port = ?',
                        (row.get('ip'), int(row.get('port', 0)))
                    )
                    
                    if cursor.fetchone() is None:
                        # Encrypt password if present
                        password_encrypted = None
                        if 'password' in row and row['password']:
                            cipher_suite = self._get_cipher_suite()
                            password_encrypted = cipher_suite.encrypt(row['password'].encode()).decode()
                        
                        # Insert new proxy
                        cursor.execute('''
                        INSERT INTO proxies (
                            ip, port, username, password_encrypted, protocol, status
                        ) VALUES (?, ?, ?, ?, ?, ?)
                        ''', (
                            row.get('ip'),
                            int(row.get('port', 0)),
                            row.get('username'),
                            password_encrypted,
                            row.get('protocol', 'http'),
                            'active'
                        ))
            
            conn.commit()
            logger.info(f"Loaded proxies from {proxies_file}")
        except Exception as e:
            logger.error(f"Failed to load proxies from {proxies_file}: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def _get_cipher_suite(self):
        """Get encryption cipher suite"""
        from cryptography.fernet import Fernet
        encryption_key = self.config.get("account_management", "encryption_key")
        return Fernet(encryption_key.encode())
    
    def get_available_proxies(self):
        """Get list of available proxies"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT id, ip, port, username, password_encrypted, protocol, last_used, status, failure_count
        FROM proxies
        WHERE status = 'active' AND failure_count < 5
        ''')
        
        proxies = []
        for row in cursor.fetchall():
            proxy = {
                'id': row[0],
                'ip': row[1],
                'port': row[2],
                'username': row[3],
                'password_encrypted': row[4],
                'protocol': row[5],
                'last_used': row[6],
                'status': row[7],
                'failure_count': row[8]
            }
            
            # Decrypt password if present
            if proxy['password_encrypted']:
                cipher_suite = self._get_cipher_suite()
                proxy['password'] = cipher_suite.decrypt(proxy['password_encrypted'].encode()).decode()
            else:
                proxy['password'] = None
            
            proxies.append(proxy)
        
        conn.close()
        return proxies
    
    def get_next_proxy(self):
        """Get next available proxy based on rotation policy"""
        available_proxies = self.get_available_proxies()
        
        if not available_proxies:
            logger.error("No available proxies")
            return None
        
        # Sort by last used (oldest first)
        available_proxies.sort(key=lambda p: p['last_used'] if p['last_used'] else '1970-01-01')
        
        # Get the least recently used proxy
        proxy = available_proxies[0]
        
        # Update last_used timestamp
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE proxies SET last_used = ? WHERE id = ?',
            (datetime.now().isoformat(), proxy['id'])
        )
        conn.commit()
        conn.close()
        
        return proxy
    
    def get_proxy_url(self, proxy):
        """Get proxy URL for requests"""
        auth = ""
        if proxy['username'] and proxy['password']:
            auth = f"{proxy['username']}:{proxy['password']}@"
        
        return f"{proxy['protocol']}://{auth}{proxy['ip']}:{proxy['port']}"
    
    def get_proxy_dict(self, proxy):
        """Get proxy dictionary for requests"""
        proxy_url = self.get_proxy_url(proxy)
        return {
            'http': proxy_url,
            'https': proxy_url
        }
    
    def test_proxy(self, proxy):
        """Test if proxy is working"""
        try:
            proxy_dict = self.get_proxy_dict(proxy)
            
            headers = {}
            if self.use_random_user_agents:
                headers['User-Agent'] = self.user_agent_generator.random
            
            response = requests.get(
                self.test_url,
                proxies=proxy_dict,
                headers=headers,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                logger.debug(f"Proxy {proxy['ip']}:{proxy['port']} is working")
                return True
            else:
                logger.warning(f"Proxy {proxy['ip']}:{proxy['port']} returned status code {response.status_code}")
                return False
        except Exception as e:
            logger.warning(f"Proxy {proxy['ip']}:{proxy['port']} test failed: {e}")
            self._increment_failure_count(proxy['id'])
            return False
    
    def _increment_failure_count(self, proxy_id):
        """Increment failure count for proxy"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        UPDATE proxies 
        SET failure_count = failure_count + 1,
            status = CASE WHEN failure_count + 1 >= 5 THEN 'inactive' ELSE status END
        WHERE id = ?
        ''', (proxy_id,))
        
        conn.commit()
        conn.close()
    
    def reset_failure_count(self, proxy_id):
        """Reset failure count for proxy"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        UPDATE proxies 
        SET failure_count = 0,
            status = 'active'
        WHERE id = ?
        ''', (proxy_id,))
        
        conn.commit()
        conn.close()
    
    def rotate_proxies(self):
        """Rotate proxies based on configuration"""
        logger.info("Rotating proxies...")
        
        # Get all proxies
        available_proxies = self.get_available_proxies()
        
        # Test each proxy and update status
        for proxy in available_proxies:
            if self.test_proxy(proxy):
                self.reset_failure_count(proxy['id'])
            
        logger.info("Proxy rotation complete")
        return True
