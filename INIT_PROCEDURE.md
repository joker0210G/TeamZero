# TeamZero Init Procedure

## The contract (what an agent does)

An AI coding agent (Claude Code, Cursor, Antigravity, …) only needs one step:

> **"Init TeamZero in this project"** → the agent runs:

```bash
python -m teamzero init .
```

Everything else is computed deterministically. The agent never hand-crafts `.teamzero/` files.

## What `init` does (deterministic, idempotent)

1. **Refuses to clobber** an existing `.teamzero/` (exit 2) unless `--force`, which first moves it to `.teamzero.backup.<timestamp>`.
2. **Detects the project profile** (`--profile auto`): `pyproject.toml`/`setup.py` → `python`; `package.json` → `node`; `Cargo.toml` → `rust`; `go.mod` → `go`; otherwise `generic`. Override with `--profile`.
3. **Scaffolds the governance tree**: `memory/{adr,map,specs,traps}`, `redteam/{campaigns,findings}`, `inbox/{asks,decisions}`, `ledger`.
4. **Generates `constitution.yaml`** templated with the org name and profile-specific deterministic gates (pytest / npm test / cargo test / go test + secret scan + dependency probation).
5. **Writes ADR-000 (genesis)** — the anchor record every later ADR cites.
6. **Mints the genesis receipt**: creates `.teamzero/.mintkey` (gitignored, 0600 on POSIX) and appends an HMAC-SHA256-signed `genesis` event to `ledger/receipts.jsonl`. Founding is *verified*, not asserted — INV-03 applies to the org itself.
7. **Wires MCP clients**: merges a `teamzero` server block into `claude_mcp.json`, `.mcp.json`, `.cursor/mcp.json`, `antigravity_mcp.json`, each with `env.TZ_ROOT` pointing at the governed project.
8. **Updates `.gitignore`** so `.mintkey` is never committed.

## What `doctor` checks

```bash
python -m teamzero doctor .
```

- `.teamzero/` tree complete, ledgers are valid JSONL
- A mint authority exists (`.mintkey` or `TZ_SERVER_SECRET`)
- Latest receipt HMAC verifies against the local key (detects key rotation / ledger tampering)
- `.gitignore` covers `.mintkey`

## Required refactor in this repo (one-time)

1. **Path resolution** — honor `TZ_ROOT` (with `TZ_PROJECT_DIR` support), fall back to the package repo.
2. **Package the server** — moved `mcp_server.py` into the package as `teamzero/mcp_server.py` and added `teamzero/__main__.py`.
3. **Console scripts** in `pyproject.toml`:
   ```toml
   [project.scripts]
   tz = "teamzero.cli:main"
   teamzero = "teamzero.cli:main"
   ```
4. **Publish** (`pip install teamzero`) — then any agent in any project can run `teamzero init` with zero setup.

## Install from source (until published)

```bash
pip install -e /path/to/TeamZero
python -m teamzero init /path/to/your-project
```

## Post-init checklist for the founder

1. Review `.teamzero/constitution.yaml` gate commands against your real test setup.
2. Commit `.teamzero/` (`.mintkey` is gitignored).
3. Set `TZ_SERVER_SECRET` in CI so CI becomes the exclusive mint authority (per the constitution's `threat_model_boundary`).
4. Tell your agent: *read `.teamzero/constitution.yaml` before writing code.*
