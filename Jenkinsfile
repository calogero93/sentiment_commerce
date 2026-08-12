
Claude ha terminato la risposta
Abbiamo quello che ci serve per fare questo

Pipeline CI/CD con Jenkins

Trigger automatico: La pipeline si attiva quando viene effettuato un commit nel repository.
Build: Compilazione del modello e creazione dell'immagine Docker.
Test: Esecuzione di test automatizzati per validare le previsioni del modello.
Deploy: Pubblicazione del modello su un ambiente di produzione o staging

Ha pensato per 12s
Ha pensato per 12s
Quasi. Manca un pezzo: le cartelle tests/ sono ancora vuote, quindi lo stage "Test" non avrebbe niente da eseguire. Scrivo prima i test, poi il Jenkinsfile che li richiama.


Eseguiti 5 comandi, creati 3 file, file modificato · 1 nota
Eseguiti 5 comandi, creati 3 file, file modificato · 1 nota
I test hanno trovato un bug reale mentre li scrivevo: out_of_vocabulary restituiva un np.bool_ invece di un bool Python — cosa che si sarebbe serializzata in modo imprevedibile in JSON. Ho corretto il servizio, non il test.

Eseguiti davvero: 18 unit test + 14 di integrazione, tutti verdi. Gli unit girano diretti sul servizio; per gli altri ho avviato uvicorn su una porta locale e li ho lanciati contro l'API viva.

Sui quattro punti della traccia:

Trigger — githubPush() per il webhook, più pollSCM('H/2 * * * *') come rete di sicurezza. Il webhook è immediato ma fragile: se Jenkins sta dietro NAT o il tunnel cade, il commit passa inosservato. Con il polling la pipeline parte comunque entro due minuti.

Build — nota terminologica che vale la pena avere chiara in sede di consegna: la traccia dice "compilazione del modello", ma qui non si compila nulla. Il .pkl è già addestrato e versionato nel repo; il Dockerfile lo copia dentro l'immagine. Lo stage costruisce l'immagine e basta. Se qualcuno si aspetta un training in pipeline, va detto esplicitamente che il modello è fornito pre-addestrato.

Test — l'immagine si costruisce prima dei test, così quella rilasciata è esattamente quella testata. Gli unit girano in un container usa-e-getta senza rete. Gli integration avviano l'API in un container e la interrogano da un secondo container sulla stessa rete, passando API_URL — che è precisamente come i test sono scritti. I report JUnit vengono estratti con docker cp anche quando i test falliscono.

Deploy — solo su main, docker run con --restart unless-stopped, e smoke test che non si limita a /health: fa una predizione reale e verifica che esca "sentiment":"positive". Se fallisce, rollback automatico sull'immagine precedente.

Il test che secondo me vale di più è test_il_contatore_delle_predizioni_si_incrementa: legge /metrics, fa una predizione, rilegge e verifica l'incremento. Lega API e monitoraggio, e senza di esso le metriche potrebbero esistere e restare ferme a zero senza che nessuno se ne accorga.

Restano fuori solo docker-compose.yml con Prometheus e Grafana, e il README.


Jenkinsfile
 

Test model
PY 

Test api
PY 

Pytest
INI 

Model
PY 
Non mi devi dare un file di produzione super dettagliato e complicato, considera che si suppone che io non sappia granche di jenkins anche i test non aggiungere roba complicata mantieni semplice


Ha pensato per 12s
Ha pensato per 12s
Hai ragione, semplifico entrambi.


Eseguiti 3 comandi, file creato, file letto
Eseguiti 3 comandi, file creato, file letto
Jenkinsfile da 102 righe (di cui metà commenti), quattro stage lineari, zero funzioni Groovy.

Cosa ho tolto: rollback automatico, retry, la funzione notifica(), emailext con HTML, i report JUnit con docker cp, le reti Docker temporanee, archiveArtifacts, cleanWs, il when { branch 'main' }. Sono cose sensate in produzione ma da spiegare, e tu non le devi difendere.

Semplificazione che vale la pena notare: prima creavo una rete Docker e due container che si parlavano. Ora l'API gira in un container e i test partono dentro lo stesso container con docker exec. Il risultato è identico — le chiamate passano davvero per HTTP su localhost:8000 — ma sono tre comandi invece di sei, e non c'è niente da spiegare sul networking Docker.

L'unica cosa che ho tenuto e che potrebbe sembrare superflua è il blocco post { always { docker rm -f test-app } } sullo stage di integrazione. Serve: se i test falliscono, il container resta appeso e la build successiva si pianta perché il nome è già occupato. È il classico inceppamento da principiante, e vale la riga in più.

