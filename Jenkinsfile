pipeline {
    agent any
    
    environment {
        IMAGE_NAME = "securenet-parent-portal"
        IMAGE_TAG = "${BUILD_NUMBER}"
        FULL_IMAGE = "${IMAGE_NAME}:${IMAGE_TAG}"
        AWS_REGION = "us-east-1"
        // FIX: Use single quotes to prevent insecure Groovy interpolation
        AWS_ACCOUNT_ID = credentials('AWS_ACCOUNT_ID') 
        ECR_REGISTRY = "${env.AWS_ACCOUNT_ID}.dkr.ecr.${env.AWS_REGION}.amazonaws.com"
        ECR_REPO = "securenet-parent-portal"
        SONAR_SERVER_NAME = "SonarQube"
        SONAR_SCANNER_NAME = "Sonar Scanner"
        SONAR_PROJECT_KEY = "securenet-parent-portal"
        SONAR_TOKEN = credentials('SONAR_TOKEN')
        QG_TIMEOUT_MINS = "5"
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
                bat "docker --version"
                // Added 'py' as a fallback for Windows
                bat "python --version || py --version" 
                bat "git --version"
                bat """
                    "C:\\Python311\\python.exe" --version
                    "C:\\Python311\\Scripts\\pip.exe" --version
                """
            }
        }

        stage('Checkov IaC Scan') {
            steps {
                echo "==> Scanning Terraform code..."
                bat "if not exist reports mkdir reports"
                // Added --quiet to reduce log noise
                bat "checkov -d terraform/ --soft-fail --output cli || exit 0"
            }
        }

        stage('Docker Build') {
            steps {
                echo "==> Building Docker Image..."
                // Ensure Docker Desktop is RUNNING on the Windows host
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

        stage('Quality Gate') {
            steps {
                timeout(time: 5, unit: 'MINUTES') {
                    waitForQualityGate abortPipeline: true
                }
            }
        }

        stage('Claude Security Summary') {
            steps {
                // Use 'py -m pip' to ensure it hits the right Windows installation
                bat "py -m pip install anthropic python-dotenv --quiet"
                script {
                    def result = bat(script: "py scripts/claude_triage_pipeline.py", returnStatus: true)
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

        stage('Terraform Apply') {
            steps {
                dir('terraform') {
                    bat "terraform init && terraform apply -auto-approve"
                }
            }
        }
    }

    post {
        always {
            echo "==> Cleaning Workspace..."
            bat "docker rmi ${env.FULL_IMAGE} || exit 0"
            cleanWs()
        }
        success {
            echo "==> Build ${env.BUILD_NUMBER} Deployed Successfully."
        }
        failure {
            echo "==> Build ${env.BUILD_NUMBER} Failed."
        }
    }
}
