# FortiGate for Home Assistant

A custom Home Assistant integration that exposes FortiGate firewall policies as switch entities, so you can enable or disable policies from dashboards and automations.

## Features

- One switch per firewall policy: on means the policy is enabled
- Policy attributes: policy id, source and destination interfaces, action
- Device page with model, serial number and FortiOS version
- Config flow setup with reauthentication when the token is rotated
- Local polling of the FortiOS REST API every 30 seconds; no cloud dependency

## Requirements

- FortiOS 7.x (6.4+ may work but is not tested)
- A REST API administrator token (see security notes below)
- Home Assistant 2025.1 or newer

## Installation (manual, v0.1)

1. Copy the `custom_components/fortigate` folder into the `custom_components` directory of your Home Assistant configuration.
2. Restart Home Assistant.
3. Go to Settings, then Devices and services, then Add integration, and search for FortiGate.
4. Enter the host, API token, VDOM (default `root`) and whether to verify the SSL certificate.

## Creating the API token on the FortiGate

1. Create an administrator profile with write access limited to Firewall Policy (Policy and Objects, Policy) and read access to System for the status call.
2. Create a REST API administrator using that profile and note the token shown once at creation.
3. Restrict the administrator's trusted hosts to your Home Assistant IP address.

## Security notes

- Use a dedicated REST API administrator with the minimum profile described above, not a full admin.
- Restrict trusted hosts to the Home Assistant IP.
- The token is stored in Home Assistant's config entry storage.
- Prefer a proper certificate on the FortiGate; only disable SSL verification for self-signed certificates on a trusted network.

## Out of scope

- Presence detection (the core `fortios` integration covers this)
- Creating, deleting or editing policies beyond their enable/disable status
- FortiManager or FortiCloud managed devices

## Roadmap

- Options flow to select which policies get switches
- Diagnostics, tests and CI, then publication through HACS
- WAN interface sensors, VPN tunnel binary sensors and session count sensors
