# Video Composer · instalação no Windows
# Copia a aplicação para %LOCALAPPDATA%\Programs\VideoComposer, prepara o Docker,
# cria atalhos e registra em "Aplicativos instalados" (para desinstalar pelo Windows).
. (Join-Path $PSScriptRoot "comum.ps1")

# ---------- 0. copiar para a pasta de instalação (ou atualizar uma instalação existente) ----------
if ($Raiz.TrimEnd('\') -ne $PastaInstalacao.TrimEnd('\')) {
    Titulo "Video Composer $Versao · instalação"
    Write-Host "  Origem:  $Raiz"
    Write-Host "  Destino: $PastaInstalacao"
    if (Test-Path (Join-Path $PastaInstalacao "docker-compose.yml")) {
        Write-Host "  Já existe uma instalação: ela será atualizada. Vídeos, chaves e configurações são mantidos."
    }
    New-Item -ItemType Directory -Force -Path $PastaInstalacao | Out-Null
    # /MIR deixaria a pasta igual à origem e apagaria .env, config e trabalho; por isso /E com exclusões
    robocopy $Raiz $PastaInstalacao /E /XD trabalho config .git __pycache__ /XF .env *.command /NFL /NDL /NJH /NJS /NP | Out-Null
    if ($LASTEXITCODE -ge 8) { Erro "Falha ao copiar os arquivos (robocopy $LASTEXITCODE)."; Sair 1 }
    New-Item -ItemType Directory -Force -Path (Join-Path $PastaInstalacao "config") | Out-Null
    # arquivos baixados da internet vêm marcados como bloqueados; libera os da aplicação
    Get-ChildItem $PastaInstalacao -Recurse -File | Unblock-File -ErrorAction SilentlyContinue
    Ok "Arquivos copiados"
    & (Join-Path $PastaInstalacao "scripts\windows\instalar.ps1")
    exit $LASTEXITCODE
}

Titulo "Video Composer $Versao · instalação (Windows)"
Write-Host "  Pasta da aplicação: $Raiz"

# ---------- 1. Docker Desktop ----------
Titulo "1/6 Docker Desktop"
if (-not (Docker-Instalado)) {
    Aviso "O Docker Desktop não está instalado. Ele é necessário para rodar a aplicação."
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        $r = Read-Host "  Instalar o Docker Desktop agora pelo winget? [S/n]"
        if ($r -notmatch '^[nN]$') {
            winget install -e --id Docker.DockerDesktop --accept-package-agreements --accept-source-agreements
            Write-Host ""
            Aviso "O Docker Desktop usa o WSL 2. Se o Windows pedir, REINICIE o computador."
            Write-Host "  Depois: abra o Docker Desktop uma vez, aceite os termos e rode o atalho"
            Write-Host "  'Instalar Video Composer' (ou Instalar.bat) de novo."
            New-Item -ItemType Directory -Force -Path $PastaMenuIniciar | Out-Null
            Criar-Atalho (Join-Path $PastaMenuIniciar "Instalar Video Composer.lnk") (Join-Path $Raiz "Instalar.bat") "Continuar a instalação"
            Sair 0
        }
    }
    Write-Host "  Baixe e instale: https://www.docker.com/products/docker-desktop/"
    Start-Process "https://www.docker.com/products/docker-desktop/"
    Sair 1
}
if (-not (Garantir-Docker)) { Erro "O Docker Desktop não respondeu. Abra o Docker Desktop, espere ficar verde e rode de novo."; Sair 1 }
Ok ("Docker rodando (" + ((docker --version) -replace ',.*', '') + ")")
$ver = (docker compose version --short 2>$null) -replace '^v', ''
if (-not $ver) { Erro "Docker Compose não encontrado. Atualize o Docker Desktop."; Sair 1 }
$p = $ver.Split('.')
if ([int]$p[0] -lt 2 -or ([int]$p[0] -eq 2 -and [int]$p[1] -lt 24)) { Erro "Docker Compose $ver é antigo (precisa de 2.24 ou mais novo). Atualize o Docker Desktop."; Sair 1 }
Ok "Docker Compose $ver"

# ---------- 2. Chrome ----------
Titulo "2/6 Google Chrome"
if (Caminho-Chrome) { Ok "Chrome encontrado" } else { Aviso "Chrome não encontrado. A gravação de abas precisa do Chrome: https://www.google.com/chrome/" }

