"""Tests for the public ``/api/health`` endpoint and legacy ``/health`` alias."""

from __future__ import annotations


def test_api_health_returns_ok(client):
    """GET /api/health returns 200 with {"status": "ok"}."""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_legacy_health_still_works(client):
    """GET /health (legacy) returns 200 with the same shape.

    Backward compatibility for Phase 1 tests and any existing deployment
    scripts that probe the un-prefixed endpoint.
    """
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
