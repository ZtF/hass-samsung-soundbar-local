"""Constants for the Samsung Soundbar Local integration."""

from homeassistant.const import Platform

DOMAIN = "samsung_soundbar_local"

PLATFORMS = [Platform.BUTTON, Platform.MEDIA_PLAYER]

CONF_POLL_INTERVAL = "poll_interval"
DEFAULT_POLL_INTERVAL = 10  # seconds
MIN_POLL_INTERVAL = 5
MAX_POLL_INTERVAL = 300

CONF_VERIFY_SSL = "verify_ssl"
