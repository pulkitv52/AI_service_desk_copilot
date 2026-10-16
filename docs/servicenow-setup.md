# ServiceNow PDI setup

This guide covers the existing Basic Auth integration for a local demonstration. Use a Personal Developer Instance and synthetic support issues. The default demo can run with `USE_MOCK_SERVICENOW=true` until this setup is complete.

## Create a dedicated integration account

In the PDI's user administration, create a service account such as `svc_service_desk`:

- Active checked; Locked out unchecked.
- Identity type Machine and Web service access only enabled where exposed by your instance's form.
- Password needs reset cleared after setting its password.
- Incident-management permissions required by the PDI. The verified demo used `itil`; review the applicable ACLs before choosing permissions for another environment.

Keep the interactive administrator account for browser administration. The integration does not require its password.

Save the user record before selecting Set Password. Generate or enter the password, copy it into your password manager, and select Save Password. The dialog may remain open while displaying a success message. Close it, check the reset/lockout flags, and select Update if you changed them.

## Configure the caller and assignment groups

Find an active synthetic employee/caller and active support groups in your PDI. Copy each record's 32-character sys_id. Configure the root `.env`:

```env
USE_MOCK_SERVICENOW=false
SERVICENOW_INSTANCE_URL=https://devXXXXX.service-now.com
SERVICENOW_USERNAME=svc_service_desk
SERVICENOW_PASSWORD='your-service-account-password'
SERVICENOW_TIMEOUT_SECONDS=10.0

SERVICENOW_CALLER_SYS_ID=<active-demo-caller-sys_id>
SERVICENOW_FALLBACK_GROUP_SYS_ID=<active-service-desk-group-sys_id>
SERVICENOW_GROUP_IDS={"Network Support":"<network-group-sys_id>","SAP Support":"<sap-group-sys_id>"}
```

Replace the placeholder IDs with real sys_ids. Prefer a separate synthetic employee as the caller, rather than the service account. The configured caller overrides a caller supplied by a chat client. Available logical group names are Identity & Access Support, Network Support, End User Computing, Collaboration Support, SAP Support, and Service Desk L1. A missing specialist mapping uses the configured fallback group.

Quote the password so `#` is not treated as a dotenv comment. Do not source `.env` in a shell. The Make controller passes only database settings to Compose, avoiding interpolation of application credentials containing `$`.

Restart the backend after changes. Use `make restart`, including any custom backend/frontend port overrides used at startup.

## Read-only preflight

With PostgreSQL running:

```bash
cd backend
PYTHONPATH=. uv run --no-sync python ../scripts/verify_servicenow.py
```

This checks credentials and configured caller/group references without creating an incident. The service account must be able to read the configured references as well as perform the incident operations used by the demo.

## Explicit live acceptance test

Only when ready to create a synthetic incident:

```bash
cd backend
PYTHONPATH=. uv run --no-sync python ../scripts/verify_servicenow.py --create-demo
```

This creates one synthetic VPN incident, checks the configured caller and routing, verifies refusal creates nothing, and checks that repeated acceptance returns the same incident. It stores a resumable conversation ID in ignored `sample-data/incident-demo.local`. Keep that file after a timeout; rerunning reconciles the same attempt. Deleting it starts a new demonstration and may create another incident.

The chat also creates real incidents after explicit acceptance while live ServiceNow mode is enabled. Use mock mode for screenshots and general UI exploration.

## Troubleshooting

| Symptom | Check |
|---|---|
| Browser login works, API returns 401 | Verify the service-account password, reset flag, active/lockout state, and Basic Auth eligibility. Browser login alone does not prove API access. |
| Log mentions `SNCRestrictBasicAuthUserAuthenticationGate` denying an interactive-login user | Use the dedicated web-service account and inspect the instance's policy; do not disable the restriction just to make admin credentials work. |
| API returns 403 | Check the account's table/field ACL permissions. Do not automatically grant administrator access. |
| Missing caller or assignment-group configuration | Check each sys_id and active record, including the fallback group. |
| Creation times out | Keep the conversation and local acceptance state; reconcile by correlation ID instead of sending another POST. |
| Multiple incidents match one correlation ID | Manual reconciliation is required. The workflow keeps another creation blocked. |

`GET /health` reports app/configuration status, not dependency reachability. The PDI integration was verified with one selected priority matrix; review your own impact/urgency rules if they differ. ServiceNow's returned ticket priority remains authoritative.
