pipeline {

    agent any

    // La pipeline parte da sola: Jenkins controlla il repository ogni 2 minuti
    // e se trova un commit nuovo avvia la build.
    triggers {
        pollSCM('H/2 * * * *')
    }

    // Variabili riutilizzate negli stage sottostanti.
    environment {
        IMAGE          = "sentiment-api:${env.BUILD_NUMBER}"
        CONTAINER_NAME = 'sentiment-api-deploy'
        PORTA          = '8001'
    }

    stages {
        // Costruisce l'immagine Docker. Il modello .pkl e' gia' nel
        // repository e il Dockerfile lo copia dentro l'immagine.
        stage('Build') {
            steps {
                sh 'docker build -t ${IMAGE} .'
            }
        }

        // Girano in un container temporaneo (--rm lo cancella da solo).
        // Se un test fallisce il comando esce con errore e la pipeline si
        // ferma qui: nessun deploy.
        stage('Unit test') {
            steps {
                sh 'docker run --rm ${IMAGE} python -m pytest tests/unit -v'
            }
        }

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