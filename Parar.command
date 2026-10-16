#!/bin/bash
# Video Composer: para o contêiner (os arquivos e as chaves são mantidos).
cd "$(dirname "$0")" || exit 1
docker compose down
echo "Video Composer parado."
