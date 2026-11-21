"""Tests for the paper endpoints. Run from my_cosmos/backend:  python -m pytest -q"""
import sys
from pathlib import Path

from fastapi.testclient import TestClient  # pyright: ignore[reportMissingImports]

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app  # pyright: ignore[reportMissingImports]

client = TestClient(app)


def test_health():
    assert client.get("/health").json()["status"] == "ok"


def test_stats_match_the_corpus():
    s = client.get("/stats").json()
    assert s["papers"] == 1500
    assert s["year_from"] <= s["year_to"]
    assert s["synthetic"] is True  # demo data must say so


def test_filters_really_filter():
    r = client.get("/papers", params={"country": "India", "topic": "Computer Vision"}).json()
    assert r["total"] > 0
    for p in r["items"]:
        assert p["country"] == "India"
        assert "Computer Vision" in p["derived"]["topics"]


def test_unknown_paper_is_404():
    assert client.get("/papers/does-not-exist").status_code == 404
