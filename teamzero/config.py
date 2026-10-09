"""Configuration and constants for TeamZero."""

import os
from pathlib import Path

# Paths
ROOT_DIR = Path(__file__).resolve().parent.parent
ORG_DIR = ROOT_DIR / ".teamzero"
MEMORY_DIR = ORG_DIR / "memory"
ADR_DIR = MEMORY_DIR / "adr"
MAP_DIR = MEMORY_DIR / "map"
SPECS_DIR = MEMORY_DIR / "specs"
TRAPS_DIR = MEMORY_DIR / "traps"
REDTEAM_DIR = ORG_DIR / "redteam"
FINDINGS_DIR = REDTEAM_DIR / "findings"
CAMPAIGNS_DIR = REDTEAM_DIR / "campaigns"
INBOX_DIR = ORG_DIR / "inbox"
ASKS_DIR = INBOX_DIR / "asks"
DECISIONS_DIR = INBOX_DIR / "decisions"
LEDGER_DIR = ORG_DIR / "ledger"
TRUST_LEDGER = LEDGER_DIR / "trust.jsonl"
PAYROLL_LEDGER = LEDGER_DIR / "payroll.jsonl"
RECEIPTS_LEDGER = LEDGER_DIR / "receipts.jsonl"
CONSTITUTION_FILE = ORG_DIR / "constitution.yaml"

import secrets

MINTKEY_FILE = ORG_DIR / ".mintkey"


def get_server_secret() -> str:
    """Retrieves the mint key:
    1. From TZ_SERVER_SECRET environment variable (mandatory in CI/production).
    2. From persistent local keyfile .teamzero/.mintkey (gitignored) for cross-process CLI consistency.
    3. Auto-generates once per developer repository if absent.
    """
    env_secret = os.environ.get("TZ_SERVER_SECRET")
    if env_secret:
        return env_secret.strip()

    if MINTKEY_FILE.exists():
        try:
            key = MINTKEY_FILE.read_text(encoding="utf-8").strip()
            if key:
                return key
        except Exception:
            pass

    key = secrets.token_hex(32)
    try:
        MINTKEY_FILE.parent.mkdir(parents=True, exist_ok=True)
        MINTKEY_FILE.write_text(key, encoding="utf-8")
        if sys.platform != "win32":
            os.chmod(MINTKEY_FILE, 0o600)
    except Exception:
        pass
    return key


SERVER_SECRET = get_server_secret()
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
PROBER_MODEL = os.environ.get("TZ_PROBER_MODEL", "meta-llama/llama-3.3-70b-instruct:free")
PROBER_BUDGET = 2500

# Poison and Injection Patterns (L2 Sentinel)
POISON_PATTERNS = [
    r"(?i)ignore (all )?(previous|prior) instructions",
    r"(?i)you are now|disregard (the )?above|new instructions",
    r"(?i)as an? (ai|assistant|agent|model)[,:]?\s*(you|please)",
    r"(?i)(curl|wget|nc|bash -c)\s+[^\n]*(https?://|base64|/dev/tcp)",
    r"(?i)eval\s*\(|exec\s*\(|__import__|subprocess\.",
    r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"][A-Za-z0-9_\-]{8,}",
    r"(?i)send|post|exfiltrate.{0,30}(env|secret|variable|token)",
    r"(?i)<!--\s*(ignore|note to (ai|agent|model|maintainer))",
    r"(?i)data:(text|application)/[^;]*;base64,[A-Za-z0-9+/=]{40,}",
]

PROTECTED_PATHS = [
    ".teamzero/constitution.yaml",
    ".teamzero/memory/adr/*",
    ".teamzero/memory/map/*",
    ".teamzero/ledger/*",
    ".github/workflows/*",
]
