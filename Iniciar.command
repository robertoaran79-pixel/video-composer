#!/bin/bash
# Video Composer: sobe o contêiner e abre a aplicação no Chrome.
cd "$(dirname "$0")" || exit 1

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker não encontrado. Instale o Docker Desktop: https://www.docker.com/products/docker-desktop/"
  read -r -p "Pressione Enter para sair."; exit 1
fi
if ! docker info >/dev/null 2>&1; then
  echo "Abrindo o Docker Desktop…"
  open -a Docker
  until docker info >/dev/null 2>&1; do sleep 2; done
fi

mkdir -p config
if [ -f .env ]; then set -a; . ./.env; set +a; fi
# pasta de trabalho escolhida pela tela de Configurações tem prioridade
if [ -f config/pasta.env ]; then set -a; . ./config/pasta.env; set +a; fi
export PASTA_TRABALHO="${PASTA_TRABALHO:-$PWD/trabalho}"
mkdir -p "$PASTA_TRABALHO"

echo "Construindo e iniciando o contêiner (a primeira vez leva alguns minutos)…"
docker compose up -d --build || { read -r -p "Falhou. Pressione Enter para sair."; exit 1; }

echo -n "Aguardando a aplicação"
for _ in $(seq 1 60); do
  if curl -fs http://localhost:8898/api/sistema >/dev/null 2>&1; then break; fi
  echo -n "."; sleep 1
done
echo
if [ -d "/Applications/Google Chrome.app" ]; then
  open -a "Google Chrome" http://localhost:8898
else
  open http://localhost:8898
fi
echo "Video Composer rodando em http://localhost:8898"
