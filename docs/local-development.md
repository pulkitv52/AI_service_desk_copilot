# Local service commands

Run Make commands from the repository root. The controller targets Linux (process groups and `/proc`) and works with this repository's directory name, including its trailing space. It runs PostgreSQL through Docker Compose and the backend/frontend as managed local processes.

## First run

```bash
make setup
```

Requires Python 3.12+, GNU Make, uv, pnpm, Docker, and Docker Compose. Setup installs locked backend/frontend dependencies and creates `.env` from `.env.example` only when absent. It preserves existing credentials and model settings. Configure `.env` before using live Gemini or ServiceNow integrations.

```bash
make start
```

Startup checks ports, waits for PostgreSQL health, applies Alembic migrations, starts FastAPI and Vite in the background, and waits for HTTP readiness. Both apps bind to `127.0.0.1`. Backend defaults to `.env`'s `APP_PORT` (8000); frontend defaults to 5173. The frontend proxy receives the actual selected backend address.

For occupied ports:

```bash
make start BACKEND_PORT=8007 FRONTEND_PORT=5177
make restart BACKEND_PORT=8007 FRONTEND_PORT=5177
```

Use the same overrides when restarting. Stop/status/log commands read the saved process state and need no port arguments. To change ports for already managed apps, run `make stop-apps` first, then start with the new ports. An occupied unmanaged port causes a clear error before startup; no process is killed to free it.

## Commands

| Command | Effect |
|---|---|
| `make help` | List commands |
| `make setup` | Install dependencies; create `.env` only if missing |
| `make start` | Start database, migrate, and start apps; running managed apps are reused |
| `make status` | Show managed process readiness/URLs and database status |
| `make stop` | Stop managed app process groups and PostgreSQL; retain the data volume |
| `make stop-apps` | Stop managed apps and leave PostgreSQL running |
| `make restart` | Stop the stack, then start it |
| `make logs` | Show recent backend/frontend logs |
| `make logs SERVICE=backend` | Show only backend logs; `frontend` is also supported |
| `make logs-follow` | Follow app logs; Ctrl+C exits the viewer |
| `make db-start` / `make db-stop` | Start/stop just PostgreSQL |
| `make db-logs` | Follow PostgreSQL logs |
| `make migrate` | Apply migrations against the configured database |
| `make test` | Run isolated backend, frontend, and service-control safety checks |
| `make test-postgres` | Run real PostgreSQL tests in a disposable database |
| `make lint` / `make format` | Check/apply Python formatting; lint also checks frontend |
| `make build` | Type-check/build frontend |
| `make rag-check` | Run the 12-case live Gemini acceptance dataset; API charges may apply |

The app log files and process state live in ignored `.run/`. Process records include PID, Linux process start time, and port; these prevent stale PID records from stopping unrelated services. Stop targets only process groups started by this controller. Manually launched servers remain your responsibility. Stopping keeps conversations, audit history, incidents, and knowledge vectors in the database volume. There is deliberately no data-reset/delete-volume command.

The controller never executes `.env` as shell code. Compose receives only the parsed PostgreSQL settings, so application passwords containing `$` do not trigger Compose variable interpolation. Existing shell environment variables retain their normal precedence over `.env` database settings.

If startup fails, inspect `make logs`. Any app processes newly launched by that failed invocation are stopped; previously managed apps are preserved. The database may remain running for inspection. The controller is for local development, not a production process supervisor.
