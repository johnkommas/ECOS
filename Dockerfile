# ECOS Dockerfile
# - Python slim base
# - Installs Microsoft ODBC Driver 17 for SQL Server (msodbcsql17)
# - Installs unixODBC for pyodbc runtime (and -dev for builds when needed)
# - Runs FastAPI app with Uvicorn on port 8000

FROM python:3.11-slim-bullseye

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System dependencies and Microsoft ODBC Driver 17 for SQL Server
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       curl gnupg2 apt-transport-https ca-certificates \
       unixodbc unixodbc-dev build-essential \
    && curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - \
    && curl https://packages.microsoft.com/config/debian/11/prod.list > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql17 \
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
