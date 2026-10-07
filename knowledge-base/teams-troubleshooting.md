# Microsoft Teams Desktop Client Troubleshooting

## Metadata

- Source Identifier: KB-COL-006
- Category: Collaboration and Email
- Last Updated: 2026-09-30

## Problem Description

Remediating common Microsoft Teams issues including audio/video device detection failures, screen sharing black screens, notification latency, and login loops.

## Symptoms

- Teams client stuck on "Loading Microsoft Teams..." splash screen.
- Microphone or webcam device not detected during meetings.
- Screen sharing shows a black rectangular box to other attendees.

## Preconditions

- Windows 10/11 or macOS with Microsoft Teams work account.
- Active network connection with UDP ports 3478-3481 permitted for media traffic.

## Resolution Steps

1. Clear the Microsoft Teams client cache:
   - Completely quit Teams by right-clicking the Teams icon in the system tray and choosing "Quit".
   - On Windows: Press Win+R, type `%appdata%\Microsoft\Teams` (or for the new Teams client: `%localappdata%\Packages\MSTeams_8wekyb3d8bbwe\LocalCache\Roaming\Microsoft\Teams`), and delete all files in the directory.
   - On macOS: Run `rm -rf ~/Library/Application\ Support/Microsoft/Teams`.
   - Relaunch Microsoft Teams.
2. Check peripheral privacy permissions:
   - On Windows: Open Settings > Privacy & Security > Camera & Microphone. Verify "Let desktop apps access your camera/microphone" is toggled On.
   - On macOS: Open System Settings > Privacy & Security > Screen Recording, Camera, and Microphone, and ensure Microsoft Teams is checked.
3. Test using Teams Web Client:
   - Navigate to `https://teams.microsoft.com` in Google Chrome or Microsoft Edge.
   - Verify if calls and chat work in the browser.
4. Update display drivers:
   - Outdated GPU drivers cause black screens during screen sharing. Update display drivers via Windows Update or device manufacturer.

## Escalation Conditions

- Corporate tenant-wide Microsoft 365 incident (advisory recorded in M365 Admin Center).
- Call quality degradation caused by corporate gateway packet loss exceeding 5%.
- User account missing Teams Enterprise Voice license for dial-in conferencing.
- Escalate to the Collaboration Support assignment group.
