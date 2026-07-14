pipeline {
    agent any
    
    options {
        timeout(time: 2, unit: 'HOURS')
        timestamps()
        buildDiscarder(logRotator(numToKeepStr: '10'))
    }
    
    environment {
        V8_VERSION = "8.3.25.1374"
        IB_PATH = "./build/ib"
        SONAR_PROJECT_KEY = "kb99_site_chat_bot"
    }
    
    stages {

        stage('Checkout') {
            steps {
                checkout scm   // multibranch сам подставит нужную ветку
                bat """
                    chcp 65001 > nul
                    echo %BRANCH_NAME%
                """
            }
        }

        stage('Создание ИБ из шаблона') {
            steps {
                echo "Создание информационной базы из шаблона"
                script {
                        echo "Копирование шаблона базы данных"
                        bat """
                            chcp 65001 > nul
                            prepare.cmd
                        """
                }
            }
        }
                
        stage('Сборка и загрузка из репозитория') {
            steps {
                echo "Сборка и загрузка из репозитория"
                bat """
                    chcp 65001 > nul
                    call build.cmd 
                """
            }
        }

        stage('Start BDD Tests') {
            steps {
                echo "Запуск BDD тестов с подробным логированием"
                script {
                    try {
                        bat """
                            chcp 65001 > nul
                            call test.cmd 
                        """
                    } catch (Exception e) {
                        echo "BDD тесты завершились с ошибками: ${e.getMessage()}"
                        
                        currentBuild.result = 'UNSTABLE'
                    }
                }
            }
        }

        stage('SonarQube Analysis') {
            steps {
                script {
                    
                    // Генерируем версию динамически на основе номера сборки Jenkins
                    def projectVersion = "1.0.${env.BUILD_NUMBER}"
                    
                    // Получение пути к установленной автоматически утилите sonar-scanner.
                    // Имя утилиты должно совпадать с заданным в настройках Global Tool Configuration
                    def scannerHome = tool 'sonar-scanner'
                    def sonarCommand = "${scannerHome}\\bin\\sonar-scanner.bat"
                    
                    // Получение данных авторизации к серверу SonarQube.
                    // Имя сервера должно совпадать с заданным в настройках System Configuration
                    withSonarQubeEnv('SONARQUBE_ENV') {
                        bat """
                            chcp 65001 > nul
                            "${sonarCommand}" \
                            -Dsonar.projectVersion=${projectVersion} \
                            -Dsonar.projectKey=${env.SONAR_PROJECT_KEY} \
                            -Dsonar.host.url=%SONAR_HOST_URL% \
                            -Dsonar.token=%SONAR_AUTH_TOKEN%                             
                        """
                    }
                }
            }
        }                
    }
    
    post {
        always {
            echo "Публикация отчетов и сбор статистики"
            script {
                // Публикация отчетов Allure
                if (fileExists('build/out/allure')) {
                    allure([
                        includeProperties: false,
                        jdk: '',
                        properties: [],
                        reportBuildPolicy: 'ALWAYS',
                        results: [[path: 'build/out/allure']]
                    ])
                }

                
/*                 // Публикация синтаксических отчетов (Allure)
                if (fileExists('build/reports/syntax-check/allure')) {
                    allure([
                        includeProperties: false,
                        jdk: '',
                        properties: [],
                        reportBuildPolicy: 'ALWAYS',
                        results: [[path: 'build/reports/syntax-check/allure']]
                    ])
                } */
                
                // Публикация HTML отчета с логами
                if (fileExists('build/logs')) {
                    publishHTML([
                        allowMissing: true,
                        alwaysLinkToLastBuild: true,
                        keepAll: true,
                        reportDir: 'build/logs',
                        reportFiles: '*.log',
                        reportName: 'Vanessa Test Logs',
                        reportTitles: 'Логи тестирования Vanessa'
                    ])
                }
                
                // Архивирование всех артефактов
                archiveArtifacts artifacts: 'build/**/*.log', allowEmptyArchive: false
                archiveArtifacts artifacts: 'build/logs/**/*', allowEmptyArchive: false
                archiveArtifacts artifacts: 'build/reports/**/*', allowEmptyArchive: false
                //archiveArtifacts artifacts: 'out/smoke/**/*', allowEmptyArchive: false
            }
        }
        success {
            echo "Pipeline выполнен успешно"
        }
        failure {
            echo "Pipeline завершился с ошибкой"
            script {
                // Отправка email при ошибке
                if (env.CHANGE_ID == null) { // только для основной ветки
                    mail to: 'fa@kb99.pro',
                         subject: "Jenkins Build Failed: ${env.JOB_NAME} - ${env.BUILD_NUMBER}",
                         body: """Сборка завершилась с ошибкой.
                         
Проект: ${env.JOB_NAME}
Номер сборки: ${env.BUILD_NUMBER}
URL: ${env.BUILD_URL}

Проверьте логи для получения деталей."""
                }
            }            
        }
    }
}