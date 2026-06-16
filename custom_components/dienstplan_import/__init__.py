"""
Dienstplan Import — Home Assistant custom integration.

Merges an ICS file (produced by the Dienstplan Scanner) into an existing
local_calendar named "Dienstplan", in place, keeping history. Provides:

  * a service `dienstplan_import.import_ics` (used by the bundled upload card
    over the authenticated connection), and
  * an optional webhook (enabled when `webhook_id` is configured) so the web
    app's "To Home Assistant" button can push directly.

The bundled Lovelace card is auto-registered as a frontend resource — no manual
resource setup needed.
"""

import logging

import voluptuous as vol

from homeassistant.components import persistent_notification, webhook
from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .merge import merge_ics_file

_LOGGER = logging.getLogger(__name__)

DOMAIN = "dienstplan_import"

DEFAULT_CAL_FILE = "/config/.storage/local_calendar.dienstplan.ics"
DEFAULT_CAL_ENTITY = "calendar.dienstplan"
BACKUP_DIR = "/config/dienstplan_backups"
MAX_BACKUPS = 30

CONF_WEBHOOK_ID = "webhook_id"
CONF_LOCAL_ONLY = "local_only"
CONF_CALENDAR_FILE = "calendar_file"
CONF_CALENDAR_ENTITY = "calendar_entity"

FRONTEND_URL = f"/{DOMAIN}/dienstplan-upload-card.js"
FRONTEND_FILE = f"custom_components/{DOMAIN}/frontend/dienstplan-upload-card.js"

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.All(
            lambda value: value or {},
            vol.Schema(
                {
                    vol.Optional(CONF_WEBHOOK_ID): cv.string,
                    vol.Optional(CONF_LOCAL_ONLY, default=True): cv.boolean,
                    vol.Optional(CONF_CALENDAR_FILE, default=DEFAULT_CAL_FILE): cv.string,
                    vol.Optional(CONF_CALENDAR_ENTITY, default=DEFAULT_CAL_ENTITY): cv.string,
                }
            ),
        )
    },
    extra=vol.ALLOW_EXTRA,
)

SERVICE_SCHEMA = vol.Schema(
    {
        vol.Required("ics_content"): cv.string,
        vol.Optional("calendar_file"): cv.string,
        vol.Optional("calendar_entity"): cv.string,
    }
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the integration from configuration.yaml."""
    conf = config.get(DOMAIN) or {}
    default_file = conf.get(CONF_CALENDAR_FILE, DEFAULT_CAL_FILE)
    default_entity = conf.get(CONF_CALENDAR_ENTITY, DEFAULT_CAL_ENTITY)

    async def _do_import(ics_content, file_override=None, entity_override=None):
        cal_file = file_override or default_file
        cal_entity = entity_override or default_entity

        if not ics_content or "BEGIN:VCALENDAR" not in ics_content:
            persistent_notification.async_create(
                hass, "No valid ICS content received.", "Dienstplan import failed"
            )
            return

        try:
            result = await hass.async_add_executor_job(
                merge_ics_file, ics_content, cal_file, BACKUP_DIR, MAX_BACKUPS
            )
        except Exception as err:  # noqa: BLE001
            _LOGGER.error("Merge failed: %s", err)
            persistent_notification.async_create(
                hass, f"Import failed: {err}", "Dienstplan import failed"
            )
            return

        try:
            await hass.services.async_call(
                "homeassistant",
                "reload_config_entry",
                {"entity_id": cal_entity},
                blocking=True,
            )
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("reload_config_entry failed: %s", err)

        msg = (
            f"Period {result['range_start']} to {result['range_end']} updated.\n"
            f"New/updated: {result['added']} • replaced: {result['removed']} • "
            f"unchanged (archive): {result['kept']}"
        )
        _LOGGER.info("Dienstplan import: %s", msg.replace("\n", " "))
        persistent_notification.async_create(hass, msg, "Dienstplan import successful")

    # ── Service ──────────────────────────────────────────────────────────────
    async def handle_service(call: ServiceCall) -> None:
        await _do_import(
            call.data["ics_content"],
            call.data.get("calendar_file"),
            call.data.get("calendar_entity"),
        )

    hass.services.async_register(DOMAIN, "import_ics", handle_service, schema=SERVICE_SCHEMA)

    # ── Optional webhook (for the web app's push button) ───────────────────────
    webhook_id = conf.get(CONF_WEBHOOK_ID)
    if webhook_id:

        async def handle_webhook(hass, webhook_id, request):
            try:
                content_type = request.content_type or ""
                if "json" in content_type:
                    data = await request.json()
                else:
                    data = await request.post()
                ics = data.get("ics")
            except Exception as err:  # noqa: BLE001
                _LOGGER.error("Webhook payload could not be parsed: %s", err)
                return
            await _do_import(ics)

        webhook.async_register(
            hass,
            DOMAIN,
            "Dienstplan Import",
            webhook_id,
            handle_webhook,
            local_only=conf.get(CONF_LOCAL_ONLY, True),
            allowed_methods=["POST"],
        )
        _LOGGER.info("Dienstplan import webhook registered (local_only=%s)", conf.get(CONF_LOCAL_ONLY, True))

    # ── Bundled Lovelace card (auto-registered) ────────────────────────────────
    try:
        await hass.http.async_register_static_paths(
            [StaticPathConfig(FRONTEND_URL, hass.config.path(FRONTEND_FILE), False)]
        )
        add_extra_js_url(hass, FRONTEND_URL)
    except Exception as err:  # noqa: BLE001
        _LOGGER.warning("Could not register the upload card: %s", err)

    return True
