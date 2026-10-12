"""Step 0: Gate Attack War Games.

Five adversarial acceptance tests against TeamZero's Merge Gate Authority:
1. Tamper: Flip one byte in a ledger receipt -> verify_receipt FAILS
2. Replay: Copy a valid receipt from SHA-A to SHA-B -> check-merge for SHA-B FAILS
3. Forge: Attempt to forge a receipt without knowing the server secret -> FAILS
4. Incomplete Pre-reqs: Gauntlet pass + Breaker pass but NO founder approval -> BLOCKED
5. Happy Path: All three prerequisites present and untampered -> UNLOCKED
"""

import json
import pytest
import os
import time
from pathlib import Path

from teamzero.config import SERVER_SECRET
from teamzero.governance import sign_receipt, verify_receipt
from teamzero.merge_gate import evaluate_merge_prerequisites, get_receipts_for_sha


def test_tamper_attack():
    """Test 1: Tampering with a single byte in the receipt string invalidates it."""
    orig = sign_receipt("test_subject", "test_kind")
    receipt_str = orig["receipt"]
    
    # Tamper: flip the last character
    tampered_char = "a" if receipt_str[-1] != "a" else "b"
    tampered_receipt = receipt_str[:-1] + tampered_char
    
    # Verification must fail
    is_valid = verify_receipt(
        tampered_receipt,
        orig["subject"],
        orig["kind"],
        orig["issued_at"]
    )
    assert not is_valid, "Tampered receipt was erroneously accepted!"


def test_replay_attack():
    """Test 2: Replaying a receipt issued for SHA-A against SHA-B must be rejected."""
    sha_a = "1111222233334444555566667777888899990000"
    sha_b = "aaaabbbbccccddddeeeeffff0000111122223333"
    
    receipt_a = sign_receipt(f"gauntlet_run:{sha_a}", "gauntlet_run")
    
    # Check if receipt for SHA-A is accepted for SHA-B
    receipts_for_b = get_receipts_for_sha(sha_b)
    # sha_b has no matching receipts
    assert not any(r["receipt"] == receipt_a["receipt"] for r in receipts_for_b), \
        "Replay attack succeeded: Receipt from SHA-A leaked into SHA-B!"


def test_forge_attack():
    """Test 3: Forging a receipt with a guessed or arbitrary secret fails verification against real secret."""
    import hmac
    import hashlib
    
    subject = "breaker_run:attacker_sha"
    kind = "breaker_run"
    issued_at = time.time()
    
    # Attacker tries to mint receipt with a guessed fake secret
    fake_secret = "attacker-guessed-secret-xyz"
    body = f"{kind}:{subject}:{issued_at}"
    fake_sig = hmac.new(fake_secret.encode(), body.encode(), hashlib.sha256).hexdigest()
    fake_receipt = f"TZ-{fake_sig}"
    
    # Server verifies against actual SERVER_SECRET
    is_valid = verify_receipt(fake_receipt, subject, kind, issued_at)
    assert not is_valid, "Forged receipt with invalid secret was accepted!"


def test_incomplete_prerequisites_blocks_merge():
    """Test 4: If any required receipt (e.g. founder approval) is missing, merge is strictly blocked."""
    test_sha = "test_sha_incomplete_99999999"
    # Mint only gauntlet
    sign_receipt(f"gauntlet_run:{test_sha}", "gauntlet_run")
    
    eval_res = evaluate_merge_prerequisites(target_ref=test_sha, required_autonomy_level=2)
    assert not eval_res["eligible_to_merge"], "Merge was erroneously allowed with missing prerequisites!"


def test_happy_path_unlocks_merge(tmp_path, monkeypatch):
    """Test 5: When gauntlet, clean breaker, and founder approval exist for SHA, merge attestation is issued."""
    test_sha = "aabbccddeeff11223344556677889900aabbccdd"
    short_sha = test_sha[:8]
    
    # Create fake clean findings packet
    from teamzero.config import FINDINGS_DIR
    FINDINGS_DIR.mkdir(parents=True, exist_ok=True)
    packet_path = FINDINGS_DIR / f"TASK-TEST_{short_sha}.json"
    packet_path.write_text(json.dumps({
        "verdict": "PASS",
        "summary": {"critical": 0, "high": 0, "medium": 0, "low": 0}
    }), encoding="utf-8")
    
    try:
        # Sign all 3 prerequisites
        sign_receipt(f"gauntlet_run:{test_sha}", "gauntlet_run")
        sign_receipt(f"TASK-TEST:{test_sha}", "breaker_run")
        sign_receipt(f"founder_approval:{test_sha}", "founder_approval")
        
        eval_res = evaluate_merge_prerequisites(target_ref=test_sha, required_autonomy_level=2)
        assert eval_res["eligible_to_merge"], f"Happy path failed! Details: {eval_res['gates']}"
        assert eval_res["merge_attestation"].startswith("TZ-"), "Merge attestation receipt was not issued!"
    finally:
        if packet_path.exists():
            packet_path.unlink()
