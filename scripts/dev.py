"""Linux local-service control used by Makefile. Never sources .env as shell code."""

import argparse
import fcntl
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / ".run"
STATE = RUNTIME / "services.json"


def run(command: list[str], cwd: Path = ROOT) -> None:
    subprocess.run(command, cwd=cwd, check=True)


def compose(*args: str) -> None:
    # Do not let Compose interpolate unrelated Gemini/ServiceNow credentials.
    # Parse only database keys with dotenv, preserving literal '$' characters.
    env = os.environ.copy()
    if (ROOT / ".env").exists():
        python = ROOT / "backend/.venv/bin/python"
        if not python.exists():
            raise RuntimeError("Run make setup before using database commands.")
        result = subprocess.run(
            [
                str(python),
                "-c",
                "import json; from dotenv import dotenv_values; "
                'v=dotenv_values(".env", interpolate=False); '
                'print(json.dumps({k:v[k] for k in ("POSTGRES_DB","POSTGRES_USER","POSTGRES_PASSWORD","POSTGRES_PORT") if v.get(k) is not None}))',
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        for key, value in json.loads(result.stdout).items():
            env.setdefault(key, value)
    subprocess.run(
        [
            "docker",
            "compose",
            "--env-file",
            "/dev/null",
            "--project-directory",
            str(ROOT),
            "-f",
            str(ROOT / "docker-compose.yml"),
            *args,
        ],
        cwd=ROOT,
        env=env,
        check=True,
    )


def require(*commands: str) -> None:
    missing = [name for name in commands if shutil.which(name) is None]
    if missing:
        raise RuntimeError("Missing commands: " + ", ".join(missing))


def read_state() -> dict:
    return json.loads(STATE.read_text()) if STATE.exists() else {}


def save_state(state: dict) -> None:
    temporary = STATE.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, indent=2) + "\n")
    temporary.replace(STATE)


def identity(pid: int) -> str | None:
    try:
        # Field 22 is starttime; comm (in parentheses) can contain spaces.
        fields = Path(f"/proc/{pid}/stat").read_text().rsplit(") ", 1)[1].split()
        return None if fields[0] == "Z" else fields[19]
    except (FileNotFoundError, ProcessLookupError):
        return None


def owned(record: dict) -> bool:
    pid = record.get("pid", 0)
    try:
        return (
            bool(record.get("identity"))
            and pid > 1
            and identity(pid) == record["identity"]
            and os.getpgid(pid) == pid
        )
    except ProcessLookupError:
        return False


def stop_app(name: str, state: dict) -> None:
    record = state.get(name)
    if not record:
        print(f"{name}: not managed")
        return
    if owned(record):
        os.killpg(record["pid"], signal.SIGTERM)
        deadline = time.monotonic() + 8
        while owned(record) and time.monotonic() < deadline:
            time.sleep(0.1)
        if owned(record):
            os.killpg(record["pid"], signal.SIGKILL)
        print(f"{name}: stopped")
    else:
        print(f"{name}: stale state removed; no unrelated process was stopped")
    state.pop(name, None)
    save_state(state)


def ready(url: str) -> bool:
    try:
        with urlopen(url, timeout=1) as response:
            return response.status == 200
    except (URLError, TimeoutError, OSError):
        return False


def ports() -> dict[str, int]:
    backend = os.environ.get("BACKEND_PORT", "").strip()
    if not backend:
        # Read only the non-secret port through the backend's actual config loader.
        result = subprocess.run(
            [
                "uv",
                "run",
                "--no-sync",
                "python",
                "-c",
                "from app.core.config import get_settings; print(get_settings().app_port)",
            ],
            cwd=ROOT / "backend",
            capture_output=True,
            text=True,
        )
        if result.returncode:
            raise RuntimeError(
                "Backend configuration unavailable. Run make setup and check .env."
            )
        backend = result.stdout.strip()
    result = {
        "backend": int(backend),
        "frontend": int(os.environ.get("FRONTEND_PORT", "5173")),
    }
    if (
        any(p < 1 or p > 65535 for p in result.values())
        or len(set(result.values())) != 2
    ):
        raise RuntimeError("Use distinct backend/frontend ports between 1 and 65535")
    return result


def launch(
    name: str, command: list[str], cwd: Path, port: int, state: dict, env: dict
) -> None:
    with (RUNTIME / f"{name}.log").open("ab") as log:
        process = subprocess.Popen(
            command,
            cwd=cwd,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    state[name] = {"pid": process.pid, "identity": identity(process.pid), "port": port}
    save_state(state)
    url = f"http://127.0.0.1:{port}" + ("/health" if name == "backend" else "/")
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"{name} exited. Inspect make logs SERVICE={name}.")
        if ready(url):
            print(f"{name}: ready at http://127.0.0.1:{port}", flush=True)
            return
        time.sleep(0.25)
    raise RuntimeError(
        f"{name} did not become ready. Inspect make logs SERVICE={name}."
    )


