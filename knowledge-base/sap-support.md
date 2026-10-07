# SAP ERP and Fiori Purchase Order Authorization Support

## Metadata

- Source Identifier: KB-APP-007
- Category: Enterprise Applications
- Last Updated: 2026-10-02

## Problem Description

Resolving authorization failures, release strategy lockouts, and gateway timeouts when approving or modifying Purchase Orders (PO) in SAP GUI and SAP Fiori launchpad.

## Symptoms

- User receives "You are not authorized to use transaction ME28 or ME29N" (authorization object `M_EINK_FRG`).
- Fiori tile "Manage Purchase Orders" or "My Inbox - Approve Purchase Orders" displays error "RFC call failed" or "Backend HTTP 500".
- Purchasing document is locked by another user session (Lock table entry error).

## Preconditions

- Employee has an active SAP user master record in production client (PRD 100).
- Corporate network connection or active GlobalProtect VPN tunnel.

## Resolution Steps

1. Verify SAP GUI connection and server status:
   - Ensure you are connected to the production system `PRD - Global ERP` with application server `sap-prd-app01.corp.internal`.
   - If connecting remotely, verify GlobalProtect VPN is connected.
2. Check authorization trace:
   - In SAP GUI, open transaction `/nSU53` immediately after encountering the authorization failure.
   - Note the missing authorization object, field value, and activity (ACTVT).
   - If the missing object is `M_BANF_FRG` (Requisition Release) or `M_EINK_FRG` (PO Release), verify if your approval limit matches the PO monetary value.
3. Release orphaned session locks:
   - If the error states "Document is currently locked by user X", check with the named user to ensure they exited transaction ME22N/ME29N.
   - If the lock was orphaned by a network disconnect, contact your SAP Basis administrator to review transaction `SM12` lock entries.
4. Fiori browser cache cleanup:
   - In Google Chrome or Edge, clear cached site data for the SAP Fiori Launchpad domain (`https://fiori.erp.corp.internal`).
   - Hard refresh with Ctrl+F5.

## Escalation Conditions

- Missing business role assignment required for standard job function (submit GRC Access Request via SAP GRC portal).
- SAP Basis system error or dump (e.g., `RFC_ERROR_COMMUNICATION` or `TIME_OUT` dump visible in `ST22`).
- Approval workflow stuck due to inactive organizational hierarchy.
- Escalate to the SAP Support assignment group with details from `/nSU53` or Fiori error logs.
