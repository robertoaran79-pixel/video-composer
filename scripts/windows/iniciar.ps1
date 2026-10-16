# Video Composer · abrir no Windows
. (Join-Path $PSScriptRoot "comum.ps1")
Titulo "Video Composer $Versao"
if (-not (Docker-Instalado)) { Erro "Docker Desktop não encontrado. Rode a instalação de novo."; Sair 1 }
if (-not (Garantir-Docker)) { Erro "O Docker Desktop não respondeu. Abra o Docker Desktop, espere ficar verde e tente de novo."; Sair 1 }
Preparar-Compose
Write-Host "  Iniciando..."
docker compose up -d
if ($LASTEXITCODE -ne 0) { Erro "Falha ao iniciar. Rode a instalação de novo (ela atualiza sem apagar nada)."; Sair 1 }
if (Esperar-App) { Abrir-Navegador; Ok "Video Composer rodando em $Url. Pode fechar esta janela." } else { Erro "A aplicação não respondeu. Diagnóstico: 'docker compose logs' nesta pasta."; Sair 1 }
Start-Sleep -Seconds 3
