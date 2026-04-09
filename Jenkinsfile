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

    stages{

        // STAGE 1

        stage('Environment Info') {
            steps{
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

        // STAGE 2

        stage('Checkov IaC Scan') {
            steps{
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
            post{
                always {
                    archiveArtifacts artifacts: 'reqports/*.txt', allowEmptyArchive: true
                }
            }
        }

        // STAGE 3

        stage('Docker Build') {
            steps{
                echo "==> Building Docker Image: ${FULL_IMAGE}..."
                sh "docker build -t ${FULL_IMAGE}."
                echo "==> Docker Build Complete."
            }
        }

        // STAGE 4

        stage('SonarQube Analysis') {
            steps{
                echo "==> Starting SonarQube SAST Scan..."
                withSonarQubeEnv("${SONAR_SERVER_NAME}") {
                    script {
                        def scannerHome = tool "${SONAR_SCANNER_NAME}"
                        sh """
                            ${scannerHome}/bin/sonar-scanner \
                            -Dsonar.projectkey=${SONAR_PROJECT_KEY} \
                            -Dsonar.sources=app,scripts \
                            -Dsonar.python.version=3.11 \
                            -Dsonar.exclusions=**/__pycache__/**,**/*.pyc
                        """
                    }
                }
                echo "==> SonarQube Analysis Submitted." 
            }
        }

        // STAGE 5

        stage('Quality Gate') {
            steps{
                echo "==> Waiting for SonarQube Quality Gate..."
                timeout(time: Integer.parseInt(QG_TIMEOUT_MINS), unit: 'MINUTES') {
                    waitForQualityGate abortPipeline: true
                }
                echo "==> Quality Gate PASSED."
            }
        }

        // STAGE 6

        stage('Claude Security Summary') {
            steps{
                echo "==> Generating Calude AI Security Summary..."
                sh "pip3 install anthropic python-dotenv --quiet"
                sh "mkdir -p reports"
                script {
                    def result = sh(
                        script: "python3 scripts/claude_triage_pipeline.py",
                        returnStatus: true
                    )
                    if (result == 1) {
                        error("Claude AI flagged CRITICAL issues - Blocking Deployment")
                    }
                }
                echo "==> Claude Summary Complete."
            }
            post{
                always {
                    archiveArtifacts artifacts: 'reports/claude_pipeline_*.json', allowEmptyArchive: true
                }
            }
        }

        // STAGE 7

        stage('Push to ECR') {
            steps{
                echo "==> Pushing Image to ECR..."
                sh """
                    aws ecr get-login-password --region ${AWS_REGION} | \
                        docker login --username AWS --password-stdin ${ECR_REGISTRY}
                    docker tag ${FULL_IMAGE} ${ECR_REGISTRY}/${ECR_REPO}:${IMAGE_TAG}
                """
                echo "==> Pushed to: ${ECR_REGISTRY}/${ECR_REPO}:${IMAGE_TAG}"        
            }
        }

        // STAGE 8

        stage('Terraform Apply') {
            steps{
                echo "==> Applying Terraform Infrastructure..."
                dir('terraform') {
                    sh "terraform init"
                    sh "terraform validate"
                    sh "terraform plan -out=tfplan"
                    sh "terraform apply -aut-approve tfplan"
                }
                echo "==> Terraform Apply Complete."
            }
        }

        // STAGE 9

        stage('Deploy to EKS') {
            steps{
                echo "==> Deploying to EKS..."
                sh """
                    aws eks update-kubeconfig --region ${AWS_REGION} --name Securenet-Cluster
                    kubectl apply -f k8s/namespace.yml
                    kubectl apply -f k8s/network-policy.yml
                    kubectl set image deployment/Securenet-App \
                        app=${ECR_REGISTRY}/${ECR_REPO}:${IMAGE_TAG} \
                        -n backend
                """   
                echo "==> EKS Deployment Complete."        
            }
        }
    }

    // POST CLEANING

    post{
        always {
            echo "==> Cleaning Workspace and Docker Image..."
            sh "sh "docker rmi ${env.FULL_IMAGE} || true"
            sh "docker logout || true"
            cleanWs()
            echo "==> Cleanup Complete."
        }
        success {
            echo "==> PIPELINE PASSED - Build ${BUILD_NUMBER} deployed to EKS."
        }
        failure {
            echo "==> PIPELINE FAILED - Build ${BUILD_NUMBER} unsuccessful"
            echo "==> Check: SonarQube Dashboard, Checkov Report, Claude Summary, ECR"
        }
    }
}
