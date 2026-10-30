FROM ghcr.io/nicholas-ruest/openenv-decision-ledger@sha256:9455e57ef88fe99d94a0f0b32651c1f52472f9aba6da68c11a68db18c936ed22
LABEL org.opencontainers.image.source="https://github.com/nicholas-ruest/openenv-decision-ledger"
LABEL org.opencontainers.image.description="Separate unapproved public-review candidate with explicit empty-action finish"
COPY integrations/software-repair/repair_env/*.py /app/repair_env/
COPY research/software-public-check-20261028/public_check.py /app/research/software-public-check-20261028/public_check.py
COPY ["research/software-portable-review-default-20261030/portable_environment.py", "research/software-portable-review-default-20261030/portable_app.py", "research/software-portable-review-default-20261030/review_environment.py", "research/software-portable-review-default-20261030/mandatory_environment.py", "research/software-portable-review-default-20261030/joint_revision_environment.py", "research/software-portable-review-default-20261030/field_feedback.py", "/app/research/software-portable-review-default-20261030/"]
ENV PYTHONPATH="/app/research/software-portable-review-default-20261030:/app"
CMD ["python","-m","uvicorn","portable_app:app","--host","0.0.0.0","--port","8000","--workers","1"]
