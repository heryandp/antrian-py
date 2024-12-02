import json
import os
import logging

logger = logging.getLogger('Config')

DEFAULT_CONFIG = {
    "office_name": "KANTOR PELAYANAN TERPADU",
    "counters": {
        "A": 2,  # A1, A2
        "B": 2,  # B1, B2
    },
    "services": [
        {
            "code": "A",
            "name": "Pelayanan A",
            "description": "Layanan administrasi A"
        },
        {
            "code": "B",
            "name": "Pelayanan B",
            "description": "Layanan administrasi B"
        }
    ]
}

CONFIG_FILE = 'queue_config.json'

def load_config():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        else:
            save_config(DEFAULT_CONFIG)
            return DEFAULT_CONFIG
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return DEFAULT_CONFIG

def save_config(config):
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        logger.error(f"Error saving config: {e}")

def get_counter_list():
    """Generate list of counters from config"""
    config = load_config()
    counters = []
    for letter, count in config['counters'].items():
        for num in range(1, count + 1):
            counters.append(f"{letter}{num}")
    return counters

def get_service_list():
    """Get list of services from config"""
    config = load_config()
    return config['services']

def get_office_name():
    """Get office name from config"""
    config = load_config()
    return config['office_name']
