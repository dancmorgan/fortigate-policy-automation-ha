"""Sensor entities for FortiGate firewall policy statistics."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfInformation
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import Policy
from .coordinator import FortiGateConfigEntry, FortiGateCoordinator
from .entity import FortiGatePolicyEntity


@dataclass(frozen=True, kw_only=True)
class FortiGatePolicySensorDescription(SensorEntityDescription):
    """Describes one value available on a firewall policy."""

    value_fn: Callable[[Policy], int | str | None]


SENSOR_DESCRIPTIONS: tuple[FortiGatePolicySensorDescription, ...] = (
    FortiGatePolicySensorDescription(
        key="name",
        translation_key="policy_name",
        icon="mdi:rename-box",
        value_fn=lambda policy: policy.name,
    ),
    FortiGatePolicySensorDescription(
        key="comment",
        translation_key="policy_comment",
        icon="mdi:comment-text-outline",
        # None when empty so the sensor reads unknown rather than blank.
        value_fn=lambda policy: policy.comments or None,
    ),
    FortiGatePolicySensorDescription(
        key="hit_count",
        translation_key="policy_hit_count",
        icon="mdi:counter",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda policy: policy.hit_count,
    ),
    FortiGatePolicySensorDescription(
        key="bytes",
        translation_key="policy_bytes",
        icon="mdi:sort-numeric-descending",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.MEBIBYTES,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=2,
        value_fn=lambda policy: policy.bytes,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FortiGateConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up statistic sensors for every firewall policy."""
    coordinator = entry.runtime_data
    known_ids: set[int] = set()

    @callback
    def _add_new_policies() -> None:
        new_ids = set(coordinator.data) - known_ids
        if not new_ids:
            return
        known_ids.update(new_ids)
        async_add_entities(
            FortiGatePolicySensor(coordinator, policy_id, description)
            for policy_id in sorted(new_ids)
            for description in SENSOR_DESCRIPTIONS
        )

    _add_new_policies()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_policies))


class FortiGatePolicySensor(FortiGatePolicyEntity, SensorEntity):
    """One statistic on a firewall policy device."""

    entity_description: FortiGatePolicySensorDescription

    def __init__(
        self,
        coordinator: FortiGateCoordinator,
        policy_id: int,
        description: FortiGatePolicySensorDescription,
    ) -> None:
        super().__init__(coordinator, policy_id)
        self.entity_description = description
        serial = coordinator.device.serial
        self._attr_unique_id = f"{serial}_policy_{policy_id}_{description.key}"
        self.entity_id = f"sensor.fortigate_policy_{policy_id}_{description.key}"

    @property
    def native_value(self) -> int | str | None:
        if (policy := self._policy) is None:
            return None
        value = self.entity_description.value_fn(policy)
        if isinstance(value, str):
            # Entity states are capped at 255 characters.
            return value[:255]
        return value
