"""Prepare attributed media-only Docker context from a frozen public checkout."""
import argparse
import hashlib
import shutil
from pathlib import Path

PIN = '958198e55299eb18ad812f438a6b2ca6abaa7f5c'


def prepare(source, adapter, output):
    if output.exists():
        raise ValueError('fresh context required')
    if not (source/'LICENSE').read_text().startswith('MIT License'):
        raise ValueError('upstream license missing')
    shutil.copytree(source, output)
    for name in ('media_app.py', 'server_controls.py', 'tcp_controls.py'):
        shutil.copy2(adapter/name, output/name)
    ignore = output / '.dockerignore'
    ignore.write_text(ignore.read_text() + '\n!tests\n!tests/**\n!scripts\n!scripts/**\n')
    docker = (source/'Dockerfile.terminal').read_text()
    docker += '\nCOPY tests /app/tests\nCOPY scripts /app/scripts\nCOPY LICENSE /app/UPSTREAM_LICENSE\nCOPY media_app.py server_controls.py tcp_controls.py /app/\n'
    docker += 'RUN pip install --no-cache-dir pytest==9.0.3\n'
    docker += 'LABEL org.opencontainers.image.source="https://github.com/nicholas-ruest/openenv-decision-ledger"\n'
    docker += f'LABEL org.opencontainers.image.base.source="https://github.com/proffesor-for-testing/openenv-qe-arena/tree/{PIN}"\n'
    docker += 'CMD ["python", "-m", "uvicorn", "media_app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]\n'
    (output/'Dockerfile.media').write_text(docker)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    prepare(a.source, Path(__file__).resolve().parent, a.output)
