"""Chaves de API.

Ordem de leitura: variável de ambiente (arquivo .env do compose) e depois o
arquivo /dados/segredos.json, que fica num volume Docker próprio, fora da
pasta de trabalho montada do computador. Nunca são gravadas na pasta de
trabalho nem devolvidas inteiras pela API.
"""
import os
import threading

from . import jsonio
from .caminhos import DADOS

ARQ = DADOS / "segredos.json"
ENV = {"claude": "ANTHROPIC_API_KEY", "elevenlabs": "ELEVENLABS_API_KEY"}
_lock = threading.Lock()


def obter(nome: str) -> str:
    v = os.environ.get(ENV.get(nome, ""), "").strip()
    if v:
        return v
    return (jsonio.ler(ARQ, {}) or {}).get(nome, "").strip()


def origem(nome: str) -> str:
    if os.environ.get(ENV.get(nome, ""), "").strip():
        return "arquivo .env"
    if (jsonio.ler(ARQ, {}) or {}).get(nome):
        return "cofre da aplicação"
    return ""


def definir(nome: str, valor: str) -> None:
    if nome not in ENV:
        raise ValueError("Segredo desconhecido")
    with _lock:
        dados = jsonio.ler(ARQ, {}) or {}
        if valor:
            dados[nome] = valor.strip()
        else:
            dados.pop(nome, None)
        jsonio.gravar(ARQ, dados)
        try:
            os.chmod(ARQ, 0o600)
        except OSError:
            pass


def mascarar(v: str) -> str:
    if not v:
        return ""
    if len(v) <= 12:
        return "•" * len(v)
    return f"{v[:7]}…{v[-4:]}"


def resumo() -> dict:
    return {n: {"mascara": mascarar(obter(n)), "origem": origem(n), "definida": bool(obter(n))} for n in ENV}
