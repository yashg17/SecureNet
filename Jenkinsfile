pipeline {
    agent any
    
    environment {
        IMAGE_NAME = "securenet-parent-portal"
        IMAGE_TAG = "${BUILD_NUMBER}"
        FULL_IMAGE = "${IMAGE_NAME}:${IMAGE_TAG}"
        AWS_REGION = "us-east-1"
        // Ensure these exist in Jenkins -> Manage Jenkins -> Credentials as Secret Text
        AWS_ACCOUNT_ID = credentials('AWS_ACCOUNT_ID') 
        ECR_REGISTRY = "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
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
                bat "python --version"
                bat "git --version"
            }
        }

        stage('Checkov IaC Scan') {
            steps {
                echo "==> Scanning Terraform code..."
                // Windows uses 'mkdir' without '-p'
                bat "if not exist reports mkdir reports"
                bat """
                    checkov -d terraform/ ^
                        --soft-fail-on LOW,MEDIUM ^
                        --hard-fail-on ${CHECKOV_THRESHOLD} ^
                        --output cli ^
                        --output-file-path reports/ || exit 0
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
                bat "docker build -t ${FULL_IMAGE} ."
            }
        }

        stage('SonarQube Analysis') {
            steps {
                withSonarQubeEnv("${SONAR_SERVER_NAME}") {
                    script {
                        def scannerHome = tool "${SONAR_SCANNER_NAME}"
                        // Use backslashes for Windows paths
                        bat """
                            "${scannerHome}\\bin\\sonar-scanner" ^
                            -Dsonar.projectKey=${SONAR_PROJECT_KEY} ^
                            -Dsonar.sources=app,scripts ^
                            -Dsonar.python.version=3.11 ^
                            -Dsonar.token=${SONAR_TOKEN}
                        """
                    }
                }
            }
        }

        stage('Quality Gate') {
            steps {
                timeout(time: Integer.parseInt(QG_TIMEOUT_MINS), unit: 'MINUTES') {
                    waitForQualityGate abortPipeline: true
                }
            }
        }

        stage('Claude Security Summary') {
            steps {
                bat "pip install anthropic python-dotenv --quiet"
                script {
                    def result = bat(script: "python scripts/claude_triage_pipeline.py", returnStatus: true)
                    if (result == 1) error("Claude AI flagged CRITICAL issues")
                }
            }
        }

        stage('Push to ECR') {
            steps {
                bat """
                    aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_REGISTRY}
                    docker tag ${FULL_IMAGE} ${ECR_REGISTRY}/${ECR_REPO}:${IMAGE_TAG}
                    docker push ${ECR_REGISTRY}/${ECR_REPO}:${IMAGE_TAG}
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

        stage('Deploy to EKS') {
            steps {
                bat """
                    aws eks update-kubeconfig --region ${AWS_REGION} --name Securenet-Cluster
                    kubectl set image deployment/Securenet-App app=${ECR_REGISTRY}/${ECR_REPO}:${IMAGE_TAG} -n backend
                """
            }
        }
    }

    post {
        always {
            script {
                // Check if workspace context exists before running cleanup commands
                if (getContext(hudson.FilePath)) {
                    echo "==> Cleaning Workspace..."
                    bat "docker rmi ${FULL_IMAGE} || exit 0"
                    bat "docker logout || exit 0"
                    cleanWs()
                }
            }
        }
        success {
            echo "==> Build ${env.BUILD_NUMBER} Deployed Successfully."
        }
        failure {
            echo "==> Build ${env.BUILD_NUMBER} Failed."
        }
    }
}
