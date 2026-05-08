#!/bin/bash
set -e
echo "Running database migrations..."

# If schema already exists but alembic_version is untracked (e.g. persisted volume
# after a fresh container), stamp to head so migrations don't re-run from scratch.
python - <<'EOF'
import os
import sqlalchemy as sa

engine = sa.create_engine(os.environ["DATABASE_URL"])
insp = sa.inspect(engine)
schema_exists = insp.has_table("events")
version_tracked = insp.has_table("alembic_version") and bool(
    engine.connect().execute(sa.text("SELECT 1 FROM alembic_version LIMIT 1")).fetchone()
)
if schema_exists and not version_tracked:
    import subprocess
    print("Existing schema detected with no alembic_version — stamping head")
    subprocess.run(["alembic", "stamp", "head"], check=True)
EOF

alembic upgrade head
echo "Starting server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
