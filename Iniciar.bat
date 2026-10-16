@echo off
REM Video Composer - Abrir (Windows)
title Video Composer - Abrir
if not exist "%~dp0scripts\windows\iniciar.ps1" (
  echo.
  echo Arquivos da aplicacao nao encontrados.
  echo Se voce abriu direto do .zip, primeiro clique com o botao direito no .zip,
  echo escolha "Extrair tudo" e rode este arquivo de dentro da pasta extraida.
  echo.
  pause
  exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\windows\iniciar.ps1"
