"""Voz offline Kokoro (modelo Kokoro-82M, licença Apache 2.0, uso comercial permitido).

Tem voz feminina em português do Brasil (Dora) e duas masculinas (Alex e Santa).
Os arquivos do modelo (cerca de 350 MB) são baixados no primeiro uso para o volume
de dados do Docker e reaproveitados depois.
"""
import threading
import wave
from pathlib import Path

import httpx

from .caminhos import DADOS

PASTA = DADOS / "kokoro"
ARQUIVOS = {
    "kokoro-v1.0.onnx": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/kokoro-v1.0.onnx",
    "voices-v1.0.bin": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/voices-v1.0.bin",
}
VOZES = [
    {"id": "pf_dora", "nome": "Dora (feminina)"},
    {"id": "pm_alex", "nome": "Alex (masculina)"},
    {"id": "pm_santa", "nome": "Santa (masculina)"},
]
_lock = threading.Lock()
_modelo = None


def disponivel() -> bool:
    import importlib.util
    return importlib.util.find_spec("kokoro_onnx") is not None


def _baixar(nome: str, url: str, aviso=None):
    destino = PASTA / nome
    if destino.exists() and destino.stat().st_size > 1_000_000:
        return destino
    PASTA.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_suffix(destino.suffix + ".parcial")
    with httpx.stream("GET", url, timeout=600, follow_redirects=True,
                      headers={"User-Agent": "VideoComposer/0.3"}) as r:
        if r.status_code != 200:
            raise RuntimeError(f"Não foi possível baixar o modelo de voz Kokoro ({r.status_code})")
        total = int(r.headers.get("content-length") or 0)
        feito = 0
        with open(tmp, "wb") as f:
            for parte in r.iter_bytes(1 << 20):
                f.write(parte)
                feito += len(parte)
                if aviso and total:
                    aviso(f"Baixando a voz offline Kokoro (só na primeira vez): {feito // 1_048_576} de {total // 1_048_576} MB")
    tmp.replace(destino)
    return destino


def _carregar(aviso=None):
    global _modelo
    with _lock:
        if _modelo is None:
            if not disponivel():
                raise RuntimeError("A voz Kokoro não está instalada nesta imagem. Reconstrua com o instalador.")
            for nome, url in ARQUIVOS.items():
                _baixar(nome, url, aviso)
            from kokoro_onnx import Kokoro
            _modelo = Kokoro(str(PASTA / "kokoro-v1.0.onnx"), str(PASTA / "voices-v1.0.bin"))
        return _modelo


def sintetizar(texto: str, voz: str, saida: Path, velocidade: float = 1.0, aviso=None) -> Path:
    import numpy as np
    modelo = _carregar(aviso)
    with _lock:
        audio, taxa = modelo.create(texto, voice=voz or "pf_dora", speed=max(0.5, min(2.0, velocidade)), lang="pt-br")
    pcm = (np.clip(audio, -1.0, 1.0) * 32767).astype("<i2")
    with wave.open(str(saida), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(int(taxa))
        w.writeframes(pcm.tobytes())
    return saida
