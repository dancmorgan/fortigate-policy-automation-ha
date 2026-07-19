"""Constants for the FortiGate integration."""

from __future__ import annotations

DOMAIN = "fortigate_policy_automation"

CONF_VDOM = "vdom"

DEFAULT_VDOM = "root"
DEFAULT_SCAN_INTERVAL = 30

ATTR_POLICY_ID = "policy_id"
ATTR_SRCINTF = "srcintf"
ATTR_DSTINTF = "dstintf"

# Accept-only settings FortiOS clears or resets when a policy's action
# changes to deny. Snapshotted before the switch and restored on re-allow.
# Keys missing from a given FortiOS version are simply skipped.
ACTION_SNAPSHOT_FIELDS = (
    "nat",
    "natip",
    "ippool",
    "poolname",
    "fixedport",
    "utm-status",
    "profile-protocol-options",
    "ssl-ssh-profile",
    "av-profile",
    "webfilter-profile",
    "dnsfilter-profile",
    "emailfilter-profile",
    "spamfilter-profile",
    "dlp-sensor",
    "application-list",
    "ips-sensor",
    "voip-profile",
    "icap-profile",
    "waf-profile",
    "traffic-shaper",
    "traffic-shaper-reverse",
    "per-ip-shaper",
)
