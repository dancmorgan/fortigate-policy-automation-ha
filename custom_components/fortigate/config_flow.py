"""Config flow for the FortiGate integration."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_API_TOKEN, CONF_HOST, CONF_VERIFY_SSL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import FortiGateApi, FortiGateApiError, FortiGateAuthError, FortiGateDevice
from .const import CONF_VDOM, DEFAULT_VDOM, DOMAIN

_LOGGER = logging.getLogger(__name__)

USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_API_TOKEN): str,
        vol.Optional(CONF_VDOM, default=DEFAULT_VDOM): str,
        vol.Optional(CONF_VERIFY_SSL, default=True): bool,
    }
)

REAUTH_SCHEMA = vol.Schema({vol.Required(CONF_API_TOKEN): str})


async def _validate(hass: HomeAssistant, data: Mapping[str, Any]) -> FortiGateDevice:
    """Check the credentials by fetching device status."""
    session = async_get_clientsession(hass, data[CONF_VERIFY_SSL])
    api = FortiGateApi(
        session,
        data[CONF_HOST],
        data[CONF_API_TOKEN],
        data.get(CONF_VDOM, DEFAULT_VDOM),
    )
    return await api.get_status()


class FortiGateConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the FortiGate config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                device = await _validate(self.hass, user_input)
            except FortiGateAuthError:
                errors["base"] = "invalid_auth"
            except FortiGateApiError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error validating FortiGate connection")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(device.serial)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=device.hostname, data=user_input
                )
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(USER_SCHEMA, user_input),
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Handle reauth when the API token is rejected."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for a replacement API token and validate it."""
        errors: dict[str, str] = {}
        reauth_entry = self._get_reauth_entry()
        if user_input is not None:
            data = {**reauth_entry.data, CONF_API_TOKEN: user_input[CONF_API_TOKEN]}
            try:
                await _validate(self.hass, data)
            except FortiGateAuthError:
                errors["base"] = "invalid_auth"
            except FortiGateApiError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error validating FortiGate connection")
                errors["base"] = "unknown"
            else:
                return self.async_update_reload_and_abort(reauth_entry, data=data)
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=REAUTH_SCHEMA,
            description_placeholders={CONF_HOST: reauth_entry.data[CONF_HOST]},
            errors=errors,
        )
