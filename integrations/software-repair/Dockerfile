FROM python:3.12-slim@sha256:2b4f19dae3a777dfc3b76730bda1e82e1f66ab2a2686fa93ca78edbfb4f04ffe
LABEL org.opencontainers.image.source="https://github.com/nicholas-ruest/openenv-decision-ledger"
LABEL org.opencontainers.image.description="Decision Ledger software edit/test candidate; no host code execution"
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates tini && rm -rf /var/lib/apt/lists/*
COPY integrations/openenv-arena/requirements.lock /app/requirements.lock
RUN pip install --no-cache-dir -r /app/requirements.lock && useradd --uid 10001 --create-home arena
COPY integrations/software-repair/repair_env /app/repair_env
COPY integrations/software-repair/openenv.yaml /app/openenv.yaml
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 ENABLE_WEB_INTERFACE=false
USER 10001
EXPOSE 8000
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python", "-m", "uvicorn", "repair_env.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
