---
name: git-github
description: Use this skill for anything involving Git or GitHub - committing, branching, merging, rebasing, resolving conflicts, undoing mistakes or recovering lost commits, writing commit messages, opening and reviewing pull requests, configuring branch protection or CODEOWNERS, GitHub Actions CI/CD, handling leaked secrets, releases and tagging, forks and open-source contribution, and using the GitHub CLI (gh). Also use it when the user asks to "push", "commit", "open a PR", "fix my git history", "set up a repo", or "work with a team on GitHub".
---

# Git and GitHub: Complete Working Skill

This skill tells you how to use Git and GitHub safely and effectively, solo or in a team. It covers daily workflow, history hygiene, recovery, collaboration, repository governance, CI/CD, security, releases, and the GitHub CLI.

Read sections 1 and 2 every time. Jump to the other sections as the task needs.

---

## 1. Prime directives

1. **Inspect before you act.** Run `git status`, `git branch --show-current`, and `git diff` (or `git diff --staged`) before any commit, merge, rebase, reset, or push. Know which branch you are on and what is staged.
2. **Never commit directly to `main`/`master`.** Work on a short-lived branch and merge through a Pull Request.
3. **Small, atomic commits.** One logical change per commit, with a message that says what changed and why.
4. **Sync early and often.** Bring `main` into your branch regularly so conflicts stay small.
5. **Never rewrite shared history.** Rebase, amend, and force-push only on branches that nobody else has based work on.
6. **Prefer reversible operations.** `git revert` for published history, `git restore`/`git switch` over `checkout`, `--force-with-lease` over `--force`, create a backup branch before risky surgery.
7. **Secrets never enter a repository.** If one does, rotate it first, clean history second.
8. **Let machines do the tedious checks.** Branch protection, CI, linters, pre-commit hooks, and Dependabot exist so humans do not have to catch everything.
9. **"Lost" usually means "unreferenced".** Before panicking, run `git reflog`.

---

## 2. Operating rules when an AI agent runs Git commands

These rules apply whenever you (the agent) execute Git or `gh` commands on the user's behalf.

### Tier 1: Never, unless the user explicitly requests it in this conversation

- `git push --force` or `--force-with-lease` to `main`/`master`/`develop` or any shared branch.
- `git reset --hard`, `git clean -fd`/`-fdx`, `git checkout .`, `git restore .` on a tree with uncommitted work you did not create.
- `git commit --no-verify` or any bypass of hooks and quality gates.
- Committing `.env`, keys, tokens, certificates, credentials, or large build artifacts.
- Changing `git config` (global or local), remotes, or credentials.
- Deleting remote branches, tags, or releases.
- Rewriting already-pushed history (`rebase`, `commit --amend`, `filter-repo`).
- Merging a PR on the user's behalf.

### Tier 2: Ask first (stop, describe the exact command, wait for approval)

- Any `git push` (the user may not want the work published yet).
- Creating a PR, issue, release, or tag on GitHub.
- Installing dependencies or modifying CI/deploy configuration.
- Any operation that touches more than the files you changed in this session.
- Resolving a merge conflict where the intent of both sides is unclear.

### Tier 3: Fine without asking

- `git status`, `git diff`, `git log`, `git show`, `git blame`, `git branch`, `git remote -v`, `git reflog`.
- Creating a local feature branch, staging specific files, committing to a feature branch.
- Running tests and linters.
- `git stash` only when you created the changes being stashed, and say so.

### Agent checklist for every commit

1. `git status` and `git diff` to see exactly what changed.
2. Stage **specific paths** (`git add path/to/file`), or `git add -p` for partial staging. Avoid `git add -A` / `git add .` when other work may be in the tree.
3. `git diff --staged` and verify nothing sensitive or unrelated is included.
4. Commit non-interactively with a Conventional Commit message: `git commit -m "type(scope): summary" -m "Why this change was made."`
5. `git show --stat --oneline HEAD` to confirm the result.
6. Only push if asked. Preferred first push: `git push -u origin HEAD`. After that, `git pull --rebase` before `git push` if the remote moved.

### Amend policy

Use `git commit --amend` only if the commit is the most recent one **and has not been pushed**. If amending would require a force-push, make a new commit (or `git commit --fixup`) instead.

### Detached HEAD / worktree safety

- If Git refuses to switch because a branch is checked out in another worktree, do not force it. Use a different branch name or ask.
- If you land in detached HEAD, create a branch before doing anything else: `git switch -c rescue/<name>`.

---

## 3. Mental model

| Area | What it is | Commands that move data |
|---|---|---|
| Working directory | Files on disk | edit files, `git restore` |
| Staging area (index) | Snapshot you are preparing for the next commit | `git add`, `git restore --staged` |
| Local repository | Commit history in `.git` | `git commit`, `git reset`, `git rebase` |
| Remote (`origin`, `upstream`) | Copy on GitHub | `git fetch`, `git pull`, `git push` |

Key facts:

- A **commit** is an immutable snapshot with a parent pointer. Branches and tags are just movable (branch) or fixed (tag) labels pointing at commits.
- `HEAD` points at the commit/branch you are on.
- `origin/main` is your local, last-known copy of the remote branch. It only updates on `git fetch`/`pull`.
- `git pull` = `git fetch` + (`merge` or `rebase`).
- Git keeps old objects around for a while after you "lose" them. That is why `reflog` can save you.

---

## 4. One-time setup

### Identity

```bash
git config --global user.name  "Your Name"
git config --global user.email "you@example.com"
```

