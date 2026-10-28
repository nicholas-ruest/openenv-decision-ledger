FROM ghcr.io/nicholas-ruest/openenv-decision-ledger@sha256:9455e57ef88fe99d94a0f0b32651c1f52472f9aba6da68c11a68db18c936ed22
LABEL org.opencontainers.image.source="https://github.com/nicholas-ruest/openenv-decision-ledger"
LABEL org.opencontainers.image.description="Experimental two-response software public-feedback candidate; unapproved"
COPY research/software-revision-candidate-20261028/revision_environment.py /app/revision_environment.py
COPY research/software-revision-candidate-20261028/revision_app.py /app/revision_app.py
COPY research/software-public-check-20261028/public_check.py /app/public_check.py
CMD ["python","-m","uvicorn","revision_app:app","--host","0.0.0.0","--port","8000","--workers","1"]
