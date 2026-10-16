"""Música de fundo gerada pelo Eleven Music (API da ElevenLabs).

É a fonte recomendada para uso comercial: a faixa é composta sob medida para o vídeo,
instrumental, e a ElevenLabs a declara liberada para uso comercial conforme os Music Terms.
O plano da conta importa: os planos individuais (Free a Pro) são para pessoa física;
empresas precisam de Scale (até 10 funcionários), Business (até 50) ou Enterprise.
"""
import time

import httpx

from . import claude, jsonio, midia, precos
from .caminhos import MODO_TESTE, MUSICA
from .elevenlabs import URL, ErroVoz, _cab

ESTILOS = {
    "corporativo": ("Corporativo leve", "light corporate background music, soft piano and plucked acoustic guitar, warm and optimistic"),
    "tecnologia": ("Tecnologia moderna", "modern technology background music, clean electronic pulses, soft synth pads, confident and forward-moving"),
    "inspirador": ("Inspirador", "inspiring cinematic background music, gentle strings and piano, uplifting build without big drops"),
    "calmo": ("Calmo e ambiente", "calm ambient background music, soft pads and light textures, relaxed and focused"),
    "lofi": ("Lo-fi suave", "soft lo-fi background music, mellow keys, light vinyl texture, relaxed groove"),
    "acustico": ("Acústico", "acoustic background music, fingerpicked guitar and light percussion, friendly and natural"),
}
BASE = ("Instrumental only, no vocals. Designed to sit under a voice-over narration of a software demo: "
        "steady tempo, no sudden changes, no loud drops, moderate dynamics, clean ending.")
PLANOS_EMPRESA = {"scale": "até 10 funcionários", "business": "até 50 funcionários"}
PLANOS_INDIVIDUAIS = {"free", "starter", "creator", "pro"}


def plano() -> dict:
    """Plano da conta ElevenLabs e o que ele permite para música."""
    if MODO_TESTE:
        return {"tier": "creator", "nome": "creator", "individual": True, "exige_credito": False,
                "aviso": "Plano individual (modo de teste)."}
    try:
        r = httpx.get(f"{URL}/user/subscription", headers=_cab(), timeout=20)
    except ErroVoz as e:
        return {"tier": "", "erro": str(e)}
    except httpx.HTTPError as e:
        return {"tier": "", "erro": f"Sem conexão com a ElevenLabs: {e}"}
    if r.status_code != 200:
        return {"tier": "", "erro": f"A ElevenLabs respondeu {r.status_code}"}
    tier = str(r.json().get("tier", "")).lower()
    individual = any(tier.startswith(p) for p in PLANOS_INDIVIDUAIS)
    empresa = next((v for k, v in PLANOS_EMPRESA.items() if tier.startswith(k)), "")
    if tier.startswith("free"):
        aviso = ("Plano gratuito: a música exige o crédito \"Eleven Music\" (a aplicação coloca no encerramento) "
                 "e é para uso individual. Para vídeos da empresa, use um plano empresarial.")
    elif individual:
        aviso = ("Plano individual: os Music Terms da ElevenLabs liberam uso comercial por pessoa física. "
                 "Para vídeos de uma empresa, o plano precisa ser Scale (até 10 funcionários), "
                 "Business (até 50) ou Enterprise (acima de 50).")
    elif empresa:
        aviso = f"Plano empresarial ({empresa}): uso comercial pela empresa dentro desse porte."
    else:
        aviso = "Plano Enterprise: confira no contrato se inclui o Eleven Music."
    return {"tier": tier, "nome": tier, "individual": individual, "exige_credito": tier.startswith("free"), "aviso": aviso}


def compor(estilo: str, descricao: str, duracao_s: float, nome_base: str, registro=None) -> dict:
    rotulo, prompt_estilo = ESTILOS.get(estilo, ESTILOS["corporativo"])
    prompt = f"{prompt_estilo}. {descricao.strip()}. {BASE}" if descricao.strip() else f"{prompt_estilo}. {BASE}"
    ms = int(max(10, min(600, duracao_s + 1.5)) * 1000)
    MUSICA.mkdir(parents=True, exist_ok=True)
    carimbo = time.strftime("%Y%m%d-%H%M%S")
    destino = MUSICA / f"gerada-{nome_base}-{carimbo}.mp3"
    p = plano()
    if MODO_TESTE:
        midia.rodar(["ffmpeg", "-y", "-f", "lavfi", "-i", f"sine=frequency=220:duration={ms / 1000:.1f}", "-f", "lavfi",
                     "-i", f"sine=frequency=277:duration={ms / 1000:.1f}", "-filter_complex", "amix=inputs=2,volume=0.5",
                     "-ac", "2", destino])
    else:
        corpo = {"prompt": prompt, "music_length_ms": ms, "model_id": "music_v1", "force_instrumental": True}
        try:
            r = httpx.post(f"{URL}/music", params={"output_format": "mp3_44100_128"}, headers=_cab(), json=corpo, timeout=600)
        except httpx.HTTPError as e:
            raise ErroVoz(f"Sem conexão com o Eleven Music: {e}") from e
        if r.status_code != 200:
            raise ErroVoz(f"O Eleven Music respondeu {r.status_code}: {r.text[:300]}")
        destino.write_bytes(r.content)
    dur = midia.duracao(destino)
    usd = round(dur / 60 * precos.ELEVEN_MUSIC_USD_MIN, 3)
    if registro:
        claude.registrar(registro, {"etapa": "música gerada", "servico": "elevenlabs-music", "modelo": "music_v1",
                                    "segundos": round(dur, 1), "usd": usd})
    credito = "Música: Eleven Music" if p.get("exige_credito") else ""
    texto = [
        "COMPROVANTE DE ORIGEM DA MÚSICA",
        f"Gerada em: {time.strftime('%d/%m/%Y %H:%M')} pelo Eleven Music (ElevenLabs), modelo music_v1, pela API da conta configurada",
        f"Plano da conta no momento da geração: {p.get('tier') or 'não identificado'}",
        f"Estilo: {rotulo}",
        f"Prompt: {prompt}",
        f"Duração: {dur:.1f} s",
        "",
        "Uso: conforme os Music Terms da ElevenLabs (https://elevenlabs.io/music-terms) para o plano acima.",
        p.get("aviso", ""),
        "Exclusões em todos os planos, exceto Enterprise Music: cinema, TV, rádio e jogos de estúdio.",
        ("Crédito obrigatório: \"Eleven Music\"." if credito else "Crédito ao Eleven Music não exigido neste plano."),
    ]
    destino.with_suffix(".txt").write_text("\n".join(texto) + "\n", encoding="utf-8")
    meta = {"arquivo": destino.name, "titulo": f"{rotulo} (gerada)", "autor": "Eleven Music", "origem": "eleven_music",
            "licenca": "eleven_music", "verificada": True, "exige_atribuicao": bool(credito), "credito": credito,
            "plano": p.get("tier", ""), "aviso_plano": p.get("aviso", ""), "prompt": prompt, "duracao_s": dur,
            "baixado_em": time.strftime("%Y-%m-%d %H:%M")}
    jsonio.gravar(destino.with_suffix(".json"), meta)
    return meta
