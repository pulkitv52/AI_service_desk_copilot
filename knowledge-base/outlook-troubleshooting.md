# Microsoft Outlook and Mailbox Synchronization Troubleshooting

## Metadata

- Source Identifier: KB-COL-005
- Category: Collaboration and Email
- Last Updated: 2026-09-28

## Problem Description

Resolving mailbox synchronization delays, profile corruption, meeting calendar sync issues, and disconnected states in Microsoft Outlook desktop client.

## Symptoms

- Status bar at the bottom of Outlook indicates "Disconnected" or "Need Password".
- New emails received on mobile or Outlook Web App (OWA) do not appear in Outlook desktop client.
- Calendar invites and meeting updates fail to update meeting status.

## Preconditions

- Corporate Microsoft 365 Exchange Online mailbox.
- Device has an active internet connection.

## Resolution Steps

1. Verify Microsoft 365 cloud service status:
   - Log into Outlook Web Access at `https://outlook.office.com`.
   - If emails are visible on the web, the cloud mailbox is operational and the issue is restricted to the local client.
2. Reconnect and refresh authentication:
   - In Outlook, click on the "Send / Receive" tab and click "Update Folder" or "Send/Receive All Folders".
   - If prompted for credentials, re-enter corporate password and approve the MFA push notification.
3. Start Outlook in Safe Mode to isolate add-in conflicts:
   - Press Win+R, type `outlook.exe /safe`, and press Enter.
   - If Outlook functions normally in Safe Mode, disable third-party COM add-ins under File > Options > Add-ins > COM Add-ins > Go.
4. Repair Outlook Data File (OST):
   - Close Outlook.
   - Navigate to `%LOCALAPPDATA%\Microsoft\Outlook`.
   - Rename `username@corp.com.ost` to `username@corp.com.ost.old`.
   - Relaunch Outlook to automatically generate a fresh cached Exchange data file.
5. Quick Repair of Office 365 suite:
   - Open Windows Settings > Installed Apps > Microsoft 365 Apps > Modify > Quick Repair.

## Escalation Conditions

- Mailbox size quota exceeded (Exchange 50 GB or 100 GB limit reached).
- OWA web client also fails to load emails with HTTP 500 or mailbox unavailable errors.
- Shared mailbox or delegated permissions revoked in Exchange Admin Center.
- Escalate to the Collaboration Support assignment group.
