#!/usr/bin/env python3
"""
Reddit Account Manager - Main Application
"""
import argparse
import os
import sys
from datetime import datetime

from src.account_manager import AccountManager
from src.config import Config
from src.logger import setup_logger

logger = setup_logger()

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Reddit Account Manager")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Init command
    init_parser = subparsers.add_parser("init", help="Initialize the system")
    
    # Register command
    register_parser = subparsers.add_parser("register", help="Register new accounts")
    register_parser.add_argument("--accounts", required=True, help="Path to accounts CSV file")
    register_parser.add_argument("--proxies", required=True, help="Path to proxies CSV file")
    register_parser.add_argument("--count", type=int, default=1, help="Number of accounts to register")
    
    # Engage command
    engage_parser = subparsers.add_parser("engage", help="Run automated engagement")
    engage_parser.add_argument("--schedule", action="store_true", help="Run on schedule")
    engage_parser.add_argument("--accounts", help="Specific accounts to use (comma-separated usernames)")
    
    # Export command
    export_parser = subparsers.add_parser("export", help="Export account data")
    export_parser.add_argument("--format", choices=["json", "csv"], default="json", help="Export format")
    export_parser.add_argument("--output", default="accounts_export", help="Output file name (without extension)")
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Check account status")
    
    return parser.parse_args()

def main():
    """Main application entry point"""
    args = parse_arguments()
    
    # Load configuration
    config = Config()
    
    # Initialize account manager
    account_manager = AccountManager(config)
    
    if args.command == "init":
        logger.info("Initializing system...")
        account_manager.initialize()
        
    elif args.command == "register":
        logger.info(f"Registering {args.count} new accounts...")
        account_manager.register_accounts(
            accounts_file=args.accounts,
            proxies_file=args.proxies,
            count=args.count
        )
        
    elif args.command == "engage":
        logger.info("Starting engagement process...")
        specific_accounts = args.accounts.split(",") if args.accounts else None
        account_manager.run_engagement(
            scheduled=args.schedule,
            accounts=specific_accounts
        )
        
    elif args.command == "export":
        logger.info(f"Exporting account data to {args.format} format...")
        account_manager.export_accounts(
            export_format=args.format,
            output_file=args.output
        )
        
    elif args.command == "status":
        logger.info("Checking account status...")
        account_manager.check_status()
        
    else:
        logger.error("No command specified. Use --help for available commands.")
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Process interrupted by user. Exiting gracefully...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        sys.exit(1)
