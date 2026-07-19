"""The FortiGate integration."""

from __future__ import annotations

from homeassistant.const import CONF_API_TOKEN, CONF_HOST, CONF_VERIFY_SSL, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import FortiGateApi
from .const import CONF_VDOM, DEFAULT_VDOM, DOMAIN
from .coordinator import FortiGateConfigEntry, FortiGateCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.SWITCH]


async def async_setup_entry(hass: HomeAssistant, entry: FortiGateConfigEntry) -> bool:
    """Set up FortiGate from a config entry."""
    session = async_get_clientsession(hass, entry.data[CONF_VERIFY_SSL])
    api = FortiGateApi(
        session,
        entry.data[CONF_HOST],
        entry.data[CONF_API_TOKEN],
        entry.data.get(CONF_VDOM, DEFAULT_VDOM),
    )
    coordinator = FortiGateCoordinator(hass, entry, api)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    device = coordinator.device
    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, device.serial)},
        name=device.hostname,
        manufacturer="Fortinet",
        model=device.model,
        sw_version=device.version,
        serial_number=device.serial,
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: FortiGateConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
