"""Constants for Fleet Guard."""
from datetime import timedelta

DOMAIN = 'fleet_guard'
PLATFORMS = ['sensor', 'binary_sensor', 'button', 'update']
SCAN_INTERVAL = timedelta(seconds=45)
CONF_URL = 'url'
CONF_TOKEN = 'token'
CONF_VERIFY_SSL = 'verify_ssl'
