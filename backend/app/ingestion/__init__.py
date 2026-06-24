"""Resilient ingestion layer: clients, validation, interpolation, and storage.

Every upstream is assumed unreliable and wrapped with timeout + retry/backoff +
circuit breaker + last-known-good cache (HL5). The ETL is idempotent and replayable;
raw pulls are immutable and all cleaning is downstream and reproducible.
"""
