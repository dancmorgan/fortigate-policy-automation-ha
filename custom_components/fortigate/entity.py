"""Base entity for FortiGate firewall policy entities."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import Policy
from .const import DOMAIN
from .coordinator import FortiGateCoordinator


class FortiGatePolicyEntity(CoordinatorEntity[FortiGateCoordinator]):
    """An entity that belongs to one firewall policy device."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: FortiGateCoordinator, policy_id: int) -> None:
        super().__init__(coordinator)
        self._policy_id = policy_id
        serial = coordinator.device.serial
        policy = coordinator.data[policy_id]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{serial}_policy_{policy_id}")},
            name=policy.name,
            manufacturer="Fortinet",
            model="Firewall policy",
            via_device=(DOMAIN, serial),
        )

    @property
    def _policy(self) -> Policy | None:
        return self.coordinator.data.get(self._policy_id)

    @property
    def available(self) -> bool:
        return super().available and self._policy is not None
