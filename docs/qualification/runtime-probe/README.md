# BE-000-03 - Reproducible runtime compatibility probe (M0)

**Purpose:** test the *candidate* Python/FastAPI/Pydantic/SQLAlchemy/Alembic/psycopg stack independently of the FPS business application. All code here is a qualification fixture. It is **not** M1 bootstrap and cannot substitute for application CI or migrations.

## Status on 2026-11-25

- Python 3.13.5 and uv 0.10.0 were observed.
- A separate local exploratory smoke using older installed libraries passed 4 tests.
- Candidate `uv lock` failed to reach PyPI and emitted **no** valid lockfile. No candidate `uv sync`, Docker build or PostgreSQL integration passed.
- GitHub files in this directory provide a reproducible procedure to complete those checks later, **not proof that they were executed against the target stack**.
- See `../BE-000-03_RUNTIME_COMPATIBILITY_EVIDENCE.md` and `../M0_GATE_REPORT.md`. **The earlier NO-GO has been superseded by a qualified GO for M1**, supported by Actions run 45530002637 and PR #16.

## Target versions

`pyproject.toml` declares the candidate ranges from the previously accepted ADR-0002 and runtime-compatibility contract. The solver must generate a reproducible lockfile using actual index access before any version can become an approved pin.

## Steps (network-enabled isolated Codespaces / CI, no production credentials)

```bash
cd docs/qualification/runtime-probe
python3 --version
uv --version
uv lock --python 3.13
uv sync --frozen
uv run --frozen pytest -q test_runtime_probe.py
```

The last command runs four exploratory smoke tests and skips strict checks unless explicitly enabled. **Four green smoke tests alone are never a Gate M0 PASS.**

Prepare a disposable PostgreSQL 17 test database, then run strict validation. On a Docker-capable local/CI environment a temporary database can be started using the published PostgreSQL 17 image **after digest verification** and test-only password; this is not permission to provision a billable external service. Avoid passing secrets through shell history or logs.

```bash
# Example only, set the URL as a secret in CI for an isolated test database:
export FPS_COMPAT_STRICT=1
export FPS_COMPAT_DATABASE_URL='postgresql+psycopg://test_user:REDACTED@localhost:5432/test_db'
uv run --frozen pytest -q test_runtime_probe.py
```

The strict checks:
1. Assert FastAPI >=0.165.0, Pydantic >=2.14, SQLAlchemy >=2.1, Alembic >=1.17, psycopg >=3.2, pytest >=8, HTTPX >=0.28 from *installed* dist versions.
2. Import psycopg3.
3. Connect using SQLAlchemy's explicit `postgresql+psycopg://` dialect to a real PostgreSQL 17+ sandbox.
4. Exercise commit and rollback on disposable temporary tables.

If no test database is supplied, **strict mode fails**, rather than reporting a skipped database test as success. Production or real Contact data must **never** be used.

**Further mandatory release-gate checks**, not covered by this fixture: actual Docker image build from pinned digest and locked dependencies, Alembic migration upgrade/downgrade, TLS/pooled connection to deployment-target PostgreSQL, session cleanup and concurrent access, basic FastAPI Uvicorn process. These require explicit evidence (exit code, stdout, SHA, test environment) before M0 can be changed to GO.

## Evidence recording

For a later run, collect in `docs/qualification/BE-000-03_RUNTIME_COMPATIBILITY_EVIDENCE.md` (new revision): UTC time, Git SHA, `pyproject.toml` digest, `uv.lock` Git SHA, `uv --version`, Python version, `uv sync` result, `pytest` summary, DB server version, Docker image digest, Docker build result, reviewer and CI run URL. Do **not** paste connection strings, private tokens, or customer data.

**No GitHub Actions workflow is included in this M0 PR:** private-repository runner minutes can be billable and there is no prior approval to incur such use. The prepared probe can be executed in a user-authorized network-capable environment.


## Outcome: verified GitHub Actions (2026-11-25)

- PR #16 merged: https://github.com/tawounfouet/fastapi-fps-platform/pull/16
- Final successful run: https://github.com/tawounfouet/fastapi-fps-platform/actions/runs/45530002637
- `uv.lock`: 33 packages, SHA-256 `b40d1d95eb0bc196154ba78194cf90c8077793acd5770987521900e1cc818d07`, checked and installed under Python 3.13.18.
- Six host strict tests and six Docker strict tests passed against PostgreSQL 17.12; exact image base digest is in `Dockerfile`.
- The current `docs/qualification/M0_GATE_REPORT.md` gives **GO for beginning M1 only**. The above original network-failure notes remain as the record of earlier attempts. This probe is not the root application, and it does not certify app-level Alembic migrations or production hosting.
