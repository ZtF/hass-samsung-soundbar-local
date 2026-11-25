DOMAIN = "soundbar_local"

PLATFORMS = ["button", "media_player", "select"]

DEFAULT_POLL_INTERVAL = 10  # seconds

CONF_VERIFY_SSL = "verify_ssl"

# Woofer levels in WOOFER_PLUS/WOOFER_MINUS order (observed on HW-Q990D;
# the level after -12 is -6).
WOOFER_LEVELS = ["-12", "-6", "-5", "-4", "-3", "-2", "-1", "0", "1", "2", "3", "4", "5", "6"]
DEFAULT_WOOFER_LEVEL = "0"
