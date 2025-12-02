# ECOS Dockerfile
# - Python slim base
# - Installs Microsoft ODBC Driver 18 for SQL Server (msodbcsql18)
# - Installs unixODBC for pyodbc runtime (and -dev for builds when needed)
# - Runs FastAPI app with Uvicorn on port 8000

FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System dependencies and Microsoft ODBC Driver 18 for SQL Server
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       curl gnupg ca-certificates apt-transport-https \
       unixodbc unixodbc-dev build-essential \
    && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/microsoft.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18 \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY . /app

# Install Python dependencies
# (Project intentionally has no requirements.txt; install the known essentials)
RUN pip install --upgrade pip \
    && pip install \
       fastapi \
       "uvicorn[standard]" \
       sqlalchemy \
        pyodbc \
       python-dotenv \
       jinja2 \
       pandas

EXPOSE 8000

# Default command: run the API
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
