import pytest
from pathlib import Path
import teamzero.config as tz_config

@pytest.fixture(autouse=True)
def isolate_test_ledgers(tmp_path, monkeypatch):
    """Isolates operational ledgers into tmp_path during test runs so git working tree remains clean."""
    test_ledger_dir = tmp_path / "ledger"
    test_ledger_dir.mkdir(parents=True, exist_ok=True)
    
    test_receipts = test_ledger_dir / "receipts.jsonl"
    test_trust = test_ledger_dir / "trust.jsonl"
    test_payroll = test_ledger_dir / "payroll.jsonl"
    
    # Pre-populate with existing records if original exists so baseline tests continue working
    if tz_config.RECEIPTS_LEDGER.exists():
        test_receipts.write_text(tz_config.RECEIPTS_LEDGER.read_text(encoding="utf-8"), encoding="utf-8")
    if tz_config.TRUST_LEDGER.exists():
        test_trust.write_text(tz_config.TRUST_LEDGER.read_text(encoding="utf-8"), encoding="utf-8")
    if tz_config.PAYROLL_LEDGER.exists():
        test_payroll.write_text(tz_config.PAYROLL_LEDGER.read_text(encoding="utf-8"), encoding="utf-8")
        
    monkeypatch.setattr(tz_config, "RECEIPTS_LEDGER", test_receipts)
    monkeypatch.setattr(tz_config, "TRUST_LEDGER", test_trust)
    monkeypatch.setattr(tz_config, "PAYROLL_LEDGER", test_payroll)
    
    # Also patch modules that imported these directly
    import teamzero.governance as tz_gov
    import teamzero.merge_gate as tz_mg
    monkeypatch.setattr(tz_gov, "RECEIPTS_LEDGER", test_receipts)
    monkeypatch.setattr(tz_gov, "TRUST_LEDGER", test_trust)
    monkeypatch.setattr(tz_gov, "PAYROLL_LEDGER", test_payroll)
    monkeypatch.setattr(tz_mg, "RECEIPTS_LEDGER", test_receipts)
    monkeypatch.setattr(tz_mg, "TRUST_LEDGER", test_trust)