Test ridotti a 7 + 7, tutti eseguiti e verdi. Gli unit: il modello si carica, le etichette sono le tre attese, la risposta ha i campi giusti, tre predizioni su frasi evidenti, invarianza alle maiuscole. Gli integration: /health, predizione positiva, predizione negativa, tre casi di input non valido che devono dare 422, e /metrics che espone le tre categorie richieste dalla traccia. Ho tolto il test sull'incremento del contatore — era il più interessante ma anche il più difficile da spiegare a voce.

Una cosa da sapere per quando lo consegni: pollSCM fa partire la pipeline entro due minuti dal commit. È il modo più semplice e funziona ovunque, anche con Jenkins in locale. Il webhook di GitHub sarebbe istantaneo ma richiede che Jenkins sia raggiungibile da internet, e su una macchina di sviluppo di solito non lo è.

Restano docker-compose.yml con Prometheus e Grafana, e il README.


Jenkinsfile
 

Test model
PY 

Test api
PY 






Claude è un'AI e può commettere errori. Verifica le risposte.
// =============================================================================
//  Jenkinsfile — Sentiment Analysis API
//  Build immagine -> Unit test -> Test di integrazione -> Deploy -> Notifica
// =============================================================================
 
pipeline {
 
    // Su quale macchina girare. 'any' = un qualsiasi nodo Jenkins disponibile.
    agent any
 
    // La pipeline parte da sola: Jenkins controlla il repository ogni 2 minuti
    // e se trova un commit nuovo avvia la build.
    triggers {
        pollSCM('H/2 * * * *')
    }
 
    // Variabili riutilizzate negli stage sottostanti.
    environment {
        IMAGE          = "sentiment-api:${env.BUILD_NUMBER}"
        CONTAINER_NAME = 'sentiment-api'
        PORTA          = '8000'
    }
 
    stages {
 
        // --- 1. Build ----------------------------------------------------
        // Costruisce l'immagine Docker. Il modello .pkl e' gia' nel
        // repository e il Dockerfile lo copia dentro l'immagine.
        stage('Build') {
            steps {
                sh 'docker build -t ${IMAGE} .'
            }
        }
 
        // --- 2. Unit test -------------------------------------------------
        // Girano in un container temporaneo (--rm lo cancella da solo).
        // Se un test fallisce il comando esce con errore e la pipeline si
        // ferma qui: nessun deploy.
        stage('Unit test') {
            steps {
                sh 'docker run --rm ${IMAGE} python -m pytest tests/unit -v'
            }
        }
 
        // --- 3. Test di integrazione ---------------------------------------
        // Avvia l'API in un container e lancia i test al suo interno, cosi'
        // l'API viene interrogata davvero via HTTP.
        stage('Test di integrazione') {
            steps {
                sh '''
                    docker run -d --name test-app ${IMAGE}
                    sleep 10
                    docker exec test-app python -m pytest tests/integration -v
                '''
            }
            post {
                // Il container va rimosso sia in caso di successo che di
                // errore, altrimenti la build successiva trova il nome
                // gia' occupato e fallisce.
                always {
                    sh 'docker rm -f test-app || true'
                }
            }
        }
 
        // --- 4. Deploy ------------------------------------------------------
        // Sostituisce il container in esecuzione con la nuova immagine.
        stage('Deploy') {
            steps {
                sh '''
                    docker rm -f ${CONTAINER_NAME} || true
 
                    docker run -d \
                        --name ${CONTAINER_NAME} \
                        --restart unless-stopped \
                        -p ${PORTA}:8000 \
                        ${IMAGE}
 
                    sleep 5
                    curl -f http://localhost:${PORTA}/health
                '''
            }
        }
    }
 
    // --- Notifiche ---------------------------------------------------------
    // Il blocco post viene eseguito alla fine, in base all'esito.
    post {
        success {
            echo "Pipeline completata: immagine ${IMAGE} rilasciata."
            mail to: 'team@example.com',
                 subject: "OK - ${env.JOB_NAME} build #${env.BUILD_NUMBER}",
                 body: "La pipeline e' andata a buon fine.\n${env.BUILD_URL}"
        }
        failure {
            echo 'Pipeline fallita.'
            mail to: 'team@example.com',
                 subject: "ERRORE - ${env.JOB_NAME} build #${env.BUILD_NUMBER}",
                 body: "La pipeline e' fallita. Dettagli:\n${env.BUILD_URL}"
        }
    }
}
 
