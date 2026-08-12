"""Unit test: verificano il modello senza avviare il server."""

import pytest

from app.model import SentimentService

ETICHETTE = {"negative", "neutral", "positive"}


@pytest.fixture(scope="module")
def servizio():
    """Carica il modello una volta sola per tutti i test."""
    s = SentimentService()
    s.load()
    return s


def test_il_modello_si_carica(servizio):
    assert servizio.is_loaded


def test_le_etichette_sono_corrette(servizio):
    assert set(servizio.labels) == ETICHETTE


def test_la_risposta_ha_i_campi_giusti(servizio):
    risultato = servizio.predict("This product is amazing!")
    assert risultato["sentiment"] in ETICHETTE
    assert 0.0 <= risultato["confidence"] <= 1.0


@pytest.mark.parametrize(
    "recensione, atteso",
    [
        ("This product is amazing! I love it.", "positive"),
        ("Terrible quality, complete waste of money.", "negative"),
        ("The movie was okay, not great but not bad either.", "neutral"),
    ],
)
def test_predizioni_corrette(servizio, recensione, atteso):
    """Su frasi evidenti il modello deve dare la risposta giusta."""
    assert servizio.predict(recensione)["sentiment"] == atteso


def test_le_maiuscole_non_cambiano_il_risultato(servizio):
    frase = "This product is amazing! I love it."
    assert (
        servizio.predict(frase)["sentiment"]
        == servizio.predict(frase.upper())["sentiment"]
    )