Use the email attached to your GitHub account (or GitHub's `noreply` address) so commits link to your profile.

### Recommended global configuration

```bash
git config --global init.defaultBranch main

# Pull / rebase behavior
git config --global pull.rebase true            # or: pull.ff only (never create surprise merge commits)
git config --global rebase.autoStash true
git config --global rebase.autoSquash true      # auto-apply fixup!/squash! commits
git config --global rebase.updateRefs true      # move stacked branches during rebase

# Push / fetch
git config --global push.autoSetupRemote true   # first `git push` sets upstream automatically
git config --global push.followTags true
git config --global fetch.prune true            # drop deleted remote branches locally
git config --global fetch.pruneTags true

# Better diffs and conflicts
git config --global diff.algorithm histogram
git config --global diff.colorMoved plain
git config --global diff.renames true
git config --global merge.conflictStyle zdiff3  # shows the common ancestor inside conflict markers

# Remember conflict resolutions
git config --global rerere.enabled true

# Nicer listings
git config --global branch.sort -committerdate
git config --global tag.sort version:refname
git config --global column.ui auto

# Show the diff while writing commit messages
git config --global commit.verbose true

# Catch corrupted objects early
git config --global transfer.fsckObjects true

# Typo help
git config --global help.autocorrect prompt
```

Choose one of `pull.rebase true` (linear history, rewrites your local unpushed commits on pull) or `pull.ff only` (refuse non-fast-forward pulls so you decide explicitly). Either beats the default of silently creating merge commits.

### Useful aliases

```bash
git config --global alias.st  "status -sb"
git config --global alias.co  "switch"
git config --global alias.br  "branch -vv"
git config --global alias.lg  "log --graph --oneline --decorate --all"
git config --global alias.last "log -1 --stat"
git config --global alias.unstage "restore --staged"
git config --global alias.pfwl "push --force-with-lease"
git config --global alias.undo "reset --soft HEAD~1"
```

### Authenticate to GitHub

**Option A: SSH (recommended for daily use)**

```bash
ssh-keygen -t ed25519 -C "you@example.com"
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519
cat ~/.ssh/id_ed25519.pub          # paste into GitHub > Settings > SSH and GPG keys
ssh -T git@github.com              # test
```

**Option B: HTTPS with GitHub CLI credential helper**

```bash
gh auth login                      # choose GitHub.com, HTTPS or SSH, authenticate via browser
gh auth setup-git                  # let git use gh for credentials
```

GitHub no longer accepts account passwords over HTTPS. Use a personal access token (fine-grained preferred), the GitHub CLI, or SSH. Never paste tokens into commits, chat, logs, or scripts.

### Sign your commits (shows "Verified" on GitHub)

SSH-based signing is the simplest path if you already use SSH:

```bash
git config --global gpg.format ssh
git config --global user.signingkey ~/.ssh/id_ed25519.pub
git config --global commit.gpgsign true
git config --global tag.gpgsign true
# optional local verification
echo "$(git config user.email) namespaces=\"git\" $(cat ~/.ssh/id_ed25519.pub)" >> ~/.ssh/allowed_signers
git config --global gpg.ssh.allowedSignersFile ~/.ssh/allowed_signers
```

Then add the same public key to GitHub as a **Signing Key** (Settings > SSH and GPG keys > New SSH key > Key type: Signing Key). GPG and S/MIME signing also work. GitHub automatically signs commits made in its web UI. Consider enabling **vigilant mode** so unsigned commits attributed to you are flagged.

### Separate work and personal identities

```ini
# ~/.gitconfig
[includeIf "gitdir:~/work/"]
    path = ~/.gitconfig-work
```

```ini
# ~/.gitconfig-work
[user]
    email = you@company.com
```

### Global ignore file

```bash
git config --global core.excludesFile ~/.gitignore_global
# put OS/editor junk here: .DS_Store, Thumbs.db, .idea/, .vscode/ (if not shared), *.swp
```

---

## 5. Creating and structuring a repository

### Start a repo

```bash
git init -b main
git add .gitignore README.md
git commit -m "chore: initial commit"

# publish with GitHub CLI
gh repo create my-project --private --source . --push
# or manually
git remote add origin git@github.com:USER/my-project.git
git push -u origin main
```

### Files every repository should have

| File | Purpose |
|---|---|
| `README.md` | What it is, how to install/run/test, how to contribute |
| `.gitignore` | Keeps junk, dependency folders, build output, local config, and secrets out |
| `LICENSE` | Legal terms (choose deliberately, especially for open source) |
| `CONTRIBUTING.md` | Dev setup, branching, commit style, how to run tests, PR expectations |
| `CODE_OF_CONDUCT.md` | Community standards (open source) |
| `SECURITY.md` | How to report vulnerabilities privately |
| `.github/PULL_REQUEST_TEMPLATE.md` | Structured PR descriptions |
| `.github/ISSUE_TEMPLATE/` | Structured bug reports and feature requests |
| `.github/CODEOWNERS` | Automatic reviewer assignment by path |
| `.github/dependabot.yml` | Automated dependency and Actions updates |
| `.github/workflows/*.yml` | CI/CD pipelines |
| `.gitattributes` | Line endings, diff/merge drivers, LFS tracking |
| `.env.example` | Placeholder variables (never real values) |

### `.gitignore` essentials

Set it up on day one. Common entries:

```gitignore
# Secrets and local config
.env
.env.*
!.env.example
*.pem
*.key
secrets.*

# Dependencies and build output
node_modules/
dist/
build/
__pycache__/
*.pyc
.venv/
target/

# OS / editor
.DS_Store
Thumbs.db
.idea/
*.swp
```

Important: `.gitignore` only affects **untracked** files. If a file is already tracked, stop tracking it without deleting it from disk:

```bash
git rm --cached path/to/file
git rm -r --cached path/to/dir
git commit -m "chore: stop tracking generated files"
```

Debug why something is ignored: `git check-ignore -v path/to/file`.

### `.gitattributes` basics

```gitattributes
* text=auto eol=lf
*.sh text eol=lf
*.bat text eol=crlf
*.png binary
*.jpg binary
*.pdf binary
```

This prevents the "LF will be replaced by CRLF" noise and cross-platform line-ending diffs.

### Large files

Do not commit large binaries (datasets, models, videos, build artifacts). GitHub rejects files above 100 MB and warns above 50 MB. Options: Git LFS for versioned large assets, release assets for distributables, or external storage with a download script.

```bash
git lfs install
git lfs track "*.psd" "*.zip"
git add .gitattributes
```

Track with LFS **before** committing the files. Migrating existing history later requires `git lfs migrate`.

---

## 6. The daily workflow (GitHub Flow)

```
main (always deployable)
  \__ feature/login-page --commit--commit--> push --> Pull Request --> review + CI --> squash merge --> delete branch
```

```bash
# 1. Start from fresh main
git switch main
git pull --ff-only

# 2. Branch immediately
git switch -c feature/login-page

# 3. Work in small commits
git add -p
git commit -m "feat(auth): add email validation to login form"

# 4. Stay current with main (rebase if unshared, merge if shared)
git fetch origin
git rebase origin/main          # or: git merge origin/main

# 5. Publish
git push -u origin HEAD

# 6. Open the PR
gh pr create --fill --draft     # draft until ready
gh pr ready                     # when CI is green and you want review

# 7. After merge: clean up
git switch main && git pull --ff-only
git branch -d feature/login-page
git push origin --delete feature/login-page   # skip if "delete branch on merge" is on
git fetch --prune
```

### Branch naming

Use a prefix and a short kebab-case description. Include an issue number when one exists.

| Prefix | Use for | Example |
|---|---|---|
| `feature/` | New functionality | `feature/user-authentication` |
| `bugfix/` or `fix/` | Non-urgent bug fixes | `bugfix/api-timeout-104` |
| `hotfix/` | Urgent production fixes | `hotfix/payment-crash` |
| `chore/` | Maintenance, dependencies, tooling | `chore/update-deps` |
| `docs/` | Documentation only | `docs/contributing-guide` |
| `refactor/` | Restructure without behavior change | `refactor/split-auth-module` |
| `test/` | Tests only | `test/checkout-edge-cases` |
| `release/` | Release stabilization (Gitflow) | `release/v2.1.0` |

Keep branches short-lived (ideally days, not weeks). Long-lived branches mean painful merges.

---

## 7. Branching strategies

### GitHub Flow (default recommendation)

One permanent branch (`main`). Short-lived feature branches, PR, review, merge, deploy. Best for web apps, SaaS, continuous deployment, small to mid-size teams, and most open-source projects.

### Trunk-based development

Everyone integrates into `main` at least daily, via very small branches (hours) or directly with feature flags. Needs strong CI and automated tests. Best for mature teams that deploy frequently.

### Gitflow

Permanent `main` (production) and `develop` (integration). `feature/*` branch from and merge into `develop`; `release/*` branches stabilize a version and merge into both `main` and `develop`; `hotfix/*` branch from `main`. Best for scheduled, versioned releases (desktop software, firmware, packaged libraries with multiple supported versions). Heavier process: do not adopt it unless you need release trains.

### Decision guide

| Situation | Choose |
|---|---|
| Continuous deployment, small team, web app | GitHub Flow |
| Strong CI, daily integration, feature flags | Trunk-based |
| Versioned releases, multiple supported versions | Gitflow (or GitHub Flow + `release/*` branches) |
| Open-source with external contributors | GitHub Flow + fork-and-pull |
| Solo project | GitHub Flow, even if you merge your own PRs |

---

## 8. Commits

### What makes a good commit

- **Atomic**: one logical change. If you need "and" in the subject, split it.
- **Complete**: builds and tests pass at every commit (this makes `git bisect` and reverts work).
- **Explained**: the body says *why*, not just *what*. The diff already shows what.
- **Clean**: no debug prints, no commented-out code, no unrelated whitespace churn, no secrets.

Avoid: `fix`, `update`, `stuff`, `wip`, `asdf`, `final final v2`.

### Message format (Conventional Commits 1.0.0)

```
<type>[optional scope][!]: <description>

[optional body]

[optional footer(s)]
```

Rules of thumb:

- Subject in **imperative mood** ("add", "fix", "remove"), no trailing period, about 50 characters (72 hard limit).
- Blank line, then a body wrapped at about 72 characters explaining motivation and contrast with previous behavior.
- Footers use trailer format: `Closes #42`, `Refs: #17`, `Co-authored-by: Name <email>`, `BREAKING CHANGE: description`.

| Type | Meaning | SemVer effect |
|---|---|---|
| `feat` | New user-facing feature | MINOR |
| `fix` | Bug fix | PATCH |
| `docs` | Documentation only | none |
| `style` | Formatting only, no logic change | none |
| `refactor` | Code change that neither fixes a bug nor adds a feature | none |
| `perf` | Performance improvement | none (usually PATCH by convention) |
| `test` | Add or correct tests | none |
| `build` | Build system or dependencies | none |
| `ci` | CI configuration | none |
| `chore` | Maintenance not touching src or tests | none |
| `revert` | Reverts an earlier commit | depends |
| any type with `!` or `BREAKING CHANGE:` footer | Backward-incompatible change | MAJOR |

`feat` and `fix` are the types the specification itself defines. The rest are the widely used Angular-style conventions and have no SemVer effect unless they carry a breaking change. `BREAKING CHANGE` must be uppercase in a footer; `BREAKING-CHANGE` is accepted as a synonym.

Examples:

```
feat(auth): add email validation to login form

Reject malformed addresses client-side before hitting the API so users
get instant feedback and we cut invalid requests.

Closes #42
```

```
fix(api): handle null user in session lookup
```

```
feat(api)!: change response envelope to {data, error}

BREAKING CHANGE: clients must read payloads from `data`; the top-level
array response was removed.
```

```
revert: feat(auth): add email validation to login form

This reverts commit 1a2b3c4d.
```

If a change fits several types, split it into several commits, or pick the highest-impact type.

### Linking to issues

Closing keywords in a commit message or PR description auto-close the issue when the change reaches the default branch: `Closes #12`, `Fixes #34`, `Resolves #56` (also `closes owner/repo#12` across repositories).

### Fixup commits and autosquash

When you notice a mistake in an earlier, unpushed commit:

```bash
git commit --fixup <sha>              # creates "fixup! <original subject>"
git rebase -i --autosquash origin/main
```

With `rebase.autoSquash true`, the fixup lines are pre-arranged for you.

### Commit message template (optional)

```bash
git config --global commit.template ~/.gitmessage
```

```
# <type>(<scope>): <imperative summary, <= 50 chars>
#
# Why is this change needed? What was the previous behavior?
#
# Closes #
```

### Enforce conventions automatically

- **commitlint** with `@commitlint/config-conventional` validates messages.
- **husky** or **pre-commit** (Python) run linters, formatters, tests, and secret scanners before a commit.
- **semantic-release**, **release-please**, or **release-drafter** turn Conventional Commits into version bumps and changelogs.

Hooks are local and bypassable, so always duplicate important checks in CI.

---

## 9. Staging and inspecting

### Staging precisely

```bash
git add path/to/file            # specific file
git add -p                      # review and stage hunk by hunk (strongly recommended)
git add -u                      # stage modifications/deletions of tracked files only
git restore --staged file       # unstage
git restore file                # discard working-tree changes (irreversible for uncommitted work!)
git rm file                     # delete and stage deletion
git mv old new                  # rename and stage
```

### Looking around

```bash
git status -sb                           # short status with branch info
git diff                                 # unstaged changes
git diff --staged                        # staged changes
git diff main...HEAD                     # what this branch adds relative to main (three dots)
git diff --stat main...HEAD              # summary
git diff --check                         # find whitespace errors and leftover conflict markers
git log --oneline --graph --decorate --all
git log -p -- path/to/file               # history of a file with patches
git log --follow -- path/to/file         # follow renames
git log -S"function_name"                # commits that added/removed that string (pickaxe)
git log -G"regex"                        # commits whose diff matches a regex
git log --author="name" --since="2 weeks ago"
git log main..feature                    # commits in feature not in main
git show <sha>                           # one commit with its diff
git show <sha>:path/to/file              # file as of that commit
git blame -L 10,30 path/to/file          # who changed these lines (add -w to ignore whitespace)
git shortlog -sn                         # commits per author
git branch -vv                           # branches with upstream and ahead/behind
git branch --merged main                 # safe-to-delete branches
git branch --no-merged main
git remote -v
```

Ignore noisy formatting commits in blame: put their SHAs in `.git-blame-ignore-revs` and run `git config blame.ignoreRevsFile .git-blame-ignore-revs`. GitHub honors this file automatically.

---

## 10. Syncing with the remote: fetch, pull, merge, rebase

```bash
git fetch origin                  # download, change nothing local (always safe)
git pull --ff-only                # fast-forward only; fails instead of creating a merge
git pull --rebase                 # replay your local commits on top of upstream
git merge origin/main             # merge main into your branch
git rebase origin/main            # replay your branch on top of main
```

### Merge vs rebase

| | Merge | Rebase |
|---|---|---|
| History | Preserves true history, adds a merge commit | Linear, rewrites your commits (new SHAs) |
| Safe on shared branches | Yes | **No** |
| Conflict handling | Resolve once | Resolve per replayed commit |
| Best for | Integrating shared branches, bringing `main` into a branch others use | Tidying your own unpublished branch before review |

**Golden rule of rebase:** never rebase commits that exist outside your repository and that others may have based work on. If you already pushed your feature branch and nobody else uses it, you may rebase and then `git push --force-with-lease`.

### Pushing safely

```bash
git push                                 # normal
git push -u origin HEAD                  # first push of a new branch
git push --force-with-lease              # after rebase/amend of YOUR pushed branch; refuses if the remote has commits you have not seen
git push --force-with-lease --force-if-includes   # extra safety on recent Git
# NEVER plain --force; NEVER to main/master/develop
```

If a push is rejected as "non-fast-forward", someone else pushed first: `git pull --rebase` (or merge), re-test, push again. Do not force.

### Which merge button to press on GitHub

| Method | Result | Use when |
|---|---|---|
| **Squash and merge** | All PR commits become one commit on the base branch | Default for most teams; keeps `main` readable and one-commit-per-PR. PR title becomes the commit subject, so make it a Conventional Commit |
| **Rebase and merge** | PR commits replayed individually, no merge commit | Commits are already clean and atomic and you want linear history |
| **Merge commit** | Preserves all commits plus a merge commit | You want a faithful record, or long-lived branches/release branches |

Pick one default per repository and disable the others in settings to stay consistent.

---

## 11. Merge conflicts

### Anatomy

```
<<<<<<< HEAD (ours: the branch you are on)
your version
||||||| base          (only with merge.conflictStyle diff3/zdiff3)
original version
=======
incoming version
>>>>>>> feature (theirs: what is being merged in)
```

### Step by step

```bash
git status                      # lists "both modified" files
# open each file, understand BOTH sides' intent, edit to the correct final content,
# remove ALL markers (<<<<<<<, =======, >>>>>>>)
git diff --check                # detects leftover markers
# run tests / build
git add path/to/file
git merge --continue            # or: git rebase --continue / git cherry-pick --continue
```

Bail out safely at any time:

```bash
git merge --abort
git rebase --abort
git cherry-pick --abort
```

### Tools and tricks

```bash
git mergetool                           # open configured visual merge tool
git config --global mergetool.keepBackup false
git log --merge --oneline               # commits on each side touching conflicted files
git diff --name-only --diff-filter=U    # list unmerged files
git checkout --conflict=merge file      # recreate conflict markers if you botched a file
git rerere                              # reuse recorded resolutions (enable rerere.enabled)
git rerere diff | git rerere forget file   # inspect or discard a recorded resolution
```

### ours/theirs: the classic trap

| Operation | `--ours` | `--theirs` |
|---|---|---|
| `git merge feature` (on main) | main (your current branch) | feature (incoming) |
| `git rebase main` (on feature) | **main (the upstream you are replaying onto)** | **your feature commit being replayed** |

They flip during rebase. Always check before using `git checkout --ours/--theirs file`.

Strategy options: `git merge -X ours <branch>` resolves only *conflicting hunks* in favor of the current branch (non-conflicting changes from both sides still merge). `git merge -s ours <branch>` is far more destructive: it records a merge but discards the other branch's content entirely. Do not confuse them. Blindly picking a side with `-X theirs`/`-X ours` can silently drop correct changes, so read the diff before accepting.

### Prevention

- Rebase/merge `main` into your branch daily.
- Keep PRs small and short-lived.
- Do not mix reformatting with logic changes.
- Coordinate on hot files (lockfiles, generated code, shared config). For lockfiles, resolve by regenerating them: merge, then run the package manager install, then commit.

---

## 12. Rewriting history (local, unpublished work only)

### Amend the last commit

```bash
git commit --amend                       # edit message and/or add staged changes
git commit --amend --no-edit             # add staged changes, keep message
```

### Interactive rebase

```bash
git rebase -i HEAD~5                     # last five commits
git rebase -i origin/main                # everything on this branch since main
```

Commands in the todo list: `pick` keep, `reword` edit message, `edit` stop to amend/split, `squash` meld into previous and edit message, `fixup` meld and discard message, `drop` delete, `exec` run a command. Reordering lines reorders commits.

Always make a backup first when in doubt:

```bash
git branch backup/pre-rebase
```

### Split a commit

```bash
git rebase -i <sha>^          # mark the commit as "edit"
git reset HEAD^               # unstage everything from that commit, keep changes in the tree
git add -p && git commit -m "first part"
git add -p && git commit -m "second part"
git rebase --continue
```

### Move a branch onto a different base

```bash
git rebase --onto <newbase> <oldbase> <branch>
# e.g. feature was cut from a stale topic branch, move it onto main:
git rebase --onto main topic-old feature
```

### Squash a whole branch before PR

```bash
git reset --soft $(git merge-base HEAD origin/main)
git commit -m "feat(scope): single clean commit"
```

(Or simply let GitHub squash-merge it.)

### Large rewrites across all history (remove files, rewrite authors, strip big blobs)

Use `git filter-repo` (not `filter-branch`). Work in a fresh clone, then coordinate a force-push, because every collaborator must re-clone or hard-reset.

```bash
pip install git-filter-repo         # or brew install git-filter-repo
git clone --no-local original-repo cleaned && cd cleaned
git filter-repo --path secrets.env --invert-paths        # delete a file everywhere
git filter-repo --path-glob '*.pem' --invert-paths
git filter-repo --replace-text replacements.txt          # redact strings: "OLDVALUE==>REMOVED"
git filter-repo --strip-blobs-bigger-than 10M
git filter-repo --analyze                                # report what is bloating the repo
```

BFG Repo-Cleaner is a faster, less flexible alternative. After any rewrite, force-push all branches and tags, ask collaborators to re-clone, and remember that forks, clones, caches, and PR refs may still hold the old data.

---

## 13. Undo and recovery cheat sheet

First, **stop and look**: `git status`, `git reflog`. Avoid `git gc`, pruning, and more `reset --hard` while unsure.

### Uncommitted changes

| I want to... | Command |
|---|---|
| Discard changes in one file (irreversible) | `git restore path` |
| Unstage a file but keep edits | `git restore --staged path` |
| Get a file as it was in another commit | `git restore --source=<sha> path` |
| Stash work temporarily | `git stash push -m "msg"` (include untracked: `-u`) |
| Discard all uncommitted work (irreversible) | `git restore . && git clean -fd` (preview with `git clean -nd`) |

### Local commits (not pushed)

| I want to... | Command |
|---|---|
| Undo last commit, keep changes staged | `git reset --soft HEAD~1` |
| Undo last commit, keep changes unstaged | `git reset HEAD~1` (mixed, default) |
| Undo last commit and discard changes | `git reset --hard HEAD~1` (careful) |
| Fix last commit message or add a forgotten file | `git commit --amend` |
| Committed on the wrong branch | `git branch correct-branch && git reset --hard HEAD~1 && git switch correct-branch` (or `git cherry-pick <sha>` onto the right branch, then reset the wrong one) |
| Move my last N commits onto a new branch | `git branch new-branch && git reset --hard HEAD~N && git switch new-branch` |

### Already pushed or shared

| I want to... | Command |
|---|---|
| Undo a commit without rewriting history | `git revert <sha>` (creates an inverse commit) |
| Revert a merge commit | `git revert -m 1 <merge-sha>` (keep parent 1, usually main) |
| Revert a range | `git revert OLD..NEW` |
| Take one commit from another branch | `git cherry-pick <sha>` (`-x` appends the origin SHA; `-n` stages without committing) |

Reverting a merge tells Git that merge's changes are intentionally gone; re-merging the same branch later will not bring them back unless you revert the revert.

### Recovery with the reflog

The reflog records every move of `HEAD` locally (commits, checkouts, resets, rebases, merges). Teammates and GitHub cannot see it.

```bash
git reflog                                  # find the state before the mistake
git reflog show feature/payments            # reflog of one branch
git reflog --date=iso
```

| Mistake | Fix |
|---|---|
| `reset --hard` removed commits | `git reflog` then `git reset --hard HEAD@{1}` (or the SHA) |
| Immediately after merge/rebase/reset | `git reset --hard ORIG_HEAD` |
| Bad rebase | `git reflog \| grep "rebase (start)"`, then `git reset --hard <sha-before-start>`; or `git reset --hard ORIG_HEAD` |
| Deleted a branch | `git reflog` (find its last commit) then `git branch restored-name <sha>` |
| Lost a stash | `git fsck --lost-found --no-reflogs` then inspect with `git show <sha>` and `git stash apply <sha>` |
| Amended and want the original | `git reflog`, then `git branch recovered <sha>` |
| Reflog does not show it | `git fsck --lost-found` lists dangling commits; inspect with `git show`, restore with `git branch recovered <sha>` |
| Someone force-pushed over `main` | Find the old tip in any clone (`git reflog show origin/main`), `git branch rescue <sha>`, then coordinate a fix (preferably restore via protected process) |

Create a recovery branch the moment you find the commit: `git branch recovery/lost-work <sha>` and `git switch recovery/lost-work`.

Reflog is not a backup. By default, entries for reachable commits expire after about 90 days and unreachable ones after about 30, after which `git gc` may delete them. Reflog also cannot recover uncommitted work that was never staged or stashed.

### Find which commit broke something

```bash
git bisect start
git bisect bad                  # current commit is broken
git bisect good v1.4.0          # a commit/tag known to work
# test, then answer: git bisect good | git bisect bad  (repeat)
git bisect reset                # when done
# automate:
git bisect run ./test.sh        # script exits 0 for good, 1-127 (except 125) for bad
```

---

## 14. Other power tools

### Stash

```bash
git stash push -m "wip: header refactor"     # tracked changes
git stash push -u                            # include untracked files
git stash push -p                            # choose hunks
git stash list
git stash show -p stash@{0}
git stash apply stash@{0}                    # keep the stash
git stash pop                                # apply and drop
git stash branch new-branch stash@{0}        # turn a stash into a branch
git stash drop stash@{0}
```

Prefer a WIP commit on a branch (or a worktree) over long-lived stashes.

### Worktrees: multiple branches checked out at once

```bash
git worktree add ../myrepo-hotfix -b hotfix/crash origin/main
git worktree list
git worktree remove ../myrepo-hotfix
git worktree prune
```

Great for urgent hotfixes, reviewing a PR while keeping your work intact, running long tests on one branch while coding on another, and parallel AI-agent work (one worktree per agent avoids agents clobbering each other).

### Cherry-pick

```bash
git cherry-pick <sha>
git cherry-pick <sha1> <sha2>
git cherry-pick A^..B            # inclusive range
git cherry-pick -x <sha>         # record origin in message
git cherry-pick --continue | --abort
```

Typical use: backporting a fix to a release branch.

### Tags

```bash
git tag -a v1.2.0 -m "Release 1.2.0"        # annotated (preferred for releases)
git tag -s v1.2.0 -m "Release 1.2.0"        # signed
git tag                                     # list
git push origin v1.2.0                      # push one tag
git push --follow-tags                      # push commits plus annotated tags reachable from them
git tag -d v1.2.0 && git push origin :refs/tags/v1.2.0   # delete (avoid for published releases)
```

### Submodules and subtrees

Submodules pin another repo at an exact commit: `git submodule add <url> path`, clone with `git clone --recurse-submodules`, update with `git submodule update --init --recursive`. They add friction, so use them only when truly needed; `git subtree` or a package manager is often simpler.

### Clean untracked files

```bash
git clean -nd        # dry run (always run this first)
git clean -fd        # delete untracked files and directories
git clean -fdx       # also delete ignored files (build output, .env!)
```

### Sparse and partial clones (huge repos)

```bash
git clone --filter=blob:none --sparse <url>
git sparse-checkout set path/one path/two
git clone --depth 1 <url>             # shallow clone for CI
```

### Maintenance

```bash
git maintenance start      # schedule background gc/prefetch
git gc --auto
git count-objects -vH
git fsck
```

---

## 15. Remotes, forks, and upstream

```bash
git remote -v
git remote add upstream https://github.com/ORIGINAL/REPO.git
git remote set-url origin git@github.com:YOU/REPO.git
git remote rename origin upstream
git remote prune origin
```

### Fork-and-pull workflow (open source and external contribution)

```bash
gh repo fork ORIGINAL/REPO --clone          # forks, clones, and sets up `upstream`
cd REPO
git switch -c fix/typo-in-readme
# ...commit...
git push -u origin HEAD
gh pr create --repo ORIGINAL/REPO --fill
```

### Keep a fork up to date

```bash
# quick (CLI)
gh repo sync YOU/REPO                       # sync fork's default branch with upstream
gh repo sync YOU/REPO -b main --force       # discard fork-only commits on that branch (careful)

# manual
git fetch upstream
git switch main
git merge --ff-only upstream/main           # or: git rebase upstream/main
git push origin main
```

The web UI "Sync fork" button also works (it performs a merge-style update). Never commit directly on your fork's `main` if you want sync to stay trivial; do your work on feature branches.

---

## 16. Pull requests

### Before opening

- [ ] Branch is up to date with the base branch and conflicts resolved.
- [ ] Tests, linters, type checks pass locally.
- [ ] You read your own diff (`git diff main...HEAD`) as if you were the reviewer. Remove debug code, stray files, and secrets.
- [ ] Commits are clean (or you will squash on merge).
- [ ] One concern per PR. Aim for **under ~400 changed lines**; reviews of 100 lines catch bugs, reviews of 2,000 lines produce rubber-stamp approvals.
- [ ] Docs, tests, and changelog updated where relevant.

### Writing the PR

- **Title**: Conventional-Commit style, because with squash merge it becomes the commit message.
- **Description**: what and why, how it was tested, screenshots for UI, risks/rollout notes, linked issues (`Closes #123`), breaking changes called out.
- Use **Draft PRs** for early feedback on work in progress. Convert to ready when CI is green.
- Request specific reviewers; CODEOWNERS will auto-request owners.
- Use labels (`bug`, `feature`, `breaking`, `needs-docs`) so release notes and triage can be automated.

### Reviewing

**As reviewer**

- Understand the intent first (linked issue, description), then review the design, then details.
- Check correctness, edge cases, error handling, security (injection, authz, secrets), performance, tests, naming, and docs.
- Be specific and kind. Explain *why*. Separate blocking issues from nits (`nit:`, `optional:`, `question:`, `blocking:`).
- Use GitHub suggestions (` ```suggestion `) for small fixes.
- Review in a timely manner; stale PRs rot.
- Do not approve what you did not understand.

**As author**

- Treat feedback as collaboration, not gatekeeping. Respond to every comment (fix, or explain why not).
- Push follow-up commits during review (do not force-push over reviewed commits unless asked; use `--fixup` and let squash-merge tidy up).
- Re-request review after addressing comments. Resolve conversations only when addressed.
- Never merge your own PR in a team setting without the required approval.

### Useful PR features

- **Draft PRs**, **auto-merge** (merge when checks pass), **merge queue** (serializes merges and tests the combined result), **suggested changes**, **required reviewers**, **conversation resolution requirement**, **linked issues/Projects**, **Copilot or bot reviews** (treat as input, not authority).

---

## 17. Issues, Projects, Milestones, Discussions

- **Issues** track bugs, tasks, features. One actionable thing per issue; assign an owner so work is not duplicated.
- **Labels**: type (`bug`, `feature`, `docs`, `refactor`), priority (`p0` critical, `p1` high, `p2` medium), status (`needs-triage`, `blocked`), difficulty (`good first issue`, `help wanted`). Keep the set small and documented.
- **Issue templates** (`.github/ISSUE_TEMPLATE/*.yml` forms) force reproduction steps, environment, expected vs actual behavior.
- **Projects** (Kanban/table/roadmap): columns like Todo, In Progress, In Review, Done; enable built-in workflows so items move automatically when a PR is linked or merged.
- **Milestones** group issues/PRs toward a release or sprint (`v1.0-beta`, `2026-Q4-Sprint-2`) and show progress.
- **Sub-issues** break large work into trackable pieces.
- **Discussions** keep Q&A, ideas, and community chatter out of the issue tracker, so Issues stay actionable.
- **Stale automation** (e.g. `actions/stale`) closes abandoned issues/PRs after a warning period. Exempt security and `pinned` items.
- Create a branch from an issue: `gh issue develop 42 --checkout`.

---

## 18. Repository settings and governance

### Recommended repository settings

| Setting | Recommendation |
|---|---|
| Default branch | `main` |
| Merge methods | Allow squash (preferred); disable others unless needed |
| Automatically delete head branches | **On** |
| Allow auto-merge | On once required checks exist |
| Always suggest updating PR branches | On |
| Allow force pushes / deletions on default branch | **Off** |
| Vulnerability alerts, Dependabot security updates | **On** |
| Secret scanning and push protection | **On** |
| Code scanning (CodeQL) | On for supported languages |
| Require 2FA for org members | **On** |

### Protect the default branch

Use **rulesets** (newer, layered, can apply across many repos, per-rule bypass control) or classic **branch protection rules**. Core rules:

- Require a pull request before merging (1 approval for small teams; 2 for critical code).
- Dismiss stale approvals when new commits are pushed.
- Require review from Code Owners (only once a real `CODEOWNERS` file exists).
- Require status checks to pass, and require branches to be up to date. Only require checks that actually run, with the exact job names, or merges will hang.
- Require conversation resolution.
- Require signed commits (optional, adds friction, adds assurance).
- Require linear history (matches squash/rebase workflows).
- Require merge queue for busy repos.
- Block force pushes and branch deletion.
- Apply rules to administrators too (otherwise admins bypass everything).

Notes: branch-protection bypass is all-or-nothing and can skip merge queue as well. Rulesets give finer bypass control. Private repos on free plans may have limited protection features.

Set via CLI/API when automating (verify current API shapes in the docs before scripting):

```bash
gh api repos/OWNER/REPO/rulesets            # list rulesets
gh api repos/OWNER/REPO/branches/main/protection   # classic protection
```

### CODEOWNERS

Location: `.github/CODEOWNERS`, `CODEOWNERS`, or `docs/CODEOWNERS` in the repository itself (an org-level `.github` repo does not satisfy it). Later patterns override earlier ones.

```
# Default owners
*                       @org/maintainers

# Areas
/backend/               @org/backend-team
/frontend/              @org/frontend-team @alice
/docs/                  @org/docs
*.tf                    @org/platform
/.github/workflows/     @org/security @org/platform
```

Protect `.github/workflows/` with required security review, since workflow changes can exfiltrate secrets.

### Teams and permissions

Grant the minimum role needed: Read, Triage, Write, Maintain, Admin. Prefer team-based access over individuals. Review outside collaborators regularly.

---

## 19. GitHub Actions (CI/CD)

### Baseline CI workflow

```yaml
# .github/workflows/ci.yml
name: CI

on:
  pull_request:
  push:
    branches: [main]

# Least privilege for the automatic GITHUB_TOKEN
permissions:
  contents: read

# Cancel superseded runs on the same ref
concurrency:
  group: ci-${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    strategy:
      fail-fast: false
      matrix:
        node: [20, 22]
    steps:
      # Pin third-party actions to a full commit SHA, with the tag in a comment.
      - uses: actions/checkout@<full-40-char-commit-sha>   # v4.x.x
      - uses: actions/setup-node@<full-40-char-commit-sha> # v4.x.x
        with:
          node-version: ${{ matrix.node }}
          cache: npm
      - run: npm ci
      - run: npm run lint
      - run: npm test -- --ci
      - run: npm run build
```

Replace the placeholders with real SHAs from each action's repository (not a fork), and keep them fresh with Dependabot.

### Workflow design tips

- Trigger on `pull_request` for CI so checks gate merges; use `push` to `main` for deploys.
- Name required jobs stably; branch protection matches on job names.
- Use `concurrency` to cancel redundant runs; use `timeout-minutes` to stop runaways.
- Cache dependencies (`actions/cache` or setup-action `cache:` inputs).
- Use matrix builds for OS/runtime versions.
- Split fast checks (lint, unit tests) from slow ones (integration, e2e); run slow ones only when needed using `paths:` filters.
- Reusable workflows (`workflow_call`) and composite actions remove duplication across repos.
- Use **environments** (staging, production) with required reviewers and environment-scoped secrets for deployments.
- Prefer **OIDC** to exchange a short-lived identity token for cloud credentials instead of storing long-lived cloud keys as secrets.
- Upload artifacts for test reports and build outputs (`actions/upload-artifact`); set retention deliberately.

### Security rules for workflows

1. **Set `permissions:` explicitly**, default to `contents: read` (or `permissions: {}`), and grant write scopes per job only where needed. Also set the repository/org default token permission to read-only.
2. **Pin third-party actions to a full-length commit SHA.** That is the only immutable reference. Tags and branches can be moved by whoever controls the action. Prefer GitHub-owned and verified-creator actions, and consider an allowlist.
3. **Never interpolate untrusted input directly into shell.** Issue titles, PR titles, branch names, commit messages, and `github.event.*` fields can carry injection payloads. Pass them through environment variables:

```yaml
# BAD: script injection
- run: echo "Title: ${{ github.event.pull_request.title }}"

# GOOD
- env:
    PR_TITLE: ${{ github.event.pull_request.title }}
  run: echo "Title: $PR_TITLE"
```

4. **Be very careful with `pull_request_target` and `workflow_run`.** They run with secrets and write tokens in the context of the base repo. Never check out and execute untrusted PR code in those contexts.
5. **Store secrets in Actions Secrets/Variables**, never in code. Secrets are masked in logs but can still be leaked by careless scripts; do not echo or transform them.
6. **Require review for changes to `.github/workflows/`** via CODEOWNERS.
7. **Self-hosted runners**: use only for private repos, prefer ephemeral runners, isolate them, and never expose them to untrusted PRs.
8. Enable Dependabot for the `github-actions` ecosystem so pinned SHAs get update PRs.

### Dependabot

```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: "npm"            # also: pip, maven, gradle, cargo, gomod, docker, ...
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 5
    groups:
      minor-and-patch:
        update-types: ["minor", "patch"]
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
```

### Debug runs from the terminal

```bash
gh run list --limit 10
gh run view <run-id> --log-failed
gh run watch <run-id>
gh run rerun <run-id> --failed
gh workflow list
gh workflow run ci.yml --ref my-branch
```

---

## 20. Secrets and security

### Prevention

- `.gitignore` for `.env`, keys, and credentials from the first commit; commit `.env.example` with placeholders only.
- Load config from environment variables or a secrets manager. Prefer short-lived credentials (OIDC, workload identity) to static keys.
- Enable GitHub **secret scanning** and **push protection** (blocks pushes containing detected secrets).
- Add a local scanner in pre-commit (gitleaks, trufflehog, detect-secrets) **and** a server-side check in CI, since hooks are bypassable.
- Scan full history once for a baseline, then scan diffs on every push.
- Check places scanners often skip: notebooks, CI files, Dockerfiles/build args, commit messages, test fixtures.

### Incident response: "I committed a secret"

Deleting the line in a new commit does **not** remove it; the old blob stays reachable through history, forks, clones, PR refs, and CI caches.

1. **Rotate/revoke the credential immediately** at the provider and confirm the old one fails. Assume it is compromised from the moment it was pushed (even in private repos).
2. Check access logs of the affected service for misuse.
3. Remove it from history: `git filter-repo --path file --invert-paths` or `--replace-text`, in a fresh clone (see section 12).
4. Force-push all branches and tags, tell collaborators to re-clone, ask GitHub Support to purge cached views/PR refs if the data was public.
5. Add a detection rule and fix the root cause (why was the secret in a file at all?).

If push protection blocked you before the push landed, you only need to remove the secret from your local commits (amend or interactive rebase), rotate it if it was ever live in a shared place, and push again. Do not use the "allow this secret" bypass unless it is a verified false positive.

### Repository security features to enable

- Dependabot alerts and security updates; Dependabot version updates.
- Code scanning with CodeQL (default setup is the easiest).
- Secret scanning plus push protection.
- Private vulnerability reporting, plus a `SECURITY.md` explaining how to report.
- Security advisories to publish fixes and CVEs for open-source projects.
- Dependency review action on PRs to block risky new dependencies.
- 2FA (passkeys/security keys preferred) for every account with write access; review deploy keys and PATs regularly; prefer fine-grained tokens with expiry.

---

## 21. Releases and versioning

### Semantic Versioning (`vMAJOR.MINOR.PATCH`)

- **MAJOR**: breaking changes.
- **MINOR**: backward-compatible features.
- **PATCH**: backward-compatible fixes.
- Pre-releases: `v2.0.0-rc.1`, `v2.0.0-beta.3`.

Conventional Commits map directly: `fix` is PATCH, `feat` is MINOR, any breaking marker is MAJOR.

### Release flow

```bash
git switch main && git pull --ff-only
# ensure CI is green, changelog updated
git tag -a v1.4.0 -m "v1.4.0"        # or -s to sign
git push origin v1.4.0
gh release create v1.4.0 --generate-notes --title "v1.4.0"
gh release create v1.4.0 dist/*.zip --notes-file CHANGELOG-1.4.0.md   # with assets
gh release list
```

- Never move or delete a published tag; publish a new patch release instead.
- Keep a `CHANGELOG.md` ([Keep a Changelog](https://keepachangelog.com) format) with an `Unreleased` section; do not edit sections of already released versions.
- Automate with **release-drafter**, **release-please**, **semantic-release**, or GitHub's built-in generated release notes.
- Hotfix flow: branch from the release tag/`main`, fix, PR, tag a PATCH, and merge back to any other long-lived branch (`develop`, older `release/*`) via cherry-pick.
- Use **release branches** (`release/v2.1.0`) when stabilization must continue while `main` keeps moving.

---

## 22. Running an open-source project

- **Fork-and-pull model**: maintainers work in the upstream repo; outside contributors fork and PR from forks, so upstream stays free of abandoned branches.
- **CONTRIBUTING.md**: environment setup, how to run tests and linters, code style, commit convention, PR process, how decisions are made.
- **Templates**: bug report (steps to reproduce, environment, expected vs actual), feature request, PR checklist (linked issue, tests run, breaking changes listed).
- **CLA or DCO**: use a bot (CLA Assistant, DCO app) so contributors legally certify their contributions. DCO uses `git commit -s` to add `Signed-off-by:`.
- **Labels** for onboarding: `good first issue`, `help wanted`; clear triage labels for type and priority.
- **Governance files**: `CODE_OF_CONDUCT.md`, `SECURITY.md`, `GOVERNANCE.md` or `MAINTAINERS.md`, `FUNDING.yml` if relevant.
- **Squash and merge** keeps history clean regardless of how messy a contributor's branch was. Pair it with Conventional Commit PR titles for automatic changelogs.
- **Automation**: CI on every PR, Dependabot, CodeQL, stale bot, labeler, release-drafter, auto-assign reviewers via CODEOWNERS.
- **Be welcoming and responsive**: acknowledge PRs quickly, give actionable feedback, thank contributors, and close with a clear explanation when declining.
- Support **multiple release lines** with `release/*` branches and cherry-pick backports labeled `backport-to-v2`.

---

## 23. GitHub CLI (`gh`) reference

Most `view` and `list` commands accept `--web` to open the browser instead, and many accept `--json fields --jq expr` for scripting.

### Auth and setup

```bash
gh auth login
gh auth status
gh auth refresh -s workflow,read:org      # add token scopes
gh config set editor "code --wait"
gh alias set co 'pr checkout'
```

### Repositories

```bash
gh repo create NAME --public|--private --source . --push --description "..."
gh repo clone OWNER/REPO
gh repo fork OWNER/REPO --clone
gh repo view [--web]
gh repo list OWNER --limit 50
gh repo sync [OWNER/REPO] [-b branch]
gh repo edit --delete-branch-on-merge --enable-squash-merge --enable-merge-commit=false --enable-rebase-merge=false
gh repo delete OWNER/REPO --yes           # destructive, needs delete_repo scope
```

### Issues

```bash
gh issue create --title "..." --body "..." --label bug --assignee @me
gh issue list --assignee @me --state open
gh issue view 42 --comments
gh issue comment 42 --body "..."
gh issue close 42 / gh issue reopen 42
gh issue develop 42 --checkout            # create and check out a linked branch
```

### Pull requests

```bash
gh pr create --fill                       # title/body from commits
gh pr create --draft --title "feat: ..." --body "..." --label bug --reviewer user1,org/team
gh pr ready                               # draft to ready
gh pr list [--author @me --state open]
gh pr status
gh pr view 7 [--comments|--web]
gh pr checkout 7                          # check out a PR locally
gh pr diff 7
gh pr checks 7 --watch                    # live CI status
gh pr review 7 --approve|--request-changes|--comment --body "..."
gh pr comment 7 --body "..."
gh pr merge 7 --squash --delete-branch    # or --rebase / --merge
gh pr merge 7 --auto --squash             # merge when requirements pass
gh pr edit 7 --add-label ready --add-reviewer user
gh pr close 7 / gh pr reopen 7
```

(You cannot approve your own PR.)

### Actions, releases, secrets

```bash
gh run list / gh run view ID --log-failed / gh run watch ID / gh run rerun ID --failed
gh workflow list / gh workflow run NAME / gh workflow enable|disable NAME
gh release create TAG --generate-notes [files...]
gh release list / gh release view TAG / gh release download TAG
gh secret set NAME            # prompts; never pass secret values on the command line history
gh secret list
gh variable set NAME --body value
gh cache list
```

### Raw API and extras

```bash
gh api repos/OWNER/REPO/pulls/7/comments
gh api graphql -f query='query { viewer { login } }'
gh api --paginate repos/OWNER/REPO/issues --jq '.[].title'
gh gist create file.py --public
gh search repos "topic:aerospace language:python" --limit 10
gh extension install OWNER/gh-extension
gh browse                      # open the repo in the browser
```

---

## 24. Troubleshooting table

| Symptom | Cause | Fix |
|---|---|---|
| `! [rejected] ... (non-fast-forward)` | Remote has commits you do not | `git pull --rebase` (or merge), re-test, push. Use `--force-with-lease` only after rewriting your own branch |
| `fatal: not a git repository` | Wrong directory | `cd` into the repo or `git init` |
| `You are in 'detached HEAD' state` | Checked out a commit/tag | `git switch -c new-branch` to keep work, or `git switch -` to leave |
| `refusing to merge unrelated histories` | Two repos with no common ancestor | Confirm it is intended, then `git pull --allow-unrelated-histories` |
| `Permission denied (publickey)` | SSH key not loaded or not on GitHub | `ssh-add`, add the key to GitHub, test `ssh -T git@github.com` |
| `Authentication failed` / password auth removed | HTTPS passwords unsupported | `gh auth login`, use a token or SSH |
| `src refspec main does not match any` | No commits yet, or branch named differently | Make an initial commit; check `git branch` |
| `error: failed to push some refs ... protected branch` | Branch protection | Push a feature branch and open a PR |
| `GH013: Repository rule violations` / push protection blocked | Secret detected or rule violated | Remove the secret from commits, rotate it; read the message for the exact rule |
| `remote: error: File X is 120 MB; exceeds 100 MB limit` | Large file in history | Remove it from history (`filter-repo`), use Git LFS |
| `LF will be replaced by CRLF` | Line-ending config | Add `.gitattributes` (`* text=auto eol=lf`) |
| Changes to a file are not ignored after adding it to `.gitignore` | File already tracked | `git rm --cached file` |
| `Your local changes would be overwritten by checkout/merge` | Uncommitted edits conflict | Commit, or `git stash`, then retry |
| Merge conflict marker left in code | Forgot to clean up | `git diff --check`; search for `<<<<<<<` |
| `fatal: refusing to ... branch is already checked out at ...` | Branch in another worktree | Use another branch or remove that worktree |
| Branch shows "ahead N, behind M" | Diverged | `git fetch`, then rebase (unshared) or merge |
| Pushed to wrong branch / wrong commit | Human error | `git revert` if shared; if just pushed to your own branch, fix and `--force-with-lease` |
| `.git` folder is huge | Big blobs in history | `git filter-repo --analyze`, strip blobs, adopt LFS |
| Accidentally committed to `main` locally (not pushed) | Skipped branching | `git branch feature/x && git reset --hard origin/main && git switch feature/x` |
| PR checks "Expected - Waiting for status" forever | Required check name does not match any running job | Fix the required-check name in the ruleset or the job name in the workflow |
| Dependabot or Actions cannot push / write | Token permissions too low | Add the specific `permissions:` the job needs |

---

## 25. Ready-to-use templates

### `.github/PULL_REQUEST_TEMPLATE.md`

```markdown
## Summary
<!-- What does this change do, and why? -->

## Linked issue
Closes #

## Type of change
- [ ] feat  - [ ] fix  - [ ] docs  - [ ] refactor  - [ ] test  - [ ] chore  - [ ] breaking

## How was this tested?
<!-- Commands run, scenarios covered, screenshots for UI -->

## Checklist
- [ ] Tests added/updated and passing
- [ ] Lint and type checks pass
- [ ] Docs/changelog updated
- [ ] No secrets, debug code, or unrelated changes
- [ ] Breaking changes are described above
```

### `.github/ISSUE_TEMPLATE/bug_report.yml`

```yaml
name: Bug report
description: Report something that is not working
labels: [bug, needs-triage]
body:
  - type: textarea
    id: what-happened
    attributes:
      label: What happened?
      description: What did you expect instead?
    validations:
      required: true
  - type: textarea
    id: repro
    attributes:
      label: Steps to reproduce
      placeholder: "1. ...\n2. ...\n3. ..."
    validations:
      required: true
  - type: input
    id: version
    attributes:
      label: Version / commit
    validations:
      required: true
  - type: textarea
    id: env
    attributes:
      label: Environment (OS, runtime, browser)
  - type: textarea
    id: logs
    attributes:
      label: Logs or screenshots
      render: shell
```

### `.github/ISSUE_TEMPLATE/feature_request.yml`

```yaml
name: Feature request
description: Suggest an idea
labels: [feature, needs-triage]
body:
  - type: textarea
    id: problem
    attributes:
      label: What problem are you trying to solve?
    validations:
      required: true
  - type: textarea
    id: proposal
    attributes:
      label: Proposed solution
  - type: textarea
    id: alternatives
    attributes:
      label: Alternatives considered
```

### `CONTRIBUTING.md` skeleton

```markdown
# Contributing

## Setup
<install, run, test commands>

## Workflow
1. Fork (external) or branch (internal) from `main`: `feature/<short-name>`
2. Make small, atomic commits using Conventional Commits
3. Run `<lint>` and `<test>` locally
4. Open a PR using the template; link the issue
5. Address review feedback; maintainers squash-merge

## Commit style
`type(scope): imperative summary` (feat, fix, docs, refactor, test, build, ci, chore)

## Reporting bugs / security issues
Use the issue templates. For vulnerabilities, follow SECURITY.md.
```

### `SECURITY.md` skeleton

```markdown
# Security Policy

## Supported versions
| Version | Supported |
|---|---|
| 2.x | yes |
| 1.x | security fixes only |

## Reporting a vulnerability
Please do not open a public issue. Use GitHub's "Report a vulnerability" (Security tab)
or email security@example.com. Expect an acknowledgement within 3 business days.
```

### Husky + commitlint quick start (Node projects)

```bash
npm i -D husky @commitlint/cli @commitlint/config-conventional
echo "export default { extends: ['@commitlint/config-conventional'] };" > commitlint.config.js
npx husky init
echo 'npx --no -- commitlint --edit "$1"' > .husky/commit-msg
echo 'npm run lint && npm test' > .husky/pre-commit
```

### `pre-commit` (Python) with secret scanning

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.x.x           # pin a released version
    hooks:
      - id: gitleaks
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.x.x
    hooks:
      - id: check-added-large-files
      - id: end-of-file-fixer
      - id: trailing-whitespace
      - id: check-merge-conflict
```

Install with `pip install pre-commit && pre-commit install --install-hooks`.

---

## 26. Decision guides and checklists

### "Should I merge or rebase?"

```
Is the branch shared (others pushed to it or based work on it)?
  yes -> MERGE. Never rewrite it.
  no  -> Is it already pushed / in an open PR?
           yes -> rebase is OK, then push --force-with-lease; tell reviewers.
           no  -> rebase freely to tidy history.
```

### "How do I undo this?"

```
Not committed yet?       -> restore / restore --staged / stash
Committed, not pushed?   -> reset --soft/mixed (keep work) or amend
Pushed to shared branch? -> revert (new inverse commit)
Pushed to my own branch, nobody else uses it? -> reset + push --force-with-lease
Think I lost something?  -> git reflog first, then branch the lost SHA
```

### Pre-push checklist

- [ ] `git status` clean of surprises; on the right branch.
- [ ] `git diff origin/main...HEAD` reviewed.
- [ ] Tests, lint, build pass.
- [ ] No secrets, large files, or debug code.
- [ ] Commit messages follow convention; commits are atomic.
- [ ] Rebased/merged with latest `main`.

### Pre-merge checklist (reviewer/maintainer)

- [ ] CI green, required reviews done, conversations resolved.
- [ ] PR title is a good Conventional Commit (squash).
- [ ] Linked issue will close; breaking changes documented.
- [ ] Docs and changelog updated.
- [ ] Nothing unexpected in the file list.

### New-repo setup checklist

- [ ] README, LICENSE, `.gitignore`, `.gitattributes`
- [ ] Default branch `main`, protected (PR + checks + no force push)
- [ ] Squash merge enabled, delete branch on merge on
- [ ] CI workflow with least-privilege permissions and pinned actions
- [ ] Dependabot, secret scanning, push protection, CodeQL
- [ ] PR and issue templates, CODEOWNERS, CONTRIBUTING, SECURITY
- [ ] Commit convention + commitlint/pre-commit hooks
- [ ] Release process documented (SemVer, tags, changelog)

---

## 27. Quick command index

```bash
# See
git status -sb | git diff | git diff --staged | git log --oneline --graph --all | git show SHA | git blame FILE
# Save
git add -p | git commit -m "type(scope): msg" | git commit --fixup SHA | git commit --amend (unpushed only)
# Branch
git switch -c NAME | git switch - | git branch -d NAME | git branch -vv | git fetch --prune
# Sync
git fetch | git pull --ff-only | git pull --rebase | git rebase origin/main | git merge origin/main
# Share
git push -u origin HEAD | git push --force-with-lease (own branch only)
# Undo
git restore FILE | git restore --staged FILE | git reset --soft HEAD~1 | git revert SHA | git reflog | git reset --hard ORIG_HEAD
# Shelve / parallel
git stash push -m MSG | git stash pop | git worktree add ../dir -b NAME
# Find
git log -S"text" | git bisect start/good/bad/reset | git grep "text"
# Clean
git clean -nd (dry run first) | git gc | git filter-repo (history surgery, fresh clone)
# GitHub
gh pr create --fill | gh pr checks --watch | gh pr merge --squash --delete-branch | gh run view --log-failed | gh release create TAG --generate-notes
```

---

## 28. How to apply this skill (instructions for the agent)

1. Identify the task category (commit, branch, conflict, undo, PR, CI, security, release, CLI, setup).
2. Run read-only inspection commands first to establish the current state.
3. Check the operating rules in section 2. If the task needs a Tier 1 or Tier 2 action, stop and ask, stating the exact command and its effect.
4. Prefer the safest reversible method (section 13). Create a backup branch before any history surgery.
5. Explain what you are about to do and why in one or two sentences, run it, then verify (`git status`, `git log --oneline -5`, `gh pr view`).
6. When the user's situation is ambiguous (shared vs unshared branch, pushed vs unpushed, which merge method), ask one clear question rather than guessing.
7. For repository policy questions that may change (GitHub features, plan limits, API shapes, action versions), check the current GitHub documentation instead of relying on memory.

---

## References

- Agent Skills format and Antigravity skill locations: Google Antigravity codelab "Authoring Google Antigravity Skills"
- Conventional Commits 1.0.0: https://www.conventionalcommits.org/en/v1.0.0/
- Pro Git book (rerere, rewriting history, worktrees): https://git-scm.com/book
- GitHub Docs: secure use of GitHub Actions, rulesets and branch protection, commit signature verification, GitHub CLI manual (https://cli.github.com/manual/)
- Recommended Git configuration drawn from published settings used by Git core developers and widely shared community lists
