"""Cliente mínimo da API da Anthropic, com registro de uso e custo por projeto."""
import base64
import json
import re
import time
from pathlib import Path

import httpx

from . import jsonio, precos, segredos

URL = "https://api.anthropic.com/v1"
VERSAO = "2023-06-01"


class ErroClaude(RuntimeError):
    pass


def _cab(chave: str) -> dict:
    return {"x-api-key": chave, "anthropic-version": VERSAO, "content-type": "application/json"}


def testar() -> dict:
    chave = segredos.obter("claude")
    if not chave:
        return {"ok": False, "mensagem": "Chave da Anthropic não informada"}
    try:
        r = httpx.get(f"{URL}/models", headers=_cab(chave), timeout=20)
    except httpx.HTTPError as e:
        return {"ok": False, "mensagem": f"Sem conexão com a API: {e}"}
    if r.status_code == 200:
        ids = [m.get("id") for m in r.json().get("data", [])]
        return {"ok": True, "mensagem": f"Conectado. {len(ids)} modelos disponíveis.", "modelos": ids}
    return {"ok": False, "mensagem": f"A API respondeu {r.status_code}: {r.text[:200]}"}


def imagem(caminho: Path) -> dict:
    tipo = "image/png" if caminho.suffix.lower() == ".png" else "image/jpeg"
    return {"type": "image", "source": {"type": "base64", "media_type": tipo,
                                        "data": base64.b64encode(caminho.read_bytes()).decode()}}


def texto(t: str) -> dict:
    return {"type": "text", "text": t}


def chamar(modelo: str, sistema: str, conteudo: list, max_tokens: int = 8000,
           registro: Path | None = None, etapa: str = "") -> str:
    chave = segredos.obter("claude")
    if not chave:
        raise ErroClaude("Informe a chave da Anthropic em Configurações")
    corpo = {"model": modelo, "max_tokens": max_tokens, "system": sistema,
             "messages": [{"role": "user", "content": conteudo}]}
    ultimo = ""
    for tentativa in range(4):
        try:
            r = httpx.post(f"{URL}/messages", headers=_cab(chave), json=corpo, timeout=600)
        except httpx.HTTPError as e:
            ultimo = str(e)
            time.sleep(3 * (tentativa + 1))
            continue
        if r.status_code in (429, 500, 502, 503, 529):
            ultimo = f"{r.status_code} {r.text[:200]}"
            time.sleep(5 * (tentativa + 1))
            continue
        if r.status_code != 200:
            raise ErroClaude(f"A API da Anthropic respondeu {r.status_code}: {r.text[:300]}")
        d = r.json()
        uso = d.get("usage", {})
        ent = int(uso.get("input_tokens", 0)) + int(uso.get("cache_creation_input_tokens", 0) or 0) \
            + int(uso.get("cache_read_input_tokens", 0) or 0)
        sai = int(uso.get("output_tokens", 0))
        if registro:
            registrar(registro, {"etapa": etapa, "servico": "claude", "modelo": modelo,
                                 "entrada": ent, "saida": sai,
                                 "usd": round(precos.custo_claude(modelo, ent, sai), 4)})
        partes = [b.get("text", "") for b in d.get("content", []) if b.get("type") == "text"]
        if d.get("stop_reason") == "max_tokens":
            raise ErroClaude("A resposta do modelo foi cortada (limite de tokens). Tente um vídeo menor.")
        return "".join(partes)
    raise ErroClaude(f"API da Anthropic indisponível após várias tentativas: {ultimo}")


def registrar(arquivo: Path, item: dict):
    dados = jsonio.ler(arquivo, []) or []
    item["data"] = time.strftime("%Y-%m-%d %H:%M:%S")
    dados.append(item)
    jsonio.gravar(arquivo, dados)


def extrair_json(t: str):
    t = t.strip()
    m = re.search(r"```(?:json)?\s*(.*?)```", t, re.S)
    if m:
        t = m.group(1).strip()
    ini = t.find("{")
    fim = t.rfind("}")
    if ini < 0 or fim < 0:
        raise ErroClaude("O modelo não devolveu JSON")
    try:
        return json.loads(t[ini:fim + 1])
    except json.JSONDecodeError as e:
        raise ErroClaude(f"JSON inválido devolvido pelo modelo: {e}") from e
