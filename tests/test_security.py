"""
Security-focused tests for Sam Flag Decoder.
"""
import os
import sys
from pathlib import Path

# Ensure audit key is set before importing agents
os.environ.setdefault("AUDIT_SECRET_KEY", "test-security-audit-key")

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from agents.base import (
    PHIGuard,
    AuditTrail,
    SecurityException,
    assert_no_phi,
)


class TestPHIGuard:
    """Tests for PHI outbound guard functionality."""

    def test_mrn_detection(self):
        with pytest.raises(SecurityException):
            PHIGuard.assert_no_phi("Patient MRN-12345678")

    def test_ssn_detection(self):
        with pytest.raises(SecurityException):
            PHIGuard.assert_no_phi("SSN: 123-45-6789")

    def test_phone_detection(self):
        with pytest.raises(SecurityException):
            PHIGuard.assert_no_phi("Call 555-123-4567")

    def test_email_detection(self):
        with pytest.raises(SecurityException):
            PHIGuard.assert_no_phi("Email: patient@example.com")

    def test_clean_text_passes(self):
        PHIGuard.assert_no_phi("Analytical specimen KEY-001 optimal")

    def test_none_input_passes(self):
        PHIGuard.assert_no_phi(None)

    def test_redact_phi(self):
        text = "Patient John Doe, MRN-12345"
        redacted = PHIGuard.redact_phi(text)
        assert "John Doe" not in redacted
        assert "MRN-12345" not in redacted
        assert "[REDACTED" in redacted


class TestAuditTrail:
    """Tests for HMAC-SHA256 audit trail."""

    def test_audit_trail_requires_key(self):
        original = os.environ.pop("AUDIT_SECRET_KEY", None)
        try:
            with pytest.raises(RuntimeError):
                AuditTrail()
        finally:
            if original:
                os.environ["AUDIT_SECRET_KEY"] = original

    def test_audit_trail_with_explicit_key(self):
        trail = AuditTrail(secret_key="test-key-123")
        entry = trail.log("test", "worker", "EVENT", {"data": "value"})
        assert "current_hash" in entry
        assert entry["prev_hash"] == "GENESIS_BLOCK_0000000000000000"

    def test_audit_chain_integrity(self):
        trail = AuditTrail(secret_key="test-key-456")
        trail.log("a", "worker", "E1", {"x": 1})
        trail.log("b", "worker", "E2", {"y": 2})
        trail.log("c", "worker", "E3", {"z": 3})
        assert trail.verify_integrity() is True

    def test_audit_chain_length(self):
        trail = AuditTrail(secret_key="test-key-789")
        for i in range(5):
            trail.log("actor", "tier", "EVENT", {"i": i})
        assert len(trail.get_trail()) == 5


def test_audit_tampering_detected():
    trail = AuditTrail(secret_key="test-signing-key")
    trail.log("actor", "tier", "EVENT", {"count": 1})
    trail.logs[0]["event_type"] = "FORGED_EVENT"
    assert trail.verify_integrity() is False


def test_audit_get_trail_returns_copy():
    trail = AuditTrail(secret_key="test-signing-key")
    trail.log("actor", "tier", "EVENT", {"count": 1})
    trail.get_trail()[0]["actor"] = "changed"
    assert trail.verify_integrity() is True
    assert trail.get_trail()[0]["actor"] == "actor"


def test_outbound_guard_checks_nested_payload_attributes():
    from agents.models import SystemTaskPayload
    from agents.supervisor import SystemSupervisor
    payload = SystemTaskPayload(task_id="t", target_identifier="key", primary_metric=1.0,
                                attributes={"email": "patient@example.com"})
    with pytest.raises(SecurityException):
        SystemSupervisor().process_task(payload)


def test_audit_log_endpoint_requires_read_key(monkeypatch):
    from fastapi import HTTPException
    from agents.api import api_audit_logs
    monkeypatch.delenv("AUDIT_LOG_READ_KEY", raising=False)
    with pytest.raises(HTTPException) as exc:
        api_audit_logs(x_audit_read_key="anything")
    assert exc.value.status_code == 403
    monkeypatch.setenv("AUDIT_LOG_READ_KEY", "another-independent-test-key")
    with pytest.raises(HTTPException):
        api_audit_logs(x_audit_read_key="wrong")
    assert api_audit_logs(x_audit_read_key="another-independent-test-key")["verified"] is True
