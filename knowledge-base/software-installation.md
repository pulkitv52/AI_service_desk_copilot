# Enterprise Software Installation and Service Requests

## Metadata

- Source Identifier: KB-EUC-004
- Category: Software and Applications
- Last Updated: 2026-09-25

## Problem Description

Standard procedure for requesting, installing, and licensing approved corporate software packages on managed endpoints without requiring local Administrator privileges.

## Symptoms

- Employee needs development tools (such as Visual Studio Code, Git, Docker Desktop, PyCharm).
- Employee encounters UAC credential prompt asking for administrator password when running downloaded installers.

## Preconditions

- Corporate managed Windows or macOS laptop.
- Device is enrolled in Microsoft Intune or Jamf Pro device management.

## Resolution Steps

1. Use the Corporate Self-Service Portal (Company Portal):
   - On Windows: Click Start, search for "Company Portal", and launch the application.
   - On macOS: Open Applications and launch "Self Service".
2. Search the catalog for the required application:
   - Development Tools: Visual Studio Code, Git for Windows, Node.js LTS, Python 3.
   - Collaboration: Microsoft Teams, Slack, Zoom Enterprise.
   - Productivity: Microsoft 365 Apps, Adobe Acrobat Reader.
3. Click "Install". Company Portal executes the installation in system context with silent flags, bypassing the need for local administrator credentials.
4. Verify application launch from the Start Menu or Applications folder.

## Escalation Conditions

- The requested software requires paid licensing or management approval (e.g., JetBrains All Products Pack, Docker Desktop Business, Adobe Creative Cloud).
  - Submit a formal Service Request through the ServiceNow Service Catalog (Hardware & Software Requests).
- Company Portal reports "Installation Failed" with an error code (such as 0x87D1041C).
- The required software is an unapproved or open-source tool not in the catalog.
  - Requires IT Architecture and Security risk assessment review.
- Escalate unresolved installation failures to End User Computing.
