"""
Servizio di Sentiment Analysis.
"""

import logging
import os
import pickle
from pathlib import Path

logger = logging.getLogger(__name__)

MODEL_PATH = os.getenv("MODEL_PATH", "models/sentiment_analysis_model.pkl")
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.50"))



class SentimentService:
    """Wrapper attorno alla pipeline serializzata."""

    def __init__(self, model_path: str = MODEL_PATH) -> None:
        self.model_path = Path(model_path)
        self.pipeline = None
        self.labels: tuple = ()

    def load(self) -> None:
        """Carica e valida il modello.

        La validazione avviene all'avvio
        """
        if not self.model_path.exists():
            raise Exception(f"Modello non trovato: {self.model_path}")

        try:
            with self.model_path.open("rb") as f:
                pipeline = pickle.load(f)
        except Exception as exc:
            raise Exception(f"Deserializzazione fallita: {exc}") from exc

        etichette = tuple(str(c) for c in pipeline.classes_)

        self.pipeline = pipeline
        self.labels = etichette
        logger.info("Modello caricato da %s — classi: %s", self.model_path, etichette)

    @property
    def is_loaded(self) -> bool:
        return self.pipeline is not None

    def predict(self, review: str) -> dict:
        """Analizza una recensione e restituisce etichetta e confidenza.
        """
        if self.pipeline is None:
            raise Exception("Modello non caricato.")

        testo = review.strip()
        probabilita = self.pipeline.predict_proba([testo])[0]
        indice = int(probabilita.argmax())

        return {
            "sentiment": self.labels[indice],
            "confidence": round(float(probabilita[indice]), 4)
        }


service = SentimentService()