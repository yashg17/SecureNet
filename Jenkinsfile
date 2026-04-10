pipeline {
    agent any
    
    environment {
        // Basic Image Config
        IMAGE_NAME = "securenet-parent-portal"
        IMAGE_TAG = "${BUILD_NUMBER}"
        FULL_IMAGE = "${IMAGE_NAME}:${IMAGE_TAG}"
        
        // AWS Config - Ensure 'AWS_ACCOUNT_ID' exists in Jenkins Credentials
        AWS_REGION = "us-east-1"
        AWS_ACCOUNT_ID = credentials('AWS_ACCOUNT_ID')
        ECR_REGISTRY = "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
        ECR_REPO = "securenet-parent-portal"
        
        // Tools & Security
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
                echo "Image        : ${env.FULL_IMAGE}"
                echo "ECR Registry : ${env.ECR_REGISTRY}"
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
                    mkdir -p reports
                    checkov -d terraform/ \
                        --soft-fail-on LOW,MEDIUM \
                        --hard-fail-on ${env.CHECKOV_THRESHOLD} \
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
                echo "==> Building Docker Image: ${env.FULL_IMAGE}..."
                sh "docker build -t ${env.FULL_IMAGE} ."
            }
        }

        stage('SonarQube Analysis') {
            steps {
                withSonarQubeEnv("${env.SONAR_SERVER_NAME}") {
                    script {
                        def scannerHome = tool "${env.SONAR_SCANNER_NAME}"
                        sh """
                            ${scannerHome}/bin/sonar-scanner \
                            -Dsonar.projectKey=${env.SONAR_PROJECT_KEY} \
                            -Dsonar.sources=app,scripts \
                            -Dsonar.python.version=3.11 \
                            -Dsonar.exclusions=**/__pycache__/**,**/*.pyc
                        """
                    }
                }
            }
        }

        stage('Quality Gate') {
            steps {
                timeout(time: Integer.parseInt(env.QG_TIMEOUT_MINS), unit: 'MINUTES') {
                    waitForQualityGate abortPipeline: true
                }
            }
        }

        stage('Claude Security Summary') {
            steps {
                sh "pip3 install anthropic python-dotenv --quiet"
                sh "mkdir -p reports"
                script {
                    def result = sh(script: "python3 scripts/claude_triage_pipeline.py", returnStatus: true)
                    if (result == 1) {
                        error("Claude AI flagged CRITICAL issues - Blocking Deployment")
                    }
                }
            }
            post {
                always {
                    archiveArtifacts artifacts: 'reports/claude_pipeline_*.json', allowEmptyArchive: true
                }
            }
        }

        stage('Push to ECR') {
            steps {
                sh """
                    aws ecr get-login-password --region ${env.AWS_REGION} | \
                        docker login --username AWS --password-stdin ${env.ECR_REGISTRY}
                    docker tag ${env.FULL_IMAGE} ${env.ECR_REGISTRY}/${env.ECR_REPO}:${env.IMAGE_TAG}
                    docker push ${env.ECR_REGISTRY}/${env.ECR_REPO}:${env.IMAGE_TAG}
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

        stage('Deploy to EKS') {
            steps {
                sh """
                    aws eks update-kubeconfig --region ${env.AWS_REGION} --name Securenet-Cluster
                    kubectl apply -f k8s/namespace.yml
                    kubectl apply -f k8s/network-policy.yml
                    kubectl set image deployment/Securenet-App \
                        app=${env.ECR_REGISTRY}/${env.ECR_REPO}:${env.IMAGE_TAG} \
                        -n backend
                """
            }
        }
    }

    post {
        always {
            echo "==> Cleaning Workspace and Local Docker Image..."
            // Using env. prefix ensures the variables are found in the post-block scope
            sh "docker rmi
