"""Cliente mínimo da API da ElevenLabs."""
import time

import httpx

from . import segredos

URL = "https://api.elevenlabs.io/v1"


class ErroVoz(RuntimeError):
    pass


def _cab():
    chave = segredos.obter("elevenlabs")
    if not chave:
        raise ErroVoz("Informe a chave da ElevenLabs em Configurações")
    return {"xi-api-key": chave}


def testar() -> dict:
    try:
        r = httpx.get(f"{URL}/user/subscription", headers=_cab(), timeout=20)
    except ErroVoz as e:
        return {"ok": False, "mensagem": str(e)}
    except httpx.HTTPError as e:
        return {"ok": False, "mensagem": f"Sem conexão com a API: {e}"}
    if r.status_code == 200:
        d = r.json()
        usados, limite = d.get("character_count", 0), d.get("character_limit", 0)
        return {"ok": True, "mensagem": f"Conectado. Plano {d.get('tier','?')}: {usados:,} de {limite:,} caracteres usados no ciclo.".replace(",", ".")}
    return {"ok": False, "mensagem": f"A API respondeu {r.status_code}: {r.text[:200]}"}


def _eh_pt(v: dict) -> bool:
    labels = v.get("labels") or {}
    txt = " ".join(str(x) for x in labels.values()).lower()
    if "portug" in txt or "brazil" in txt or "pt-br" in txt:
        return True
    for lang in v.get("verified_languages") or []:
        if str(lang.get("language", "")).lower().startswith("pt"):
            return True
    return False


def listar_vozes() -> list:
    r = httpx.get(f"{URL}/voices", headers=_cab(), timeout=30)
    if r.status_code != 200:
        raise ErroVoz(f"A API respondeu {r.status_code}: {r.text[:200]}")
    vozes = []
    for v in r.json().get("voices", []):
        labels = v.get("labels") or {}
        vozes.append({
            "id": v.get("voice_id"), "nome": v.get("name"),
            "pt_br": _eh_pt(v),
            "descricao": ", ".join(str(x) for x in labels.values() if x),
            "categoria": v.get("category", ""),
            "previa": v.get("preview_url", ""),
        })
    vozes.sort(key=lambda x: (not x["pt_br"], (x["nome"] or "").lower()))
    return vozes


def sintetizar(texto: str, voice_id: str, modelo: str, velocidade: float = 1.0,
               anterior: str = "", seguinte: str = "") -> bytes:
    if not voice_id:
        raise ErroVoz("Escolha uma voz da ElevenLabs em Configurações")
    corpo = {
        "text": texto, "model_id": modelo,
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75,
                           "speed": round(max(0.7, min(1.2, velocidade)), 3)},
    }
    if anterior:
        corpo["previous_text"] = anterior
    if seguinte:
        corpo["next_text"] = seguinte
    ultimo = ""
    for tentativa in range(4):
        try:
            r = httpx.post(f"{URL}/text-to-speech/{voice_id}", params={"output_format": "mp3_44100_128"},
                           headers=_cab(), json=corpo, timeout=120)
        except httpx.HTTPError as e:
            ultimo = str(e)
            time.sleep(2 * (tentativa + 1))
            continue
        if r.status_code == 200:
            return r.content
        if r.status_code in (429, 500, 502, 503):
            ultimo = f"{r.status_code} {r.text[:200]}"
            time.sleep(4 * (tentativa + 1))
            continue
        raise ErroVoz(f"A ElevenLabs respondeu {r.status_code}: {r.text[:300]}")
    raise ErroVoz(f"ElevenLabs indisponível após várias tentativas: {ultimo}")
