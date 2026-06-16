"""Config and options flow for the Dienstplan Import integration (UI setup)."""

from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components import webhook
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_CALENDAR_ENTITY,
    CONF_CALENDAR_FILE,
    CONF_LOCAL_ONLY,
    CONF_WEBHOOK_ID,
    DEFAULT_CAL_ENTITY,
    DEFAULT_CAL_FILE,
    DOMAIN,
)


def _build_schema(hass, defaults: dict) -> vol.Schema:
    """Form schema, pre-filled with the given defaults.

    The webhook ID defaults to a freshly generated random token (so the user
    doesn't have to invent one). Clear the field to disable the push webhook.
    """
    webhook_default = defaults.get(CONF_WEBHOOK_ID) or webhook.async_generate_id()
    return vol.Schema(
        {
            vol.Optional(
                CONF_CALENDAR_ENTITY,
                default=defaults.get(CONF_CALENDAR_ENTITY, DEFAULT_CAL_ENTITY),
            ): selector.EntitySelector(selector.EntitySelectorConfig(domain="calendar")),
            vol.Optional(
                CONF_CALENDAR_FILE,
                default=defaults.get(CONF_CALENDAR_FILE, DEFAULT_CAL_FILE),
            ): selector.TextSelector(),
            vol.Optional(CONF_WEBHOOK_ID, default=webhook_default): selector.TextSelector(),
            vol.Optional(
                CONF_LOCAL_ONLY,
                default=defaults.get(CONF_LOCAL_ONLY, True),
            ): selector.BooleanSelector(),
        }
    )


class DienstplanImportConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Initial UI setup."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            return self.async_create_entry(
                title="Dienstplan Import", data={}, options=user_input
            )

        return self.async_show_form(
            step_id="user", data_schema=_build_schema(self.hass, {})
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return DienstplanImportOptionsFlow(config_entry)


class DienstplanImportOptionsFlow(config_entries.OptionsFlow):
    """Edit the settings later via the UI.

    We store the entry under a private name (``_entry``) on purpose: in modern
    Home Assistant ``config_entry`` is a read-only property, and assigning to it
    raises — which made the options dialog fail with a 500. Using our own
    attribute works across all supported HA versions.
    """

    def __init__(self, config_entry) -> None:
        self._entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = {**self._entry.data, **self._entry.options}
        return self.async_show_form(
            step_id="init", data_schema=_build_schema(self.hass, current)
        )
