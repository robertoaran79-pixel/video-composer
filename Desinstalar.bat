@echo off
REM Video Composer - Desinstalar (Windows)
title Video Composer - Desinstalar
if not exist "%~dp0scripts\windows\desinstalar.ps1" (
  echo.
  echo Arquivos da aplicacao nao encontrados.
  echo Se voce abriu direto do .zip, primeiro clique com o botao direito no .zip,
  echo escolha "Extrair tudo" e rode este arquivo de dentro da pasta extraida.
  echo.
  pause
  exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\windows\desinstalar.ps1"
