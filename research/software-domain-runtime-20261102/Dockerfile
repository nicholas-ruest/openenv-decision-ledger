FROM ghcr.io/nicholas-ruest/openenv-decision-ledger@sha256:9455e57ef88fe99d94a0f0b32651c1f52472f9aba6da68c11a68db18c936ed22
LABEL org.opencontainers.image.source="https://github.com/nicholas-ruest/openenv-decision-ledger"
LABEL org.opencontainers.image.description="Unapproved two-response software final-domain reminder candidate"
# Include the actual interpreter/task source used by this candidate's controls.
COPY integrations/software-repair/repair_env /app/repair_env
COPY research/software-final-domain-cue-20261101/revision_environment.py /app/research/software-final-domain-cue-20261101/revision_environment.py
COPY research/software-entry-order-review-20261101/revision_environment.py /app/research/software-entry-order-review-20261101/revision_environment.py
COPY research/software-entry-order-review-20261101/order_diagnostic.py /app/research/software-entry-order-review-20261101/order_diagnostic.py
COPY research/software-domain-runtime-20261102/runtime_environment.py /app/research/software-domain-runtime-20261102/runtime_environment.py
COPY research/software-domain-runtime-20261102/runtime_app.py /app/runtime_app.py
ENV PYTHONPATH=/app/research/software-domain-runtime-20261102:/app
CMD ["python","-m","uvicorn","runtime_app:app","--host","0.0.0.0","--port","8000","--workers","1"]
