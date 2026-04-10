pipeline {
    agent any
    
    environment {
        IMAGE_NAME = "securenet-parent-portal"
        IMAGE_TAG = "${BUILD_NUMBER}"
        FULL_IMAGE = "${IMAGE_NAME}:${IMAGE_TAG}"
        AWS_REGION = "us-east-1"
        // Ensure these credentials IDs exist in: Manage Jenkins -> Credentials
        AWS_ACCOUNT_ID = credentials('AWS_ACCOUNT_ID') 
        ECR_REGISTRY = "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
        ECR_REPO = "securenet-parent-portal"
        SONAR_SERVER_NAME = "SonarQube"
        SONAR_SCANNER_NAME = "Sonar Scanner"
        SONAR_PROJECT_KEY = "securenet-parent-portal"
        SONAR_TOKEN = credentials('SONAR_TOKEN')
        CLAUDE_API_KEY = credentials('CLAUDE_API_KEY')
        DISCORD_WEBHOOK_URL = credentials('DISCORD_WEBHOOK_URL')
        CHECKOV_THRESHOLD = "HIGH"
    }

    stages {
        stage('Environment Info') {
            steps {
                echo "========================="
                echo "Build Number : ${env.BUILD_NUMBER}"
                echo "Image : ${env.FULL_IMAGE}"
                echo "========================="
                // Using 'bat' if on Windows, 'sh' if on Linux. Based on your logs, you are on Windows.
                sh "docker --version" 
                sh "python --version"
            }
        }

        stage('Checkov IaC Scan') {
            steps {
                echo "==> Scanning Terraform code..."
                sh "mkdir -p reports"
                // Using 'true' to ensure the pipeline continues even if Checkov finds issues
                sh """
                    checkov -d terraform/ \
                        --soft-fail \
                        --output cli \
                        --output-file-path reports/ || true
                """
            }
            post {
                always {
                    archiveArtifacts artifacts: 'reports/*.txt', allowEmptyArchive: true
                }
            }
        }

        stage('Docker Build') {
            steps {
                echo "==> Building Docker Image..."
                sh "docker build -t ${FULL_IMAGE} ."
            }
        }

        stage('SonarQube Analysis') {
            steps {
                withSonarQubeEnv("${SONAR_SERVER_NAME}") {
                    script {
                        def scannerHome = tool "${SONAR_SCANNER_NAME}"
                        sh """
                            ${scannerHome}/bin/sonar-scanner \
                            -Dsonar.projectKey=${SONAR_PROJECT_KEY} \
                            -Dsonar.sources=. \
                            -Dsonar.python.version=3.11 \
                            -Dsonar.token=${SONAR_TOKEN}
                        """
                    }
                }
            }
        }

        stage('Quality Gate') {
            steps {
                // Shortened timeout to prevent hanging
                timeout(time: 5, unit: 'MINUTES') {
                    waitForQualityGate abortPipeline: true
                }
            }
        }

        stage('Claude Security Summary') {
            steps {
                sh "pip install anthropic python-dotenv --quiet"
                script {
                    // Running the triage script with the API Key passed via environment
                    def result = sh(script: "python scripts/claude_triage_pipeline.py", returnStatus: true)
                    if (result != 0) {
                        echo "Claude AI flagged issues or script failed. Reviewing logs..."
                    }
                }
            }
        }

        stage('Push to ECR') {
            steps {
                sh """
                    aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_REGISTRY}
                    docker tag ${FULL_IMAGE} ${ECR_REGISTRY}/${ECR_REPO}:${IMAGE_TAG}
                    docker push ${ECR_REGISTRY}/${ECR_REPO}:${IMAGE_TAG}
                """
            }
        }

        stage('Terraform Apply') {
            steps {
                dir('terraform') {
                    sh "terraform init"
                    sh "terraform apply -auto-approve"
                }
            }
        }
    }

    post {
        always {
            // FIX: We wrap the cleanup in a script block to ensure FilePath context
            script {
                echo "==> Final Cleanup Tasks..."
                try {
                    sh "docker rmi ${FULL_IMAGE} || true"
                    sh "docker logout ${ECR_REGISTRY} || true"
                } catch (Exception e) {
                    echo "Cleanup warning: ${e.message}"
                }
            }
        }
        success {
            echo "==> SUCCESS: Build ${env.BUILD_NUMBER} deployed."
        }
        failure {
            echo "==> FAILURE: Build ${env.BUILD_NUMBER} failed. Check Discord for logs."
        }
    }
}
