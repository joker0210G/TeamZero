# Disaster Recovery Runbook

## 1. Context Poisoning or Corrupted ADRs
- If an agent or untrusted client attempts to inject prompt overrides into memory:
  1. Inspect red-team findings: `python -m teamzero.cli health`.
  2. The hash-chained receipts ledger (`.teamzero/ledger/receipts.jsonl`) verifies genesis integrity.
  3. Revert corrupted `.teamzero/memory/` files using `git checkout origin/main -- .teamzero/memory/`.

## 2. Compromised Mint Authority
- Rotate the local key: delete `.teamzero/.mintkey` and set a new `TZ_SERVER_SECRET` environment variable.
- Re-run `python -m teamzero.init_project doctor` to verify ledger HMAC chain.
