"""Data update coordinator for the FortiGate integration."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    FortiGateApi,
    FortiGateApiError,
    FortiGateAuthError,
    FortiGateDevice,
    Policy,
)
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

type FortiGateConfigEntry = ConfigEntry[FortiGateCoordinator]


class FortiGateCoordinator(DataUpdateCoordinator[dict[int, Policy]]):
    """Polls the firewall policy table on a fixed interval."""

    config_entry: FortiGateConfigEntry
    device: FortiGateDevice

    def __init__(
        self,
        hass: HomeAssistant,
        entry: FortiGateConfigEntry,
        api: FortiGateApi,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.api = api

    async def _async_setup(self) -> None:
        try:
            self.device = await self.api.get_status()
        except FortiGateAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except FortiGateApiError as err:
            raise UpdateFailed(str(err)) from err

    async def _async_update_data(self) -> dict[int, Policy]:
        try:
            return await self.api.get_policies()
        except FortiGateAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except FortiGateApiError as err:
            raise UpdateFailed(str(err)) from err
