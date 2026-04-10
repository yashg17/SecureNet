pipeline {
    agent any
    
    environment {
        IMAGE_NAME = "securenet-parent-portal"
        IMAGE_TAG = "${BUILD_NUMBER}"
        FULL_IMAGE = "${IMAGE_NAME}:${IMAGE_TAG}"
        AWS_REGION = "us-east-1"
        AWS_ACCOUNT_ID = credentials('AWS_ACCOUNT_ID') 
        ECR_REGISTRY = "${env.AWS_ACCOUNT_ID}.dkr.ecr.${env.AWS_REGION}.amazonaws.com"
        ECR_REPO = "securenet-parent-portal"
        SONAR_SERVER_NAME = "SonarQube"
        SONAR_SCANNER_NAME = "Sonar Scanner"
        SONAR_PROJECT_KEY = "securenet-parent-portal"
        SONAR_TOKEN = credentials('SONAR_TOKEN')
        CLAUDE_API_KEY = credentials('CLAUDE_API_KEY')
        DISCORD_WEBHOOK_URL = credentials('DISCORD_WEBHOOK_URL')
    }

    stages {
        stage('Environment Info') {
            steps {
                echo "==> Setting up Virtual Environment..."
                echo "==> Verifying Path Integrations..."
                bat """
                    python --version
                    pip --version
                    checkov --version
                """
                // Using 'py' launcher which is standard on Windows
                bat """
                    py -m venv venv
                    .\\venv\\Scripts\\python.exe -m pip install --upgrade pip
                    .\\venv\\Scripts\\pip.exe install checkov anthropic python-dotenv requests --quiet
                """
            }
        }

        stage('Checkov IaC Scan') {
            steps {
                echo "==> Scanning Terraform code..."
                bat "if not exist reports mkdir reports"
                // Run checkov from the virtual environment we just built
                bat ".\\venv\\Scripts\\checkov.exe -d terraform/ --soft-fail --output cli"
            }
        }

        stage('Docker Build') {
            steps {
                echo "==> Building Docker Image..."
                bat "docker build -t ${env.FULL_IMAGE} ."
            }
        }

        stage('SonarQube Analysis') {
            steps {
                script {
                    def scannerHome = tool "${SONAR_SCANNER_NAME}"
                    withSonarQubeEnv("${SONAR_SERVER_NAME}") {
                        bat """
                            "${scannerHome}\\bin\\sonar-scanner" ^
                            -Dsonar.projectKey=${env.SONAR_PROJECT_KEY} ^
                            -Dsonar.sources=app,scripts ^
                            -Dsonar.python.version=3.11 ^
                            -Dsonar.token=${env.SONAR_TOKEN}
                        """
                    }
                }
            }
        }

        stage('Claude Security Summary') {
            steps {
                echo "==> Running AI Triage..."
                script {
                    // Use the venv python to run your triage script
                    def result = bat(script: ".\\venv\\Scripts\\python.exe scripts/claude_triage_pipeline.py", returnStatus: true)
                    if (result != 0) error("Claude AI flagged CRITICAL issues or script failed")
                }
            }
        }

        stage('Push to ECR') {
            steps {
                bat """
                    aws ecr get-login-password --region ${env.AWS_REGION} | docker login --username AWS --password-stdin ${env.ECR_REGISTRY}
                    docker tag ${env.FULL_IMAGE} ${env.ECR_REGISTRY}/${env.ECR_REPO}:${env.IMAGE_TAG}
                    docker push ${env.ECR_REGISTRY}/${env.ECR_REPO}:${env.IMAGE_TAG}
                """
            }
        }
    }

    post {
        always {
            echo "==> Cleaning Workspace..."
            bat "docker rmi ${env.FULL_IMAGE} || exit 0"
            // Cleanup the virtual environment to keep the runner clean
            bat "rmdir /s /q venv || exit 0"
            cleanWs()
        }
    }
}
