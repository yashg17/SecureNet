pipeline {
    agent any
    
    environment {
        IMAGE_NAME = "securenet-parent-portal"
        IMAGE_TAG = "${BUILD_NUMBER}"
        FULL_IMAGE = "${IMAGE_NAME}:${IMAGE_TAG}"
        AWS_REGION = "us-east-1"
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
                echo "Build Number : ${BUILD_NUMBER}"
                echo "Image : ${FULL_IMAGE}"
                echo "ECR Registry : ${ECR_REGISTRY}"
                echo "SonarQube : ${SONAR_SERVER_NAME}"
                echo "Scanner : ${SONAR_SCANNER_NAME}"
                echo "========================="
                sh "docker --version"
                sh "python3 --version"
                sh "checkov --version"
            }
        }

        stage('Checkov IaC Scan') {
            steps {
                echo "==> Scanning Terraform code with Checkov..."
                sh """
                    checkov -d terraform/ \
                        --soft-fail-on LOW,MEDIUM \
                        --hard-fail-on ${CHECKOV_THRESHOLD} \
                        --output cli \
                        --output-file-path reports/ \
                        || true
                """
                echo "==> Checkov Scan Complete."   
            }
            post {
                always {
                    archiveArtifacts artifacts: 'reports/*.txt', allowEmptyArchive: true
                }
            }
        }

        stage('Docker Build') {
            steps {
                echo "==> Building Docker Image: ${FULL_IMAGE}..."
                sh "docker build -t ${FULL_IMAGE} ."
                echo "==> Docker Build Complete."
            }
        }

        stage('SonarQube Analysis') {
            steps {
                echo "==> Starting SonarQube SAST Scan..."
                withSonarQubeEnv("${SONAR_SERVER_NAME}") {
                    script {
                        def scannerHome = tool "${SONAR_SCANNER_NAME}"
                        sh """
                            ${scannerHome}/bin/sonar-scanner \
                            -Dsonar.projectKey=${SONAR_PROJECT_KEY} \
                            -Dsonar.sources=app,scripts \
                            -Dsonar.python.version=3
