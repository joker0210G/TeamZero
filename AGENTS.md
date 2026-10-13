# Git Operating Invariants & Safety Guardrails

These rules govern all Git and GitHub command execution in this workspace.

## Tier 1: Forbidden Operations (Never run unless explicitly commanded in current prompt)
- `git push --force` or `--force-with-lease` to `main`, `master`, `develop`, or any shared branch.
- `git reset --hard`, `git clean -fd`/`-fdx`, `git checkout .`, `git restore .` on a tree containing uncommitted work you did not author.
- `git commit --no-verify` or any bypass of hooks, linters, or quality gates.
- Committing `.env`, secrets, API keys, tokens, certificates, credentials, or large binary files (>50MB).
- Altering `git config` (global or repository level), remotes, or credentials.
- Deleting remote branches, tags, or releases.
- Rewriting already-pushed history (`rebase`, `commit --amend`, `filter-repo`).
- Autonomous merging of pull requests.

## Tier 2: Require Explicit User Approval (Stop, show command, wait for confirmation)
- Any `git push`.
- Creating a Pull Request, issue, release, or tag on GitHub.
- Installing new dependencies or modifying CI/CD workflows (`.github/workflows/*`).
- Any operation touching files outside the scope of current session task.
- Resolving merge conflicts where intent between branches is ambiguous.

## Tier 3: Pre-Approved Actions (Permitted autonomously)
- Read-only inspection: `git status`, `git diff`, `git log`, `git show`, `git blame`, `git branch`, `git remote -v`, `git reflog`.
- Creating a local feature branch, staging specific paths, committing to feature branch.
- Running test suites, linters, and verification checks.
- Stashing work authored by the agent during the current turn (with explicit mention).

## Commit Standards
1. Always inspect before staging: `git status` and `git diff`.
2. Stage specific file paths (`git add <file>`) or hunk-by-hunk (`git add -p`). Avoid `git add .` or `git add -A`.
3. Verify staged changes: `git diff --staged`.
4. Follow Conventional Commits: `<type>(<scope>): <summary>` (imperative mood, <= 50 chars).
5. Explain motivation in commit body when non-trivial.

## TeamZero MCP Operating Guidelines

When the TeamZero MCP Server is active, adhere to the following execution sequence:
1. **Zero Raw Dumps:** Call `teamzero_inspect_outline` or `teamzero_read_symbol` instead of dumping whole source files.
2. **Fact-Check Before Commit:** Call `teamzero_cove_verify` or `teamzero_ensemble_verify` to audit code against hallucinations.
3. **Verify via Gauntlet:** Execute `teamzero_run_gauntlet` or `teamzero_run_dynamic_gauntlet` to compute completion mathematically before requesting review.
4. **Tool Discovery:** If unsure which tool to invoke, run `teamzero_search_tools(query)`.

## Working on TeamZero Itself (The Self-Hosting Rule)

When you are asked to improve or modify TeamZero itself:
- **You are the Builder (The Worker).**
- **The codebase files in `teamzero/` and `tests/` are the Target (The Product).**
- **The governance files (`.teamzero/constitution.yaml`, `.github/workflows/`, and `TZ_SERVER_SECRET`) are the immutable Host Rules.** You must NEVER attempt to relax or bypass them to make a test pass.
- Every self-improvement must pass the complete gauntlet (`pytest tests/ -q`), dynamic probes, and red-team checks before you present it to the user.