def start() -> None:
    require("docker", "uv", "pnpm")
    if (
        not (ROOT / ".env").exists()
        or not (ROOT / "backend/.venv").exists()
        or not (ROOT / "frontend/node_modules").exists()
    ):
        raise RuntimeError("Run make setup first, then configure .env.")
    selected = ports()
    state = read_state()
    for name, port in selected.items():
        if name in state and owned(state[name]):
            if state[name]["port"] != port:
                raise RuntimeError(
                    f"{name} is managed on another port. Run make stop-apps before changing ports."
                )
            continue
        with socket.socket() as probe:
            if probe.connect_ex(("127.0.0.1", port)) == 0:
                raise RuntimeError(
                    f"Port {port} is already occupied by an unmanaged process. Stop it yourself or override BACKEND_PORT/FRONTEND_PORT; it will not be killed."
                )
    compose("up", "-d", "--wait", "--wait-timeout", "60", "db")
    run(["uv", "run", "--no-sync", "alembic", "upgrade", "head"], ROOT / "backend")
    commands = {
        "backend": [
            "uv",
            "run",
            "--no-sync",
            "uvicorn",
            "app.main:app",
            "--reload",
            "--host",
            "127.0.0.1",
            "--port",
            str(selected["backend"]),
        ],
        "frontend": [
            "pnpm",
            "dev",
            "--host",
            "127.0.0.1",
            "--port",
            str(selected["frontend"]),
            "--strictPort",
        ],
    }
    started = []
    try:
        for name in ("backend", "frontend"):
            if name in state and owned(state[name]):
                print(
                    f'{name}: already running at http://127.0.0.1:{state[name]["port"]}'
                )
                continue
            started.append(name)
            env = {
                **os.environ,
                "BACKEND_PROXY_URL": f'http://127.0.0.1:{selected["backend"]}',
            }
            launch(name, commands[name], ROOT / name, selected[name], state, env)
    except BaseException:
        for name in reversed(started):
            stop_app(name, state)
        raise


def stop(apps_only: bool = False) -> None:
    state = read_state()
    for name in ("frontend", "backend"):
        stop_app(name, state)
    if not apps_only:
        require("docker")
        compose("stop", "db")
        print("Database stopped; its data volume is preserved.")


def status() -> None:
    state = read_state()
    for name in ("backend", "frontend"):
        record = state.get(name, {})
        if record and owned(record):
            url = f'http://127.0.0.1:{record["port"]}'
            healthy = ready(url + ("/health" if name == "backend" else "/"))
            print(
                f'{name}: managed, {"ready" if healthy else "not responding"}, PID {record["pid"]}, {url}',
                flush=True,
            )
        else:
            print(f"{name}: not running under make", flush=True)
    if shutil.which("docker"):
        compose("ps", "-a", "db")
    else:
        print("database: docker unavailable")


def logs(follow: bool) -> None:
    service = os.environ.get("SERVICE", "all")
    if service not in {"all", "backend", "frontend"}:
        raise RuntimeError("SERVICE must be all, backend, or frontend")
    files = [
        str(RUNTIME / f"{name}.log")
        for name in ("backend", "frontend")
        if service in {"all", name} and (RUNTIME / f"{name}.log").exists()
    ]
    if not files:
        print("No application logs yet. Run make start.")
        return
    run(["tail", "-n", "80", *(["-F"] if follow else []), *files])


def setup() -> None:
    require("uv", "pnpm")
    if not (ROOT / ".env").exists():
        shutil.copyfile(ROOT / ".env.example", ROOT / ".env")
        print("Created .env; configure credentials before using live integrations.")
    else:
        print("Existing .env preserved.")
    run(["uv", "sync", "--locked"], ROOT / "backend")
    run(["pnpm", "install", "--frozen-lockfile"], ROOT / "frontend")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=[
            "help",
            "setup",
            "start",
            "stop",
            "stop-apps",
            "restart",
            "status",
            "logs",
            "db-start",
            "db-stop",
            "db-logs",
        ],
    )
    parser.add_argument("--follow", action="store_true")
    args = parser.parse_args()
    if args.command == "help":
        for line in (ROOT / "Makefile").read_text().splitlines():
            if ": " in line and "## " in line:
                name = line.split(":", 1)[0]
                print(f'make {name:<16} {line.split("## ", 1)[1]}')
        return
    RUNTIME.mkdir(mode=0o700, exist_ok=True)
    with (RUNTIME / "control.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if args.command == "setup":
            setup()
        elif args.command == "start":
            start()
        elif args.command in {"stop", "stop-apps"}:
            stop(args.command == "stop-apps")
        elif args.command == "restart":
            stop()
            start()
        elif args.command == "status":
            status()
        elif args.command == "logs":
            # The viewer must not prevent start/stop commands while following.
            fcntl.flock(lock, fcntl.LOCK_UN)
            logs(args.follow)
        elif args.command == "db-start":
            compose("up", "-d", "--wait", "--wait-timeout", "60", "db")
        elif args.command == "db-stop":
            compose("stop", "db")
        elif args.command == "db-logs":
            fcntl.flock(lock, fcntl.LOCK_UN)
            compose("logs", "--tail=80", "--follow", "db")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        raise SystemExit(130) from None
    except (RuntimeError, ValueError, subprocess.CalledProcessError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from None
