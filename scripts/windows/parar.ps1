# Video Composer · parar no Windows (vídeos, chaves e configurações são mantidos)
. (Join-Path $PSScriptRoot "comum.ps1")
if (-not (Docker-Instalado)) { Erro "Docker Desktop não encontrado."; Sair 1 }
Preparar-Compose
docker compose down
Ok "Video Composer parado. Vídeos, chaves e configurações foram mantidos."
Start-Sleep -Seconds 2
