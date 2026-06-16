"""Config and options flow for the Dienstplan Import integration (UI setup)."""

from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
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


def _build_schema(defaults: dict) -> vol.Schema:
    """Form schema, pre-filled with the given defaults."""
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
            vol.Optional(
                CONF_WEBHOOK_ID,
                default=defaults.get(CONF_WEBHOOK_ID, ""),
            ): selector.TextSelector(),
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

        return self.async_show_form(step_id="user", data_schema=_build_schema({}))

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return DienstplanImportOptionsFlow(config_entry)


class DienstplanImportOptionsFlow(config_entries.OptionsFlow):
    """Edit the settings later via the UI."""

    def __init__(self, config_entry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = {**self.config_entry.data, **self.config_entry.options}
        return self.async_show_form(step_id="init", data_schema=_build_schema(current))
