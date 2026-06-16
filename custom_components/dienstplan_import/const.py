"""Constants for the Dienstplan Import integration."""

DOMAIN = "dienstplan_import"

# Config / options keys
CONF_WEBHOOK_ID = "webhook_id"
CONF_LOCAL_ONLY = "local_only"
CONF_CALENDAR_FILE = "calendar_file"
CONF_CALENDAR_ENTITY = "calendar_entity"

# Defaults
DEFAULT_CAL_FILE = "/config/.storage/local_calendar.dienstplan.ics"
DEFAULT_CAL_ENTITY = "calendar.dienstplan"
BACKUP_DIR = "/config/dienstplan_backups"
MAX_BACKUPS = 30

# Bundled Lovelace card
FRONTEND_URL = f"/{DOMAIN}/dienstplan-upload-card.js"
FRONTEND_FILE = f"custom_components/{DOMAIN}/frontend/dienstplan-upload-card.js"
