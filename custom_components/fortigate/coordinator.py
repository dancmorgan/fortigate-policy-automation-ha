"""Data update coordinator for the FortiGate integration."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    FortiGateApi,
    FortiGateApiError,
    FortiGateAuthError,
    FortiGateDevice,
    Policy,
)
from .const import ACTION_SNAPSHOT_FIELDS, DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

SNAPSHOT_STORAGE_VERSION = 1

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
        self._snapshots: dict[str, dict[str, Any]] = {}
        self._snapshot_store: Store[dict[str, dict[str, Any]]] = Store(
            hass, SNAPSHOT_STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}_snapshots"
        )

    async def _async_setup(self) -> None:
        self._snapshots = await self._snapshot_store.async_load() or {}
        try:
            self.device = await self.api.get_status()
        except FortiGateAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except FortiGateApiError as err:
            raise UpdateFailed(str(err)) from err

    async def async_set_policy_action(self, policy_id: int, allow: bool) -> None:
        """Change a policy's action, preserving accept-only settings.

        FortiOS resets NAT, security profiles and shapers when a policy's
        action changes to deny. Snapshot those settings before denying and
        restore them in the same request that re-allows.
        """
        key = str(policy_id)
        if not allow:
            try:
                full = await self.api.get_policy(policy_id)
            except FortiGateApiError as err:
                _LOGGER.warning(
                    "Could not snapshot policy %s before switching to deny; "
                    "NAT and profile settings may reset when re-allowed: %s",
                    policy_id,
                    err,
                )
            else:
                self._snapshots[key] = {
                    field: full[field]
                    for field in ACTION_SNAPSHOT_FIELDS
                    if field in full
                }
                await self._snapshot_store.async_save(self._snapshots)
            await self.api.set_policy_action(policy_id, False)
            return

        restore = self._snapshots.get(key)
        try:
            await self.api.set_policy_action(policy_id, True, restore=restore)
        except FortiGateApiError:
            if restore is None:
                raise
            _LOGGER.warning(
                "Re-allowing policy %s with its saved NAT and profile settings "
                "failed; re-allowing without them. Check the policy's NAT "
                "settings on the FortiGate",
                policy_id,
            )
            await self.api.set_policy_action(policy_id, True)
            return
        if restore is not None:
            del self._snapshots[key]
            await self._snapshot_store.async_save(self._snapshots)

    async def _async_update_data(self) -> dict[int, Policy]:
        try:
            policies = await self.api.get_policies()
        except FortiGateAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except FortiGateApiError as err:
            raise UpdateFailed(str(err)) from err

        try:
            stats = await self.api.get_policy_stats()
        except FortiGateAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except FortiGateApiError as err:
            # Statistics are nice to have; keep the switches alive without them.
            _LOGGER.warning("Policy statistics unavailable: %s", err)
        else:
            for policy_id, policy_stats in stats.items():
                if (policy := policies.get(policy_id)) is not None:
                    policy.hit_count = policy_stats.hit_count
                    policy.bytes = policy_stats.bytes
        return policies
