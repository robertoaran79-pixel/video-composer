#!/bin/bash
# Video Composer · instalação no macOS
# Verifica o Docker Desktop, prepara a configuração, constrói a imagem, guarda as chaves
# no cofre da aplicação e cria um atalho na Mesa.
cd "$(dirname "$0")" || exit 1
PASTA_APP="$PWD"
chmod +x ./*.command 2>/dev/null

titulo() { printf "\n\033[1m%s\033[0m\n" "$1"; }
ok()     { printf "  ✅ %s\n" "$1"; }
aviso()  { printf "  ⚠️  %s\n" "$1"; }
erro()   { printf "  ❌ %s\n" "$1"; }
sair()   { echo; read -r -p "Pressione Enter para fechar."; exit "${1:-0}"; }

titulo "Video Composer · instalação (macOS)"
echo "  Pasta da aplicação: $PASTA_APP"

# 1. Docker Desktop
titulo "1/6 Docker Desktop"
if ! command -v docker >/dev/null 2>&1; then
  aviso "Docker não encontrado."
  if command -v brew >/dev/null 2>&1; then
    read -r -p "  Instalar o Docker Desktop pelo Homebrew agora? [s/N] " r
    if [[ "$r" =~ ^[sS]$ ]]; then
      brew install --cask docker || { erro "Falha na instalação pelo Homebrew."; sair 1; }
    fi
  fi
  if ! command -v docker >/dev/null 2>&1 && [ ! -d "/Applications/Docker.app" ]; then
    echo "  Baixe e instale o Docker Desktop: https://www.docker.com/products/docker-desktop/"
    open "https://www.docker.com/products/docker-desktop/"
    echo "  Depois de instalar e abrir o Docker Desktop uma vez, rode este instalador de novo."
    sair 1
  fi
  export PATH="$PATH:/Applications/Docker.app/Contents/Resources/bin"
fi
if ! docker info >/dev/null 2>&1; then
  echo "  Abrindo o Docker Desktop (aceite os termos na primeira vez)…"
  open -a Docker
  for _ in $(seq 1 90); do docker info >/dev/null 2>&1 && break; sleep 2; done
fi
docker info >/dev/null 2>&1 || { erro "O Docker Desktop não respondeu. Abra o Docker Desktop e rode de novo."; sair 1; }
ok "Docker rodando ($(docker --version | sed 's/,.*//'))"

VER=$(docker compose version --short 2>/dev/null | sed 's/^v//')
if [ -z "$VER" ]; then erro "Docker Compose não encontrado. Atualize o Docker Desktop."; sair 1; fi
MAIOR=${VER%%.*}; RESTO=${VER#*.}; MENOR=${RESTO%%.*}
if [ "$MAIOR" -lt 2 ] || { [ "$MAIOR" -eq 2 ] && [ "$MENOR" -lt 24 ]; }; then
  erro "Docker Compose $VER é antigo (precisa de 2.24 ou mais novo). Atualize o Docker Desktop."; sair 1
fi
ok "Docker Compose $VER"

# 2. Chrome
titulo "2/6 Google Chrome"
if [ -d "/Applications/Google Chrome.app" ] || [ -d "$HOME/Applications/Google Chrome.app" ]; then
  ok "Chrome encontrado"
else
  aviso "Chrome não encontrado. A gravação de abas precisa do Chrome: https://www.google.com/chrome/"
fi

# 3. Pasta de trabalho
titulo "3/6 Pasta de trabalho (vídeos, músicas, exportados)"
[ -f .env ] || cp env.exemplo .env
mkdir -p config
ATUAL=$(grep -hE '^PASTA_TRABALHO=' config/pasta.env .env 2>/dev/null | head -1 | cut -d= -f2- | tr -d '"')
SUGESTAO="$HOME/VideoComposer"
echo "  1) Dentro da pasta da aplicação: $PASTA_APP/trabalho"
echo "  2) Na sua pasta de usuário: $SUGESTAO (recomendado se Documentos sincroniza com o iCloud)"
[ -n "$ATUAL" ] && echo "  Enter) Manter a atual: $ATUAL"
read -r -p "  Escolha [1/2]: " op
case "$op" in
  1) PASTA="$PASTA_APP/trabalho" ;;
  2) PASTA="$SUGESTAO" ;;
  *) PASTA="${ATUAL:-$PASTA_APP/trabalho}" ;;
esac
mkdir -p "$PASTA"/{biblioteca,marcas,musica,exportados}
echo "PASTA_TRABALHO=\"$PASTA\"" > config/pasta.env
ok "Pasta de trabalho: $PASTA"

# 4. Imagem e contêiner
titulo "4/6 Construindo e iniciando (a primeira vez leva alguns minutos)"
set -a; . ./.env; set +a
export PASTA_TRABALHO="$PASTA"
docker compose up -d --build || { erro "Falha ao construir ou iniciar o contêiner."; sair 1; }
printf "  Aguardando a aplicação"
for _ in $(seq 1 90); do curl -fs http://localhost:8898/api/sistema >/dev/null 2>&1 && break; printf "."; sleep 1; done
echo
curl -fs http://localhost:8898/api/sistema >/dev/null 2>&1 || { erro "A aplicação não respondeu. Veja: docker compose logs"; sair 1; }
ok "Aplicação rodando em http://localhost:8898"

# 5. Chaves de API (guardadas no cofre da aplicação, num volume do Docker)
titulo "5/6 Chaves de API (opcional: também dá para informar depois em Configurações)"
read -r -s -p "  Chave da Anthropic (Enter para pular): " K1; echo
read -r -s -p "  Chave da ElevenLabs (Enter para pular): " K2; echo
if [ -n "$K1$K2" ]; then
  python3 - "$K1" "$K2" <<'PY' > /tmp/vc_chaves.json
import json, sys
d = {}
if sys.argv[1]: d["claude"] = sys.argv[1]
if sys.argv[2]: d["elevenlabs"] = sys.argv[2]
print(json.dumps(d))
PY
  if curl -fs -X PUT -H "Content-Type: application/json" --data @/tmp/vc_chaves.json http://localhost:8898/api/segredos >/dev/null; then
    ok "Chaves guardadas no cofre da aplicação"
  else
    aviso "Não foi possível guardar as chaves. Informe em Configurações."
  fi
  rm -f /tmp/vc_chaves.json
  unset K1 K2
else
  echo "  Pulado."
fi

# 6. Atalho
titulo "6/6 Atalho"
read -r -p "  Criar atalho \"Video Composer\" na Mesa? [S/n] " r
if [[ ! "$r" =~ ^[nN]$ ]]; then
  ln -sf "$PASTA_APP/Iniciar.command" "$HOME/Desktop/Video Composer.command" && ok "Atalho criado na Mesa"
fi

titulo "Pronto!"
echo "  Abrir: duplo clique em Iniciar.command (ou no atalho da Mesa)"
echo "  Parar: Parar.command · Remover: Desinstalar.command"
if [ -d "/Applications/Google Chrome.app" ]; then open -a "Google Chrome" http://localhost:8898; else open http://localhost:8898; fi
sair 0
