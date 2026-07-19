"""Switch entities for FortiGate firewall policies."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import FortiGateApi, FortiGateApiError, Policy
from .const import ATTR_DSTINTF, ATTR_POLICY_ID, ATTR_SRCINTF
from .coordinator import FortiGateConfigEntry, FortiGateCoordinator
from .entity import FortiGatePolicyEntity


@dataclass(frozen=True, kw_only=True)
class FortiGatePolicySwitchDescription(SwitchEntityDescription):
    """Describes one toggle available on a firewall policy."""

    is_on_fn: Callable[[Policy], bool]
    set_fn: Callable[[FortiGateApi, int, bool], Coroutine[Any, Any, None]]
    suitable_fn: Callable[[Policy], bool] = lambda policy: True


SWITCH_DESCRIPTIONS: tuple[FortiGatePolicySwitchDescription, ...] = (
    FortiGatePolicySwitchDescription(
        key="status",
        translation_key="policy_status",
        is_on_fn=lambda policy: policy.enabled,
        set_fn=lambda api, policy_id, on: api.set_policy_status(policy_id, on),
    ),
    FortiGatePolicySwitchDescription(
        key="action",
        translation_key="policy_action",
        is_on_fn=lambda policy: policy.action == "accept",
        set_fn=lambda api, policy_id, on: api.set_policy_action(policy_id, on),
        # IPsec (and other non accept/deny) policies must keep their action.
        suitable_fn=lambda policy: policy.action in ("accept", "deny"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FortiGateConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up switches for every firewall policy."""
    coordinator = entry.runtime_data
    known_ids: set[int] = set()

    @callback
    def _add_new_policies() -> None:
        new_ids = set(coordinator.data) - known_ids
        if not new_ids:
            return
        known_ids.update(new_ids)
        async_add_entities(
            FortiGatePolicySwitch(coordinator, policy_id, description)
            for policy_id in sorted(new_ids)
            for description in SWITCH_DESCRIPTIONS
            if description.suitable_fn(coordinator.data[policy_id])
        )

    _add_new_policies()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_policies))


class FortiGatePolicySwitch(FortiGatePolicyEntity, SwitchEntity):
    """One toggle on a firewall policy device."""

    entity_description: FortiGatePolicySwitchDescription

    def __init__(
        self,
        coordinator: FortiGateCoordinator,
        policy_id: int,
        description: FortiGatePolicySwitchDescription,
    ) -> None:
        super().__init__(coordinator, policy_id)
        self.entity_description = description
        serial = coordinator.device.serial
        if description.key == "status":
            # Keep the v0.1 unique id and entity id for the enable/disable toggle.
            self._attr_unique_id = f"{serial}_policy_{policy_id}"
            self.entity_id = f"switch.fortigate_policy_{policy_id}"
        else:
            self._attr_unique_id = f"{serial}_policy_{policy_id}_{description.key}"
            self.entity_id = f"switch.fortigate_policy_{policy_id}_{description.key}"

    @property
    def is_on(self) -> bool | None:
        if (policy := self._policy) is None:
            return None
        return self.entity_description.is_on_fn(policy)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        attrs: dict[str, Any] = {ATTR_POLICY_ID: self._policy_id}
        if self.entity_description.key == "status" and (
            policy := self._policy
        ) is not None:
            attrs[ATTR_SRCINTF] = policy.srcintf
            attrs[ATTR_DSTINTF] = policy.dstintf
        return attrs

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._async_set(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._async_set(False)

    async def _async_set(self, on: bool) -> None:
        try:
            await self.entity_description.set_fn(
                self.coordinator.api, self._policy_id, on
            )
        except FortiGateApiError as err:
            raise HomeAssistantError(
                f"Failed to update {self.entity_description.key} of policy "
                f"{self._policy_id}: {err}"
            ) from err
        await self.coordinator.async_request_refresh()
