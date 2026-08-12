"""Test di integrazione: verificano l'API mentre è in esecuzione."""

import os

import pytest
import requests

API_URL = os.getenv("API_URL", "http://localhost:8000")


def test_health():
    r = requests.get(f"{API_URL}/health", timeout=5)
    assert r.status_code == 200
    assert r.json()["model_loaded"] is True


def test_predict_risponde_correttamente():
    """La risposta deve avere il formato richiesto dalla traccia."""
    r = requests.post(
        f"{API_URL}/predict",
        json={"review": "This product is amazing! I love it."},
        timeout=5,
    )
    assert r.status_code == 200
    assert r.json()["sentiment"] == "positive"
    assert 0.0 <= r.json()["confidence"] <= 1.0


def test_predict_recensione_negativa():
    r = requests.post(
        f"{API_URL}/predict",
        json={"review": "Terrible quality, complete waste of money."},
        timeout=5,
    )
    assert r.json()["sentiment"] == "negative"


@pytest.mark.parametrize("payload", [{}, {"review": ""}, {"review": "   "}])
def test_input_non_valido(payload):
    """Un input sbagliato deve dare 422, non un errore del server."""
    r = requests.post(f"{API_URL}/predict", json=payload, timeout=5)
    assert r.status_code == 422


def test_metrics_espone_le_metriche():
    r = requests.get(f"{API_URL}/metrics", timeout=5)
    assert r.status_code == 200
    assert "http_request_duration_seconds" in r.text   # tempi di risposta
    assert "prediction_errors_total" in r.text          # errori
    assert "process_cpu_seconds_total" in r.text        # CPU e memoria