### ECOS — Docker usage

This document shows how to run ECOS (FastAPI app) in Docker. The image includes Microsoft ODBC Driver 17 for SQL Server (`msodbcsql17`) so `pyodbc` can connect to your SQL Server.

Important:
- Provide your database settings via a local `.env` file (do not bake secrets into the image).
- The optional macOS auto‑VPN logic in `SQL/sql_connect.py` does not work inside Linux containers. If you rely on VPN, connect the host to VPN first so the container can route to SQL Server via the host network stack.

---

### Files provided

- `Dockerfile` — Builds a production image on `python:3.11-slim-bullseye`, installs `msodbcsql17` and app dependencies, runs Uvicorn on port 8000.
- `docker-compose.yml` — One‑service stack mapping port `8000:8000`, loading env from `.env`, with a basic healthcheck.
- `.dockerignore` — Excludes `.env`, VCS, caches, etc., from the image context.

---

### 0) Prepare `.env`

Create `.env` at the project root (do not commit real credentials):

```
SQL_SERVER=192.168.1.10
UID=sa
SQL_PWD=yourStrong(!)Passw0rd
DATABASE=ENTER_SOFT_DB
TSC=yes
SQL_COMPANY_CODE=002
```

Note: The container must be able to reach `SQL_SERVER` over the network (LAN/VPN). The macOS auto‑VPN helper is not available inside the container.

---

### 1) Quick start with Docker Compose (recommended)

Build and start in the background:

```
docker compose build
docker compose up -d
```

Open: http://localhost:8000

Tail logs:

```
docker compose logs -f
```

Stop the service:

```
docker compose down
```

Remove containers + anonymous volumes (clean run):

```
docker compose down -v
```

---

### 2) One‑off Docker CLI (without Compose)

Build the image:

```
docker build -t ecos:latest .
```

Run the container, mapping port and injecting env vars from `.env`:

```
docker run --rm \
  --name ecos \
  -p 8000:8000 \
  --env-file .env \
  ecos:latest
```

Then visit http://localhost:8000

Stop it (if running detached):

```
docker stop ecos
```

---

### 3) Development mode (live reload)

The compose file includes commented lines to mount the source and enable `--reload`:

```
services:
  ecos:
    # ...
    # volumes:
    #   - ./:/app
    # command: ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

Uncomment those lines and run:

```
docker compose up --build
```

This will reflect code changes without rebuilding the image.

---

### 4) Health and diagnostics

- Healthcheck: `docker inspect --format='{{json .State.Health}}' ecos` (when using compose name) or `docker ps` to see `(healthy)` status.
- Check app is up: `curl -i http://localhost:8000/` should return HTTP 200.
- Logs: `docker compose logs -f` or `docker logs -f ecos`.

---

### 5) Troubleshooting

- pyodbc / ODBC driver errors in container:
  - The image installs `msodbcsql17` and `unixodbc`. If you still see driver errors, rebuild the image: `docker compose build --no-cache`.
  - Ensure your SQL Server is reachable from the container network: `docker exec -it ecos ping -c 1 <SQL_SERVER>` (Linux-based images support `ping` only if `iputils-ping` exists; otherwise use `nc -vz <SQL_SERVER> 1433`).

- Cannot connect over VPN:
  - The auto‑VPN macOS helper is not available inside the container. Connect VPN on the host first. Once the host can reach the DB, the container should too.

- Port already in use:
  - Change the published port: in compose, update `ports: - "8080:8000"` and visit http://localhost:8080

---

### 6) Security notes

- Keep `.env` out of the image; it is excluded via `.dockerignore`.
- Use `env_file: .env` (compose) or `--env-file .env` (CLI) to inject secrets at runtime.
- Rotate any credentials that may have been exposed previously.
