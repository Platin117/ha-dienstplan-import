"""
Dienstplan Import — Home Assistant custom integration.

Merges an ICS file (produced by the Dienstplan Scanner) into an existing
local_calendar named "Dienstplan", in place, keeping history. Provides:

  * a service `dienstplan_import.import_ics` (used by the bundled upload card
    over the authenticated connection), and
  * an optional webhook (enabled when a webhook ID is configured) so the web
    app's "To Home Assistant" button can push directly.

Set up entirely through the UI (config flow) — no YAML editing required. The
bundled Lovelace card is auto-registered as a frontend resource.
"""

import logging

import voluptuous as vol

from homeassistant.components import persistent_notification, webhook
from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .const import (
    BACKUP_DIR,
    CONF_CALENDAR_ENTITY,
    CONF_CALENDAR_FILE,
    CONF_LOCAL_ONLY,
    CONF_WEBHOOK_ID,
    DEFAULT_CAL_ENTITY,
    DEFAULT_CAL_FILE,
    DOMAIN,
    FRONTEND_FILE,
    FRONTEND_URL,
    MAX_BACKUPS,
)
from .merge import merge_ics_file

_LOGGER = logging.getLogger(__name__)

SERVICE_SCHEMA = vol.Schema(
    {
        vol.Required("ics_content"): cv.string,
        vol.Optional("calendar_file"): cv.string,
        vol.Optional("calendar_entity"): cv.string,
    }
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up from a config entry created via the UI."""
    conf = {**entry.data, **entry.options}
    store = hass.data.setdefault(DOMAIN, {})
    store["calendar_file"] = conf.get(CONF_CALENDAR_FILE) or DEFAULT_CAL_FILE
    store["calendar_entity"] = conf.get(CONF_CALENDAR_ENTITY) or DEFAULT_CAL_ENTITY

    async def _do_import(ics_content, file_override=None, entity_override=None):
        cal_file = file_override or store["calendar_file"]
        cal_entity = entity_override or store["calendar_entity"]

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

    store["do_import"] = _do_import

    # ── Service (register once) ────────────────────────────────────────────────
    if not hass.services.has_service(DOMAIN, "import_ics"):

        async def handle_service(call: ServiceCall) -> None:
            do_import = hass.data[DOMAIN].get("do_import")
            if do_import:
                await do_import(
                    call.data["ics_content"],
                    call.data.get("calendar_file"),
                    call.data.get("calendar_entity"),
                )

        hass.services.async_register(
            DOMAIN, "import_ics", handle_service, schema=SERVICE_SCHEMA
        )

    # ── Optional webhook (re-register on reload) ───────────────────────────────
    _unregister_webhook(hass)
    webhook_id = (conf.get(CONF_WEBHOOK_ID) or "").strip()
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
            do_import = hass.data[DOMAIN].get("do_import")
            if do_import:
                await do_import(ics)

        webhook.async_register(
            hass,
            DOMAIN,
            "Dienstplan Import",
            webhook_id,
            handle_webhook,
            local_only=conf.get(CONF_LOCAL_ONLY, True),
            allowed_methods=["POST"],
        )
        store["webhook_id"] = webhook_id
        _LOGGER.info(
            "Dienstplan import webhook registered (local_only=%s)",
            conf.get(CONF_LOCAL_ONLY, True),
        )

    # ── Bundled Lovelace card (register once per HA run) ───────────────────────
    if not store.get("frontend_registered"):
        try:
            await hass.http.async_register_static_paths(
                [StaticPathConfig(FRONTEND_URL, hass.config.path(FRONTEND_FILE), False)]
            )
            add_extra_js_url(hass, FRONTEND_URL)
            store["frontend_registered"] = True
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("Could not register the upload card: %s", err)

    # Reload the entry when the options change.
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _unregister_webhook(hass)
    if hass.services.has_service(DOMAIN, "import_ics"):
        hass.services.async_remove(DOMAIN, "import_ics")
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry so option changes (webhook, calendar) take effect."""
    await hass.config_entries.async_reload(entry.entry_id)


def _unregister_webhook(hass: HomeAssistant) -> None:
    store = hass.data.get(DOMAIN, {})
    existing = store.pop("webhook_id", None)
    if existing:
        try:
            webhook.async_unregister(hass, existing)
        except Exception:  # noqa: BLE001
            pass
