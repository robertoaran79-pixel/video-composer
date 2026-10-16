# Video Composer · desinstalação no Windows
# Remove contêiner, imagem, atalhos e o registro em "Aplicativos instalados".
# Chaves de API e vídeos só são apagados se você confirmar.
. (Join-Path $PSScriptRoot "comum.ps1")

Titulo "Video Composer $Versao · desinstalação"
Write-Host "  Pasta da aplicação: $Raiz"
$r = Read-Host "  Remover o Video Composer deste computador? [s/N]"
if ($r -notmatch '^[sS]$') { Write-Host "  Cancelado."; Sair 0 }

# ---------- 1. Docker: contêiner, imagem e (opcional) volume com chaves e vozes ----------
Titulo "1/4 Contêiner e imagem do Docker"
$pasta = Pasta-Trabalho
Preparar-Compose
if ((Docker-Instalado) -and (Garantir-Docker)) {
    $rv = Read-Host "  Apagar também as chaves de API e as vozes offline baixadas? [s/N]"
    if ($rv -match '^[sS]$') { docker compose down --rmi local -v } else { docker compose down --rmi local }
    if ($LASTEXITCODE -eq 0) { Ok "Contêiner e imagem removidos" } else { Aviso "O Docker informou um problema ao remover (pode já ter sido removido)" }
} else {
    Aviso "Docker não disponível agora: contêiner e imagem não foram removidos."
    Write-Host "  Se quiser, remova depois no Docker Desktop (Containers e Images: 'video-composer')."
}

# ---------- 2. pasta de trabalho ----------
Titulo "2/4 Pasta de trabalho (vídeos, músicas e exportados)"
Write-Host "  $pasta"
$rp = Read-Host "  Apagar essa pasta e TODOS os vídeos? Digite APAGAR para confirmar, ou Enter para manter"
if ($rp -ceq "APAGAR") {
    if (Test-Path $pasta) { Remove-Item -Recurse -Force $pasta -ErrorAction SilentlyContinue; Ok "Pasta de trabalho apagada" }
} else {
    # se os vídeos estão dentro da pasta da aplicação, move para fora antes de apagar a aplicação
    $dentro = (Test-Path $pasta) -and ((Resolve-Path $pasta).Path.TrimEnd('\') + '\').StartsWith($Raiz.TrimEnd('\') + '\', [StringComparison]::OrdinalIgnoreCase)
    if ($dentro) {
        $destino = $PastaVideosPadrao
        if (Test-Path $destino) { $destino = "$PastaVideosPadrao-" + (Get-Date -Format "yyyyMMdd-HHmm") }
        New-Item -ItemType Directory -Force -Path (Split-Path $destino) | Out-Null
        Move-Item $pasta $destino
        Ok "Vídeos mantidos e movidos para: $destino"
    } else {
        Ok "Pasta de trabalho mantida"
    }
}

# ---------- 3. atalhos e registro ----------
Titulo "3/4 Atalhos e registro no Windows"
Remove-Item $AtalhoMesa -Force -ErrorAction SilentlyContinue
Remove-Item $PastaMenuIniciar -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item $ChaveRegistro -Recurse -Force -ErrorAction SilentlyContinue
Ok "Atalhos e registro removidos"

# ---------- 4. arquivos da aplicação ----------
Titulo "4/4 Arquivos da aplicação"
$instalado = $Raiz.TrimEnd('\') -eq $PastaInstalacao.TrimEnd('\')
if ($instalado) {
    Write-Host "  A pasta $Raiz será apagada ao fechar esta janela."
} else {
    Write-Host "  Esta cópia não está na pasta de instalação padrão. Apague a pasta manualmente se quiser: $Raiz"
}
Write-Host ""
Write-Host "  O Docker Desktop continua instalado (outros programas podem usar)."
Write-Host "  Para removê-lo: Configurações do Windows > Aplicativos > Docker Desktop > Desinstalar."
Titulo "Desinstalado."
Read-Host "Pressione Enter para fechar" | Out-Null
if ($instalado) {
    Set-Location $env:TEMP
    # apaga a pasta depois que esta janela fechar (o script em execução fica dentro dela)
    Start-Process -FilePath "cmd.exe" -ArgumentList "/c timeout /t 3 /nobreak >nul & rmdir /s /q `"$Raiz`"" -WindowStyle Hidden
}
exit 0
