#!/bin/bash
# Video Composer · desinstalação no macOS
cd "$(dirname "$0")" || exit 1
sair() { echo; read -r -p "Pressione Enter para fechar."; exit "${1:-0}"; }

printf "\n\033[1mVideo Composer · desinstalação (macOS)\033[0m\n\n"
read -r -p "Remover o contêiner e a imagem do Video Composer? [s/N] " r
[[ "$r" =~ ^[sS]$ ]] || { echo "Cancelado."; sair 0; }

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker não encontrado: nada para remover no Docker."
else
  docker info >/dev/null 2>&1 || { open -a Docker; for _ in $(seq 1 60); do docker info >/dev/null 2>&1 && break; sleep 2; done; }
  [ -f .env ] && { set -a; . ./.env; set +a; }
  read -r -p "Apagar também as chaves de API e as vozes offline (volume do Docker)? [s/N] " rv
  if [[ "$rv" =~ ^[sS]$ ]]; then
    docker compose down --rmi local -v && echo "  ✅ Contêiner, imagem e volume removidos"
  else
    docker compose down --rmi local && echo "  ✅ Contêiner e imagem removidos (chaves mantidas no volume)"
  fi
fi

PASTA=$(grep -hE '^PASTA_TRABALHO=' config/pasta.env .env 2>/dev/null | head -1 | cut -d= -f2- | tr -d '"')
PASTA="${PASTA:-$PWD/trabalho}"
echo
echo "Pasta de trabalho (vídeos, músicas e exportados): $PASTA"
read -r -p "Apagar essa pasta e TODOS os vídeos? Digite APAGAR para confirmar, ou Enter para manter: " rp
if [ "$rp" = "APAGAR" ] && [ -d "$PASTA" ]; then
  rm -rf "$PASTA" && echo "  ✅ Pasta de trabalho apagada"
else
  echo "  Pasta de trabalho mantida."
fi
rm -f "$HOME/Desktop/Video Composer.command"
echo
echo "Desinstalado. Para remover a aplicação por completo, apague esta pasta: $PWD"
sair 0
