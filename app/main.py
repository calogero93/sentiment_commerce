"""API REST per il modello di Sentiment Analysis.

    POST /predict  — analizza una recensione
    GET  /metrics  — metriche in formato Prometheus
    GET  /health   — stato del servizio (healthcheck Docker)
"""

import logging
import time
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, HTTPException, Request, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from pydantic import BaseModel, Field, field_validator

from app.model import CONFIDENCE_THRESHOLD, service

logging.basicConfig(level="INFO", format="%(asctime)s %(levelname)-8s %(message)s")
logger = logging.getLogger(__name__)

# --- Metriche ---------------------------------------------------------------
# CPU e memoria non sono definite qui: prometheus_client registra da solo il
# ProcessCollector, che espone process_cpu_seconds_total e
# process_resident_memory_bytes.

richieste = Counter(
    "http_requests_total", "Richieste HTTP ricevute.", ["endpoint", "status_code"]
)
latenza = Histogram(
    "http_request_duration_seconds",
    "Tempo di risposta delle richieste HTTP.",
    ["endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
)
predizioni = Counter(
    "predictions_total", "Predizioni completate, per etichetta.", ["sentiment"]
)
errori = Counter(
    "prediction_errors_total", "Errori di predizione, per tipo.", ["error_type"]
)
modello_caricato = Gauge("model_loaded", "1 se il modello è in memoria, 0 altrimenti.")



class PredictRequest(BaseModel):
    review: str

    @field_validator("review")
    @classmethod
    def non_vuota(cls, v: str) -> str:
        """Rifiuta testi vuoti.
        """
        if not v.strip():
            raise ValueError("Il campo 'review' non può essere vuoto.")
        return v.strip()


class PredictResponse(BaseModel):
    sentiment: Literal["negative", "neutral", "positive"]
    confidence: float = Field(..., ge=0.0, le=1.0)




@asynccontextmanager
async def lifespan(app: FastAPI):
    """Carica il modello una volta sola all'avvio, non a ogni richiesta."""
    try:
        service.load()
        modello_caricato.set(1)
    except Exception:
        modello_caricato.set(0)
        logger.exception("Avvio senza modello: /predict risponderà 503.")
    yield


app = FastAPI(title="Sentiment Analysis API", version="1.0.0", lifespan=lifespan)


@app.middleware("http")
async def misura(request: Request, call_next):
    if request.url.path == "/metrics":
        return await call_next(request)

    inizio = time.perf_counter()
    risposta = await call_next(request)
    endpoint = request.url.path

    latenza.labels(endpoint=endpoint).observe(time.perf_counter() - inizio)
    richieste.labels(endpoint=endpoint, status_code=str(risposta.status_code)).inc()
    return risposta


@app.post("/predict", response_model=PredictResponse)
async def predict(payload: PredictRequest) -> PredictResponse:
    if not service.is_loaded:
        errori.labels(error_type="model_unavailable").inc()
        raise HTTPException(status_code=503, detail="Modello non disponibile.")

    try:
        risultato = service.predict(payload.review)
    except Exception as exc:
        errori.labels(error_type="inference").inc()
        logger.error("Errore di inferenza: %s", exc)
        raise HTTPException(status_code=500, detail="Errore durante l'analisi.")

    predizioni.labels(sentiment=risultato["sentiment"]).inc()
    if risultato["confidence"] < CONFIDENCE_THRESHOLD:
        logger.info("Predizione a bassa confidenza: %.4f", risultato["confidence"])

    return PredictResponse(**{k: risultato[k] for k in ("sentiment", "confidence")})


@app.get("/metrics")
async def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok" if service.is_loaded else "degraded",
        "model_loaded": service.is_loaded,
    }