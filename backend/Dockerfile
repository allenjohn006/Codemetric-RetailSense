FROM python:3.11-slim

WORKDIR /app

# Install only the minimal build tools actually needed.
# psycopg2-binary bundles libpq so libpq-dev is NOT required.
# gcc + libffi-dev are needed for some Python packages (cryptography, prophet).
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
