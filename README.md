# Sentiment Analysis API

Servizio REST per l'analisi del sentimento delle recensioni di un e-commerce, con
pipeline CI/CD su Jenkins e monitoraggio via Prometheus e Grafana.

Il modello classifica un testo in inglese come `negative`, `neutral` o `positive`
restituendo la probabilità associata alla classe prevista.

---

## Requisiti

- Docker e Docker Compose
- [uv](https://docs.astral.sh/uv/) per lo sviluppo in locale
- Jenkins con Docker disponibile sull'agente, per la pipeline

---

## Avvio

### Con Docker Compose (API + Prometheus + Grafana)

```bash
docker compose up -d --build
```

| Servizio   | Indirizzo               | Credenziali   |
|------------|-------------------------|---------------|
| API        | http://localhost:8000   | —             |
| Documentazione API | http://localhost:8000/docs | —      |
| Prometheus | http://localhost:9090   | —             |
| Grafana    | http://localhost:3000   | admin / admin |

La dashboard Grafana e la sorgente dati sono configurate automaticamente
tramite provisioning: non serve alcun passaggio manuale.

Per fermare tutto (`-v` cancella anche i dati storici di Prometheus e Grafana):

```bash
docker compose down
```

### Solo l'API, con Docker

```bash
docker build -t sentiment-api .
docker run -d --name sentiment-api -p 8000:8000 sentiment-api
```

### In locale, con uv

```bash
uv sync
uv run uvicorn app.main:app --port 8000 --reload
```

---

## Uso dell'API

### `POST /predict`

```bash
curl -X POST http://localhost:8000/predict \
  -H 'Content-Type: application/json' \
  -d '{"review": "This product is amazing! I love it."}'
```

```json
{ "sentiment": "positive", "confidence": 0.5683 }
```

Risposte di errore:

| Codice | Quando                                              |
|--------|-----------------------------------------------------|
| 422    | Campo `review` mancante, vuoto o di tipo errato      |
| 500    | Errore imprevisto durante l'inferenza                |

### `GET /metrics`

Espone le metriche nel formato testuale letto da Prometheus.

### `GET /health`

Stato del servizio. Usato dallo `HEALTHCHECK` del container e dalla pipeline.

```json
{ "status": "ok", "model_loaded": true }
```

---

## Struttura del progetto

```
app/
  main.py           API FastAPI: endpoint, validazione, metriche
  model.py          Caricamento del modello e logica di predizione
models/
  sentiment_analysis_model.pkl
tests/
  unit/             Test del modello, senza server
  integration/      Test dell'API in esecuzione
monitoring/
  prometheus.yml    Configurazione dello scraping
  grafana/          Provisioning di sorgente dati e dashboard
Dockerfile          Immagine dell'API
docker-compose.yml  Stack completo con Prometheus e Grafana
Jenkinsfile         Pipeline CI/CD
pyproject.toml      Dipendenze e configurazione di pytest
uv.lock             Versioni esatte, da tenere sotto controllo di versione
```

---

## Scelte progettuali

Ho deciso di dividere ciò che riguarda il modello dal server e di metterli in due
file separati. Questo permette con semplicità di cambiare modello, e permette
anche di usare altri framework di machine learning in modo del tutto trasparente
per il server, a patto di rispettare l'interfaccia della classe con i metodi
`load` e `predict`. In più rende la logica di predizione testabile senza dover
avviare un server HTTP, ed è proprio questo che mi permette di distinguere gli
unit test dai test di integrazione.
 
L'architettura è volutamente minimale. Il modello è già addestrato e
l'applicazione si limita a ricevere una richiesta e restituire una previsione:
la parte impegnativa del progetto non è il codice dell'API, ma la pipeline e il
monitoraggio.
 
Il modello lo carico una volta sola all'avvio, dentro il `lifespan`, e non a
ogni richiesta. Deserializzare un pickle è un costo che ha senso pagare allo
startup, non a ogni chiamata. Se il caricamento fallisce faccio uscire il
processo, così l'errore salta fuori subito invece di presentarsi alla prima
richiesta di un utente.
 
Rifiuto le recensioni vuote con un 422. Senza quel controllo il modello
riceverebbe un vettore di soli zeri e restituirebbe comunque un'etichetta, e
avrei una risposta che sembra valida ma non lo è.
 
I nomi delle metriche li considero un contratto: la dashboard di Grafana li usa
direttamente, quindi cambiarli significa rompere i pannelli.
 
Dentro il codice ci sono dei commenti per alcune scelte più mirate.

---

## Test

```bash
# Unit test: girano da soli
uv run pytest tests/unit -v

# Test di integrazione: richiedono l'API già avviata
uv run uvicorn app.main:app --port 8000   # in un altro terminale
uv run pytest tests/integration -v
```

Dentro Docker, come fa la pipeline:

```bash
docker run --rm sentiment-api python -m pytest tests/unit -v

docker run -d --name test-app sentiment-api
sleep 10
docker exec test-app python -m pytest tests/integration -v
docker rm -f test-app
```

L'indirizzo dell'API nei test di integrazione si configura con la variabile
`API_URL` (default `http://localhost:8000`).

---

## Pipeline CI/CD

Il `Jenkinsfile` definisce quattro stage:

Non userò il webhook in queso caso ma il poolSCM per evitare di esporre jenkins, perchè github in quel caso dovrebbe chiamarlo

1. **Build** — costruisce l'immagine Docker. L'immagine si costruisce *prima* dei
   test, così quella che va in produzione è esattamente quella testata.
2. **Unit test** — in un container temporaneo, senza dipendenze esterne.
3. **Test di integrazione** — avvia l'API in un container ed esegue i test al suo
   interno, interrogandola via HTTP.
4. **Deploy** — sostituisce il container in esecuzione e verifica `/health`.

Al termine, il blocco `post` invia una notifica via email in caso di successo o
di fallimento.

Le notifiche sono implementate ma non attive in locale: Jenkins prova a
consegnare su un server SMTP che nell'ambiente di sviluppo non esiste. La
chiamata è racchiusa in un `catchError`, quindi una notifica non recapitata non
altera l'esito della build.

### Trigger automatico

La pipeline parte a ogni commit tramite il webhook di GitHub. Configurazione:

1. Nel job Jenkins, spuntare **"GitHub hook trigger for GITScm polling"**.
   Il blocco `triggers` la attiva da solo, ma solo dopo la prima build manuale.
2. Su GitHub: *Settings → Webhooks → Add webhook*, con Payload URL
   `http://INDIRIZZO_JENKINS:8080/github-webhook/` (la barra finale è
   necessaria), content type `application/json`, evento *push*.

GitHub deve poter raggiungere Jenkins da internet. Se Jenkins gira in locale,
esporlo con `ngrok http 8080` e usare l'URL pubblico generato.

---

## Monitoraggio

Prometheus interroga `/metrics` ogni 10 secondi. Metriche esposte:

| Metrica                          | Descrizione                                 |
|----------------------------------|---------------------------------------------|
| `http_request_duration_seconds`  | Tempo di risposta (istogramma)              |
| `http_requests_total`            | Richieste per endpoint e codice di stato    |
| `predictions_total`              | Predizioni per etichetta prevista           |
| `prediction_errors_total`        | Errori di predizione per tipo               |
| `model_loaded`                   | 1 se il modello è in memoria                |
| `process_cpu_seconds_total`      | CPU utilizzata                              |
| `process_resident_memory_bytes`  | Memoria occupata                            |

Le ultime due sono registrate automaticamente da `prometheus_client` tramite il
`ProcessCollector`.

La dashboard Grafana mostra tempi di risposta (p50 e p95), richieste al secondo
per codice di stato, distribuzione delle predizioni, errori, stato del modello e
utilizzo delle risorse.

Se un pannello resta vuoto, controllare prima http://localhost:9090/targets, che
indica se Prometheus sta raggiungendo l'API.
