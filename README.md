### ECOS — Entersoft Document Fix Tool

ECOS is a small, local FastAPI web app that helps support teams search for Entersoft documents and apply a targeted fix in the database using prepared SQL scripts.

This tool is intended for Dedicated Server installations of Entersoft only. It runs locally on a machine that has direct network access to the SQL Server (on-prem/LAN or via VPN). It is not designed for multi-tenant SaaS or public internet exposure.

---

#### Key features

- Search documents and view key metadata (read-only)
- Validate whether a record can be safely fixed
- Apply the fix using curated SQL (`SQL/set.sql`) when conditions are met
- Uses your SQL Server credentials from a local `.env` file

---

### Prerequisites

- Python 3.10+
- Microsoft ODBC Driver 17 for SQL Server (required by `pyodbc`)
  - macOS: follow Microsoft docs to install ODBC 17 (Homebrew can be used for unixODBC)
  - Windows: install the official ODBC 17 package
- Network reachability to the SQL Server (LAN or VPN)

Optional (macOS only): If you wish to use the automatic VPN dialer, the code expects a macOS network service named `VPN`. See “Optional: auto‑VPN (macOS)” below.

---

### Installation

1) Clone the repository

```
git clone https://github.com/<your-org-or-user>/ECOS.git
cd ECOS
```

2) Create and activate a virtual environment

```
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

3) Install dependencies

There is no `requirements.txt` in the repo. Install the essentials directly:

```
pip install fastapi uvicorn[standard] sqlalchemy pyodbc python-dotenv jinja2 pandas
```

Notes:
- `pandas` is optional but some formatting utilities handle Pandas types gracefully.
- `uvicorn[standard]` brings useful extras for local development.

---

### Configure environment (.env)

Create a `.env` file in the project root with your SQL Server connection details. Do not commit real credentials to Git!

Example `.env` (placeholders):

```
SQL_SERVER=192.168.1.10       # SQL Server host or IP
UID=sa                        # SQL login
SQL_PWD=yourStrong(!)Passw0rd # SQL password
DATABASE=ENTER_SOFT_DB        # Target database name
TSC=yes                       # TrustServerCertificate (yes/no or true/false)
SQL_COMPANY_CODE=002          # Company code used by your procedures

# Optional: used only for macOS auto‑VPN (see below)
IP_EM=10.0.0.20               # A host inside the remote site (ping check)
IP_EM_ROUTER=10.0.0.1         # VPN router/gateway IP (ping check)
```

Environment variable usage:
- `SQL/sql_connect.py` reads the variables to build an ODBC connection string via SQLAlchemy + `pyodbc`.
- `TSC` controls `TrustServerCertificate` in the ODBC string.
- `IP_EM` and `IP_EM_ROUTER` are only used on macOS for optional, automatic VPN handling.

Security reminder:
- Keep `.env` local and private; add it to `.gitignore`.
- Rotate any credentials that may have been committed by accident in the past.

---

### Run locally

Start the FastAPI app with Uvicorn:

```
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Open your browser at http://localhost:8000

You should see the search page. Enter a document code to inspect. If the tool determines the record can be fixed, a “Fix” action will be available and will execute the SQL contained in `SQL/set.sql`.

---

### How it works (high level)

- Web layer: `FastAPI` + Jinja2 templates (`templates/index.html`, `templates/base.html`).
- SQL access: `SQL/sql_connect.py` builds an ODBC connection using values from `.env`.
- Business flow:
  - `SQL/check.sql` is used to validate and display the current state.
  - `SQL/set.sql` is used to apply the corrective update.
  - `SQL/auto.sql` helps fetch recent document candidates for convenience.

The app is intentionally minimal and executes only known, controlled SQL scripts from the `SQL/` folder.

---

### Scope and limitations

- Dedicated server installations only. The tool assumes you control the database and network.
- Local use. Run the tool on a trusted machine within the office LAN or over a secure VPN. Do not expose it to the public internet.
- SQL Server only (via ODBC 17). Other RDBMS engines are not supported.

---

### Optional: auto‑VPN (macOS)

If direct DB connection fails and `IP_EM` is set, the app (on macOS) will try to:

1) Ping `IP_EM`. If reachable, it will attempt to “connect” a macOS network service named `VPN` via AppleScript.
2) After a short wait, it pings `IP_EM_ROUTER`. If reachable, it retries the DB connection.

To use this:
- Ensure you have a macOS network service named exactly `VPN` in System Settings > Network.
- Provide `IP_EM` and `IP_EM_ROUTER` in `.env` as explained above.

If you do not need this feature, simply leave those variables unset; the app will attempt a normal connection only.

---

### Troubleshooting

- ODBC driver errors (e.g., “Data source name not found”):
  - Verify Microsoft ODBC Driver 17 for SQL Server is installed and discoverable by `pyodbc`.
  - On macOS, ensure `unixODBC` is installed and driver paths are correct.

- Authentication/SSL issues:
  - Check `UID` / `SQL_PWD` / `DATABASE` in `.env`.
  - Try setting `TSC=yes` to bypass certificate validation only if you trust the network.

- Cannot reach SQL Server:
  - Confirm you’re on the same LAN or connected via VPN.
  - Ping the server in `SQL_SERVER` from the machine running the app.

- Fix button disabled:
  - The validation logic determined the record cannot be safely fixed. Re-check the input or review business rules in `main.py`.

---

### Development notes

- Entry point: `main.py` (FastAPI app)
- Templates: `templates/`
- Static assets: `static/` and `images/`
- SQL scripts: `SQL/`

You can change SQL behavior by editing the scripts in `SQL/` (review carefully before applying changes in production).

---

### License / Copyright

Unless stated otherwise in source headers, this project’s source files are:

© Ioannis E. Kommas 2024 — All Rights Reserved.

If you need a different license for distribution, please contact the author/owner.