# ---------- 3. pasta de trabalho ----------
Titulo "3/6 Pasta de trabalho (vídeos, músicas e exportados)"
$atual = (Ler-Env)["PASTA_TRABALHO"]
if ($atual) { $atual = $atual -replace '/', '\' }
Write-Host "  1) $PastaVideosPadrao   (recomendado)"
Write-Host "  2) Outra pasta (você digita o caminho)"
if ($atual) { Write-Host "  Enter) Manter a atual: $atual" } else { Write-Host "  Enter) Usar a opção 1" }
$op = Read-Host "  Escolha"
switch ($op) {
    "1" { $pasta = $PastaVideosPadrao }
    "2" { $pasta = (Read-Host "  Caminho completo da pasta (ex.: D:\Videos\VideoComposer)").Trim().Trim('"') }
    default { if ($atual) { $pasta = $atual } else { $pasta = $PastaVideosPadrao } }
}
if (-not $pasta -or -not ($pasta -match '^[A-Za-z]:\\')) { Aviso "Caminho inválido; usando $PastaVideosPadrao"; $pasta = $PastaVideosPadrao }
if ($pasta -match 'OneDrive') { Aviso "Esta pasta está no OneDrive. Vídeos são grandes e podem travar a sincronização." }
foreach ($s in "biblioteca", "marcas", "musica", "exportados") { New-Item -ItemType Directory -Force -Path (Join-Path $pasta $s) | Out-Null }
Definir-Pasta ($pasta -replace '\\', '/')
Ok "Pasta de trabalho: $pasta"

# ---------- 4. construir e iniciar ----------
Titulo "4/6 Construindo e iniciando (a primeira vez leva de 5 a 15 minutos)"
Preparar-Compose
docker compose up -d --build
if ($LASTEXITCODE -ne 0) { Erro "Falha ao construir ou iniciar o contêiner. Confira a internet e rode de novo."; Sair 1 }
if (-not (Esperar-App)) { Erro "A aplicação não respondeu. Veja o diagnóstico: abra o PowerShell nesta pasta e rode 'docker compose logs'"; Sair 1 }
Ok "Aplicação rodando em $Url"

# ---------- 5. chaves ----------
Titulo "5/6 Chaves de API (opcional: também dá para informar depois em Configurações)"
function Ler-Segredo($rotulo) {
    $s = Read-Host $rotulo -AsSecureString
    $b = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($s)
    try { return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($b) } finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($b) }
}
$k1 = Ler-Segredo "  Chave da Anthropic (Enter para pular)"
$k2 = Ler-Segredo "  Chave da ElevenLabs (Enter para pular)"
if ($k1 -or $k2) {
    $corpo = @{}
    if ($k1) { $corpo.claude = $k1 }
    if ($k2) { $corpo.elevenlabs = $k2 }
    try {
        $json = [System.Text.Encoding]::UTF8.GetBytes(($corpo | ConvertTo-Json))
        Invoke-RestMethod -Method Put -Uri "$Url/api/segredos" -ContentType "application/json; charset=utf-8" -Body $json | Out-Null
        Ok "Chaves guardadas no cofre da aplicação (fora da pasta de trabalho)"
    } catch { Aviso "Não foi possível guardar as chaves. Informe em Configurações." }
    Remove-Variable k1, k2, corpo, json -ErrorAction SilentlyContinue
} else { Write-Host "  Pulado." }

# ---------- 6. atalhos e registro no Windows ----------
Titulo "6/6 Atalhos e registro no Windows"
New-Item -ItemType Directory -Force -Path $PastaMenuIniciar | Out-Null
Remove-Item (Join-Path $PastaMenuIniciar "Instalar Video Composer.lnk") -ErrorAction SilentlyContinue
Criar-Atalho (Join-Path $PastaMenuIniciar "Video Composer.lnk") (Join-Path $Raiz "Iniciar.bat") "Abrir o Video Composer"
Criar-Atalho (Join-Path $PastaMenuIniciar "Parar Video Composer.lnk") (Join-Path $Raiz "Parar.bat") "Parar o Video Composer" $true
Criar-Atalho (Join-Path $PastaMenuIniciar "Desinstalar Video Composer.lnk") (Join-Path $Raiz "Desinstalar.bat") "Remover o Video Composer"
$tutorial = Join-Path $Raiz "Tutorial de uso.pdf"
if (Test-Path $tutorial) { Criar-Atalho (Join-Path $PastaMenuIniciar "Tutorial do Video Composer.lnk") $tutorial "Como usar o Video Composer" }
Ok "Menu Iniciar: pasta 'Video Composer'"
$r = Read-Host "  Criar atalho na Área de Trabalho? [S/n]"
if ($r -notmatch '^[nN]$') { Criar-Atalho $AtalhoMesa (Join-Path $Raiz "Iniciar.bat") "Abrir o Video Composer"; Ok "Atalho na Área de Trabalho" }

try {
    New-Item -Path $ChaveRegistro -Force | Out-Null
    $tamanhoKb = [int]((Get-ChildItem $Raiz -Recurse -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum / 1KB) + 2000000  # + imagem Docker (cerca de 2 GB)
    $props = @{
        DisplayName = "Video Composer"; DisplayVersion = $Versao; Publisher = "Video Composer"
        InstallLocation = $Raiz; DisplayIcon = (Join-Path $Raiz "video-composer.ico")
        UninstallString = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$(Join-Path $Raiz 'scripts\windows\desinstalar.ps1')`""
        InstallDate = (Get-Date -Format "yyyyMMdd"); URLInfoAbout = $Url
    }
    foreach ($k in $props.Keys) { New-ItemProperty -Path $ChaveRegistro -Name $k -Value $props[$k] -PropertyType String -Force | Out-Null }
    foreach ($k in "NoModify", "NoRepair") { New-ItemProperty -Path $ChaveRegistro -Name $k -Value 1 -PropertyType DWord -Force | Out-Null }
    New-ItemProperty -Path $ChaveRegistro -Name "EstimatedSize" -Value $tamanhoKb -PropertyType DWord -Force | Out-Null
    Ok "Registrado em Configurações do Windows > Aplicativos > Aplicativos instalados"
} catch { Aviso "Não foi possível registrar em Aplicativos instalados. Use 'Desinstalar Video Composer' no Menu Iniciar." }

Titulo "Pronto!"
Write-Host "  Abrir:       Menu Iniciar > Video Composer (ou o atalho na Área de Trabalho)"
Write-Host "  Parar:       Menu Iniciar > Video Composer > Parar Video Composer"
Write-Host "  Tutorial:    Menu Iniciar > Video Composer > Tutorial do Video Composer"
Write-Host "  Desinstalar: Configurações do Windows > Aplicativos, ou Menu Iniciar > Desinstalar Video Composer"
Write-Host ""
Write-Host "  A pasta de onde você rodou o instalador pode ser apagada."
Abrir-Navegador
Sair 0
