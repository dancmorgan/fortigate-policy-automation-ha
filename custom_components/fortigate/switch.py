"""Switch entities for FortiGate firewall policies."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import FortiGateApiError
from .const import ATTR_ACTION, ATTR_DSTINTF, ATTR_POLICY_ID, ATTR_SRCINTF, DOMAIN
from .coordinator import FortiGateConfigEntry, FortiGateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FortiGateConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up one switch per firewall policy."""
    coordinator = entry.runtime_data
    known_ids: set[int] = set()

    @callback
    def _add_new_policies() -> None:
        new_ids = set(coordinator.data) - known_ids
        if not new_ids:
            return
        known_ids.update(new_ids)
        async_add_entities(
            FortiGatePolicySwitch(coordinator, policy_id)
            for policy_id in sorted(new_ids)
        )

    _add_new_policies()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_policies))


class FortiGatePolicySwitch(CoordinatorEntity[FortiGateCoordinator], SwitchEntity):
    """Enable/disable switch for a single firewall policy."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: FortiGateCoordinator, policy_id: int) -> None:
        super().__init__(coordinator)
        self._policy_id = policy_id
        device = coordinator.device
        self._attr_unique_id = f"{device.serial}_policy_{policy_id}"
        self.entity_id = f"switch.fortigate_policy_{policy_id}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device.serial)},
            name=device.hostname,
            manufacturer="Fortinet",
            model=device.model,
            serial_number=device.serial,
            sw_version=device.version,
        )

    @property
    def _policy(self):
        return self.coordinator.data.get(self._policy_id)

    @property
    def available(self) -> bool:
        return super().available and self._policy is not None

    @property
    def name(self) -> str:
        if (policy := self._policy) is not None:
            return policy.name
        return f"Policy {self._policy_id}"

    @property
    def is_on(self) -> bool | None:
        if (policy := self._policy) is None:
            return None
        return policy.enabled

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        attrs: dict[str, Any] = {ATTR_POLICY_ID: self._policy_id}
        if (policy := self._policy) is not None:
            attrs[ATTR_SRCINTF] = policy.srcintf
            attrs[ATTR_DSTINTF] = policy.dstintf
            attrs[ATTR_ACTION] = policy.action
        return attrs

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._async_set_status(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._async_set_status(False)

    async def _async_set_status(self, enabled: bool) -> None:
        try:
            await self.coordinator.api.set_policy_status(self._policy_id, enabled)
        except FortiGateApiError as err:
            raise HomeAssistantError(
                f"Failed to {'enable' if enabled else 'disable'} policy "
                f"{self._policy_id}: {err}"
            ) from err
        await self.coordinator.async_request_refresh()
