# Video Composer · funções comuns dos scripts do Windows
$ErrorActionPreference = "Continue"
$Raiz = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $Raiz
$Url = "http://localhost:8898"
$Versao = if (Test-Path (Join-Path $Raiz "VERSAO")) { (Get-Content (Join-Path $Raiz "VERSAO") -TotalCount 1).Trim() } else { "0.4" }

# onde a aplicação fica instalada, e o registro em "Aplicativos instalados" do Windows
$PastaInstalacao = Join-Path $env:LOCALAPPDATA "Programs\VideoComposer"
$ChaveRegistro = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\VideoComposer"
$PastaMenuIniciar = Join-Path ([Environment]::GetFolderPath("Programs")) "Video Composer"
$AtalhoMesa = Join-Path ([Environment]::GetFolderPath("Desktop")) "Video Composer.lnk"
$PastaVideosPadrao = Join-Path ([Environment]::GetFolderPath("MyVideos")) "VideoComposer"

function Titulo($t) { Write-Host ""; Write-Host $t -ForegroundColor Cyan }
function Ok($t)     { Write-Host "  [OK] $t" -ForegroundColor Green }
function Aviso($t)  { Write-Host "  [ATENCAO] $t" -ForegroundColor Yellow }
function Erro($t)   { Write-Host "  [ERRO] $t" -ForegroundColor Red }
function Sair($c = 0) { Write-Host ""; Read-Host "Pressione Enter para fechar" | Out-Null; exit $c }

function Docker-Instalado {
    if (Get-Command docker -ErrorAction SilentlyContinue) { return $true }
    $bin = Join-Path $env:ProgramFiles "Docker\Docker\resources\bin"
    if (Test-Path (Join-Path $bin "docker.exe")) { $env:Path += ";$bin"; return $true }
    return $false
}

function Docker-Rodando {
    try { docker info *> $null; return ($LASTEXITCODE -eq 0) } catch { return $false }
}

function Garantir-Docker {
    if (Docker-Rodando) { return $true }
    $exe = Join-Path $env:ProgramFiles "Docker\Docker\Docker Desktop.exe"
    if (Test-Path $exe) {
        Write-Host "  Abrindo o Docker Desktop (pode levar até 1 minuto)..."
        Start-Process $exe | Out-Null
        for ($i = 0; $i -lt 90; $i++) { if (Docker-Rodando) { return $true }; Start-Sleep -Seconds 2 }
    }
    return (Docker-Rodando)
}

function Ler-Env {
    # .env primeiro; config\pasta.env (pasta escolhida na instalação ou na tela) tem prioridade
    $vars = @{}
    foreach ($arq in @((Join-Path $Raiz ".env"), (Join-Path $Raiz "config\pasta.env"))) {
        if (Test-Path $arq) {
            Get-Content $arq -Encoding UTF8 | ForEach-Object {
                if ($_ -match '^\s*([A-Z_]+)\s*=\s*(.*)$') { $vars[$Matches[1]] = $Matches[2].Trim().Trim('"') }
            }
        }
    }
    return $vars
}

function Definir-Pasta($valor) {
    New-Item -ItemType Directory -Force -Path (Join-Path $Raiz "config") | Out-Null
    [System.IO.File]::WriteAllText((Join-Path $Raiz "config\pasta.env"), "PASTA_TRABALHO=`"$valor`"`n", (New-Object System.Text.UTF8Encoding($false)))
}

function Pasta-Trabalho {
    # caminho no formato do Windows (com \)
    $v = (Ler-Env)["PASTA_TRABALHO"]
    if ($v) { return ($v -replace '/', '\') }
    return (Join-Path $Raiz "trabalho")
}

function Preparar-Compose {
    # o docker compose lê PASTA_TRABALHO do ambiente; usa barras normais
    $env:PASTA_TRABALHO = (Pasta-Trabalho) -replace '\\', '/'
    New-Item -ItemType Directory -Force -Path (Pasta-Trabalho) | Out-Null
}

function Esperar-App {
    Write-Host -NoNewline "  Aguardando a aplicação"
    for ($i = 0; $i -lt 120; $i++) {
        try { Invoke-WebRequest "$Url/api/sistema" -UseBasicParsing -TimeoutSec 2 | Out-Null; Write-Host ""; return $true } catch { Write-Host -NoNewline "."; Start-Sleep -Seconds 1 }
    }
    Write-Host ""
    return $false
}

function Caminho-Chrome {
    return @("$env:ProgramFiles\Google\Chrome\Application\chrome.exe", "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
             "$env:LocalAppData\Google\Chrome\Application\chrome.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
}

function Abrir-Navegador {
    $chrome = Caminho-Chrome
    if ($chrome) { Start-Process $chrome $Url } else { Start-Process $Url }
}

function Criar-Atalho($arquivo, $alvo, $descricao, $minimizado = $false) {
    $ws = New-Object -ComObject WScript.Shell
    $lnk = $ws.CreateShortcut($arquivo)
    $lnk.TargetPath = $alvo
    $lnk.WorkingDirectory = $Raiz
    $lnk.Description = $descricao
    $ico = Join-Path $Raiz "video-composer.ico"
    if (Test-Path $ico) { $lnk.IconLocation = "$ico,0" }
    if ($minimizado) { $lnk.WindowStyle = 7 }
    $lnk.Save()
}
