"""Explicit, resumable PDI acceptance check. Run from backend/ with --create-demo."""

import argparse
import asyncio
import json
from pathlib import Path

from httpx import ASGITransport, AsyncClient

from app.core.config import get_settings
from app.integrations.servicenow import (
    ServiceNowError,
    ServiceNowProvider,
    get_ticketing_provider,
)
from app.main import app

STATE = Path(__file__).resolve().parents[1] / "sample-data" / "incident-demo.local"


async def run(create_demo: bool) -> None:
    cfg = get_settings()
    if not cfg.is_servicenow_configured:
        raise RuntimeError("Configure the real PDI credentials in .env first")
    provider = get_ticketing_provider()
    if not isinstance(provider, ServiceNowProvider):
        raise RuntimeError("The live acceptance check requires ServiceNowProvider")
    await provider.validate_references()
    print("ServiceNow credentials and configured caller/group references verified.")
    if not create_demo:
        print(
            "Read-only preflight complete. --create-demo explicitly creates one synthetic incident."
        )
        return
    STATE.parent.mkdir(parents=True, exist_ok=True)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://local-demo"
    ) as client:
        if STATE.exists():
            state = json.loads(STATE.read_text())
        else:
            started = await client.post("/api/conversations")
            started.raise_for_status()
            state = {"conversation_id": started.json()["id"]}
            # Persist the ID before sending issue or escalation, including on crashes.
            STATE.write_text(json.dumps(state, indent=2) + "\n")
        cid = state["conversation_id"]
        if not state.get("prepared"):
            response = await client.post(
                "/api/chat",
                json={
                    "session_id": cid,
                    "message": "Portfolio acceptance demo: GlobalProtect VPN is not connecting. The steps did not work.",
                },
            )
            response.raise_for_status()
            assert response.json()["response_type"] == "escalation_offered"
            declined = await client.post(
                "/api/chat",
                json={
                    "session_id": cid,
                    "message": "No thanks, do not create a ticket",
                },
            )
            declined.raise_for_status()
            assert declined.json()["ticket"] is None
            assert await provider.find_incident_by_correlation(cid) is None
            state["prepared"] = True
            STATE.write_text(json.dumps(state, indent=2) + "\n")
        accepted = await client.post(
            "/api/chat", json={"session_id": cid, "message": "Create a ticket"}
        )
        accepted.raise_for_status()
        result = accepted.json()
        if result["response_type"] != "ticket_created":
            print(
                "Incident outcome:",
                result["response_type"],
                "— rerun to reconcile this same conversation.",
            )
            return
        ticket = result["ticket"]
        again = await client.post(
            "/api/chat", json={"session_id": cid, "message": "Create a ticket"}
        )
        again.raise_for_status()
        assert again.json()["ticket"]["sys_id"] == ticket["sys_id"]
        confirmed = await provider.get_incident(ticket["sys_id"])
        assert confirmed is not None and confirmed.number == ticket["number"]
        expected_group = (
            "Network Support"
            if cfg.servicenow_group_ids.get("Network Support")
            else "Service Desk L1"
        )
        assert confirmed.assignment_group == expected_group
        assert confirmed.caller_id == cfg.servicenow_caller_sys_id
        matches = await provider.query_incidents(f"correlation_id={cid}", 2)
        assert len(matches) == 1
        audit = await client.get(f"/api/audit/{cid}")
        audit.raise_for_status()
        events = [event["event_type"] for event in audit.json()]
        assert {"escalation_declined", "escalation_accepted"}.issubset(events)
        assert any(event in events for event in ("ticket_created", "ticket_reconciled"))
        state.update(
            number=ticket["number"],
            sys_id=ticket["sys_id"],
            assignment_group=confirmed.assignment_group,
            audit_events=events,
            verified=True,
        )
        STATE.write_text(json.dumps(state, indent=2) + "\n")
        print(
            f"Verified {confirmed.number}: {confirmed.assignment_group}; decline created nothing; repeated acceptance reused one incident; audit retained."
        )
        print("Saved resumable result:", STATE)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--create-demo", action="store_true")
    args = parser.parse_args()
    try:
        asyncio.run(run(args.create_demo))
    except ServiceNowError as exc:
        print(
            f"ServiceNow verification incomplete (HTTP {exc.status_code}). Check PDI credentials, permissions, and caller/group settings."
        )
        raise SystemExit(1) from None
    except Exception as exc:
        # Never print raw external exceptions, request URLs, or credentials.
        print(
            f"Verification incomplete ({type(exc).__name__}). Check local settings and connectivity; retain the state file for reconciliation."
        )
        raise SystemExit(1) from None
