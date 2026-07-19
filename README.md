# FortiGate Policy Automation for Home Assistant

I built this to turn off home cameras / microphones / other remote monitoring devices when I am home to prevent surveillance or monitoring.

Control your FortiGate firewall policies straight from Home Assistant. Every firewall policy appears as its own device with two simple toggles:

- **Policy Enabled** turns the policy on or off, exactly like the enable/disable toggle in the FortiGate interface.
- **Policy Action Allow** flips the policy between allow (accept) and deny.

Each policy also gets two counters, ready for dashboards and graphs:

- **Hits** counts how many times the policy has matched traffic.
- **Bytes** tracks how much data has passed through the policy.

Policy devices are named by their policy ID, which never changes on the FortiGate. The current policy name and its comment are exposed as **Policy Name** and **Policy Comment** sensors, so renames on the firewall show up in Home Assistant within one polling cycle.

Use them on dashboards or in automations, for example to cut off internet access to the kids' devices at bedtime, or to open a rule only while you are home.

Everything runs locally over the FortiGate's REST API. There is no cloud dependency, and Home Assistant checks the firewall every 30 seconds so the toggles always reflect what the firewall is really doing.

## Before you start

You will need three things:

1. **FortiOS 7.x** on your FortiGate (6.4 or newer may work but is not tested).
2. **HTTPS enabled on the interface Home Assistant connects through.** The REST API is only reachable over HTTPS, so make sure it is switched on for the right interface: in the FortiGate interface go to **Network > Interfaces**, edit the interface that faces Home Assistant (usually your LAN interface), and tick **HTTPS** under **Administrative Access**. Save the change.
3. **A REST API administrator token.** See the next section.

### Creating the API token

1. On the FortiGate, go to **System > Admin Profiles** and create a new profile. Give it **Read/Write** access to **Firewall > Policy** and **Read** access to **System**, and leave everything else at **None**.
2. Go to **System > Administrators**, choose **Create New > REST API Admin**, and give it the profile you just created.
3. Under **Trusted Hosts**, add your Home Assistant IP address so nothing else can use the token.
4. When you save, the FortiGate shows the token **once**. Copy it somewhere safe; you will paste it into Home Assistant in a moment.

## Installation

This integration is installed through [HACS](https://hacs.xyz), the community store for Home Assistant. If you do not have HACS yet, follow the [HACS installation guide](https://hacs.xyz/docs/use/) first.

1. In Home Assistant, open **HACS** from the sidebar.
2. Click the three-dot menu in the top right and choose **Custom repositories**.
3. Paste `https://github.com/dancmorgan/fortigate-policy-switch-ha` as the repository, choose **Integration** as the type, and click **Add**.
4. Search HACS for **FortiGate Policy Automation** and open it.
5. Click **Download**, confirm, and then restart Home Assistant when prompted.
6. After the restart, go to **Settings > Devices & services**, click **Add integration**, and search for **FortiGate Policy Automation**.
7. Enter your FortiGate's hostname or IP address, paste the API token, and leave the VDOM as `root` unless you use multiple VDOMs. If your FortiGate uses a self-signed certificate, untick **Verify SSL certificate**.

That's it. Your firewall policies will appear under **Settings > Devices & services > FortiGate Policy Automation**, one device per policy, all linked to the FortiGate itself.

## Good to know

- Toggling **Policy Action Allow** off changes the policy's action to deny; the policy stays enabled, it just blocks instead of allows. IPsec policies do not get this toggle because their action must not change.
- FortiOS normally resets accept-only settings such as NAT, security profiles and traffic shapers when a policy's action changes to deny. The integration saves those settings just before switching to deny and restores them when re-allowing, so they survive the round trip. This only works when the switch to deny was made through Home Assistant; if the action was changed directly on the firewall, there is nothing saved to restore.
- If a policy is deleted on the FortiGate, its toggles become unavailable in Home Assistant.
- The hit and byte counters reset when the FortiGate reboots or when you clear them on the firewall. Home Assistant's long-term statistics understand these resets, so graphs stay accurate.
- If you rotate the API token, Home Assistant will prompt you to re-enter it.

## Security notes

- Use a dedicated REST API administrator with the minimal profile described above, never a full administrator account.
- Restrict the administrator's trusted hosts to your Home Assistant IP address.
- Prefer a proper certificate on the FortiGate; only disable SSL verification for self-signed certificates on a trusted network.
- The token is stored in Home Assistant's config entry storage.

## Out of scope

- Presence detection (the core `fortios` integration covers this)
- Creating, deleting or editing policies beyond the two toggles above
- FortiManager or FortiCloud managed devices
