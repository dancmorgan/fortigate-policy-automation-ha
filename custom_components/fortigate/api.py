"""Thin async client for the FortiOS REST API."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)

REQUEST_TIMEOUT = 15

POLICY_FORMAT = "policyid|name|status|srcintf|dstintf|action|comments"


class FortiGateApiError(Exception):
    """Raised when the FortiGate API returns an error or is unreachable."""


class FortiGateAuthError(FortiGateApiError):
    """Raised when the API token is rejected (401/403)."""


@dataclass(slots=True)
class FortiGateDevice:
    """Identity of the FortiGate appliance."""

    hostname: str
    model: str
    serial: str
    version: str


@dataclass(slots=True)
class PolicyStats:
    """Traffic statistics for a firewall policy."""

    hit_count: int | None
    bytes: int | None


@dataclass(slots=True)
class Policy:
    """A firewall policy as returned by the policy list call."""

    policy_id: int
    name: str
    enabled: bool
    srcintf: list[str]
    dstintf: list[str]
    action: str
    comments: str = ""
    hit_count: int | None = None
    bytes: int | None = None


class FortiGateApi:
    """Minimal async client for the endpoints this integration uses."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        host: str,
        token: str,
        vdom: str = "root",
    ) -> None:
        self._session = session
        self._base_url = f"https://{host}/api/v2"
        self._token = token
        self._vdom = vdom

    async def _request(
        self,
        method: str,
        path: str,
        params: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{self._base_url}{path}"
        query = {"vdom": self._vdom}
        if params:
            query.update(params)
        headers = {"Authorization": f"Bearer {self._token}"}
        _LOGGER.debug("%s %s (vdom=%s)", method, url, self._vdom)
        try:
            async with asyncio.timeout(REQUEST_TIMEOUT):
                response = await self._session.request(
                    method, url, params=query, json=json, headers=headers
                )
                if response.status in (401, 403):
                    raise FortiGateAuthError(
                        f"Authentication rejected (HTTP {response.status}); check the "
                        "API token and trusted hosts"
                    )
                if response.status >= 400:
                    body = await response.text()
                    raise FortiGateApiError(
                        f"{method} {path} failed: HTTP {response.status}: {body[:200]}"
                    )
                data: dict[str, Any] = await response.json(content_type=None)
        except TimeoutError as err:
            raise FortiGateApiError(f"Timeout talking to {url}") from err
        except aiohttp.ClientError as err:
            raise FortiGateApiError(f"Error talking to {url}: {err}") from err
        return data

    async def get_status(self) -> FortiGateDevice:
        """Return device identity from /monitor/system/status."""
        data = await self._request("GET", "/monitor/system/status")
        results = data.get("results") or {}
        model_name = results.get("model_name") or "FortiGate"
        model_number = results.get("model_number") or ""
        return FortiGateDevice(
            hostname=results.get("hostname") or "FortiGate",
            model=f"{model_name} {model_number}".strip(),
            serial=data.get("serial") or results.get("serial") or "",
            version=data.get("version") or "",
        )

    async def get_policies(self) -> dict[int, Policy]:
        """Return the firewall policy table keyed by policy id."""
        data = await self._request(
            "GET", "/cmdb/firewall/policy", params={"format": POLICY_FORMAT}
        )
        policies: dict[int, Policy] = {}
        for raw in data.get("results") or []:
            policy_id = raw.get("policyid")
            if policy_id is None:
                continue
            policy_id = int(policy_id)
            policies[policy_id] = Policy(
                policy_id=policy_id,
                name=raw.get("name") or f"Policy {policy_id}",
                enabled=raw.get("status") == "enable",
                srcintf=[i["name"] for i in raw.get("srcintf") or [] if "name" in i],
                dstintf=[i["name"] for i in raw.get("dstintf") or [] if "name" in i],
                action=raw.get("action") or "",
                comments=raw.get("comments") or "",
            )
        return policies

    async def get_policy_stats(self) -> dict[int, PolicyStats]:
        """Return per-policy traffic statistics keyed by policy id."""
        data = await self._request("GET", "/monitor/firewall/policy")
        stats: dict[int, PolicyStats] = {}
        for raw in data.get("results") or []:
            policy_id = raw.get("policyid")
            if policy_id is None:
                continue
            stats[int(policy_id)] = PolicyStats(
                hit_count=raw.get("hit_count"),
                bytes=raw.get("bytes"),
            )
        return stats

    async def set_policy_status(self, policy_id: int, enabled: bool) -> None:
        """Enable or disable a single firewall policy."""
        await self._request(
            "PUT",
            f"/cmdb/firewall/policy/{policy_id}",
            json={"status": "enable" if enabled else "disable"},
        )

    async def set_policy_action(self, policy_id: int, allow: bool) -> None:
        """Set a single firewall policy's action to accept or deny."""
        await self._request(
            "PUT",
            f"/cmdb/firewall/policy/{policy_id}",
            json={"action": "accept" if allow else "deny"},
        )
