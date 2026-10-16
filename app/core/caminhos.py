"""Caminhos da aplicação dentro do contêiner."""
import os
import re
from pathlib import Path

TRABALHO = Path(os.environ.get("VC_TRABALHO", "/trabalho"))
DADOS = Path(os.environ.get("VC_DADOS", "/dados"))  # volume Docker próprio: segredos e modelos de voz
APP = Path(__file__).resolve().parent.parent

BIBLIOTECA = TRABALHO / "biblioteca"
MARCAS = TRABALHO / "marcas"
MUSICA = TRABALHO / "musica"
EXPORTADOS = TRABALHO / "exportados"
CONFIG = TRABALHO / "configuracoes.json"
PIPER_DIR = DADOS / "piper"

MODO_TESTE = os.environ.get("VC_MODO_TESTE") == "1"


def garantir_pastas():
    for p in (TRABALHO, BIBLIOTECA, MARCAS, MUSICA, EXPORTADOS, DADOS, PIPER_DIR):
        p.mkdir(parents=True, exist_ok=True)


ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,80}$")


def pasta_video(video_id: str) -> Path:
    if not ID_RE.match(video_id or ""):
        raise ValueError("Identificador de vídeo inválido")
    return BIBLIOTECA / video_id


def pasta_projeto(video_id: str) -> Path:
    p = pasta_video(video_id) / "projeto"
    p.mkdir(parents=True, exist_ok=True)
    return p


def dentro(base: Path, relativo: str) -> Path:
    """Resolve um caminho relativo garantindo que fica dentro de base."""
    alvo = (base / relativo).resolve()
    if base.resolve() not in alvo.parents and alvo != base.resolve():
        raise ValueError("Caminho fora da pasta permitida")
    return alvo


def nome_seguro(nome: str) -> str:
    nome = re.sub(r"[^\w .,()-]+", "_", nome, flags=re.UNICODE).strip(" .")
    return nome[:120] or "arquivo"
