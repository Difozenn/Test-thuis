#!/usr/bin/env python3
import json
import os
import sys
import logging

# Add project root to path to allow imports from sibling directories
project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import path utilities for proper path handling
from path_utils import get_writable_path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

def fix_dashboard_users():
    """Fix dashboard users configuration to ensure NESTING is included."""
    try:
        config_path = get_writable_path('config.json')
        
        # Check if config file exists
        if not os.path.exists(config_path):
            logging.info(f"Config file does not exist at {config_path}. Creating new config.")
            config = {
                'scanner_panel_open_event_users': ['NESTING', 'OPUS', 'KL GANNOMAT'],
                'dashboard_display_users': ['NESTING', 'OPUS', 'KL GANNOMAT']
            }
        else:
            # Load existing config
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            # Get current scanner users
            scanner_users = config.get('scanner_panel_open_event_users', [])
            
            # Make sure NESTING is included
            if 'NESTING' not in scanner_users:
                scanner_users.insert(0, 'NESTING')
                config['scanner_panel_open_event_users'] = scanner_users
                logging.info(f"Added NESTING to scanner_panel_open_event_users")
            
            # Set dashboard display users
            config['dashboard_display_users'] = scanner_users
        
        # Save the updated config
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        logging.info(f"Fixed! Dashboard users: {config['dashboard_display_users']}")
        logging.info(f"Configuration saved to: {config_path}")
        
        return True
    except Exception as e:
        logging.error(f"Error fixing dashboard users: {e}")
        return False

if __name__ == '__main__':
    success = fix_dashboard_users()
    if success:
        print("Dashboard users configuration fixed successfully!")
    else:
        print("Failed to fix dashboard users configuration. Check the logs for details.")
