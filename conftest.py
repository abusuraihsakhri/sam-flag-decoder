"""
Pytest configuration for Sam Flag Decoder.
Sets up required environment variables before test collection.
"""
import os

# Set default audit secret key for test environment
# This must be set before agents.base is imported (it initializes the global audit logger)
os.environ.setdefault("AUDIT_SECRET_KEY", "pytest-test-audit-secret-key")
