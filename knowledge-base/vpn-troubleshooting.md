# Corporate VPN Connectivity Troubleshooting

## Metadata

- Source Identifier: KB-NET-002
- Category: Network and Connectivity
- Last Updated: 2026-09-20

## Problem Description

Troubleshooting connection failures, gateway authentication drops, and latency issues when connecting to the corporate GlobalProtect VPN.

## Symptoms

- GlobalProtect client displays "Connection failed" or "Gateway not responding".
- The client gets stuck in the "Connecting" loop indefinitely.
- Corporate intranet websites and internal Git/SAP systems are unreachable after connecting.

## Preconditions

- Laptop is connected to a stable local Wi-Fi or wired internet connection with public internet access.
- Valid corporate credentials and MFA token.

## Resolution Steps

1. Verify local internet connectivity:
   - Disconnect from VPN.
   - Open a browser and test public internet access (e.g. `https://google.com`).
   - If local internet fails, restart your local Wi-Fi router.
2. Restart the GlobalProtect Service:
   - On Windows: Right-click the GlobalProtect taskbar icon, select "Settings", go to the "Troubleshooting" tab, and click "Restart Service".
   - Alternatively, open PowerShell as Administrator and run: `Restart-Service -Name PanGPS`.
   - On macOS: Run `launchctl kickstart -k system/com.paloaltonetworks.gp.pangps`.
3. Clear saved portal credentials:
   - Open GlobalProtect settings, go to the "General" tab, and click "Sign Out".
   - Re-enter the portal address `vpn.corp.internal` and authenticate with SSO and MFA.
4. Switch to an alternate gateway:
   - If the Primary Gateway (US-East) is degraded, select Secondary Gateway (US-West or EU-Central) from the Gateway dropdown list.
5. Disable conflicting third-party network adapters or personal VPNs.

## Escalation Conditions

- GlobalProtect throws SSL certificate error or untrusted root certificate warning.
- User account is missing from the Active Directory VPN Security Group (`VPN-Standard-Users`).
- Gateway shows 100% packet loss despite valid local internet connection.
- Escalate by raising an incident ticket assigned to the Network Support group with urgency Medium.
