FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY sre_engine ./sre_engine
COPY edge_agent ./edge_agent
COPY scripts ./scripts

EXPOSE 8000

CMD ["uvicorn", "sre_engine.server:app", "--host", "0.0.0.0", "--port", "8000"]