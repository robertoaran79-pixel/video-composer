"""Tabela de preços (US$) e estimativa de custo por vídeo.

Preços de tabela consultados em 09/10/2026. Revisar antes de precificar:
platform.claude.com/docs/en/about-claude/pricing e elevenlabs.io/pricing/api
"""

CLAUDE = {  # US$ por milhão de tokens (entrada, saída)
    "claude-opus-5-5": (4.0, 20.0),
    "claude-sonnet-5-5": (2.0, 10.0),
    "claude-haiku-5-5": (0.10, 0.50),
}
MODELOS_CLAUDE = [
    {"id": "claude-opus-5-5", "nome": "Opus 5.5 (qualidade máxima)"},
    {"id": "claude-sonnet-5-5", "nome": "Sonnet 5.5 (econômico, cerca de metade do Opus)"},
    {"id": "claude-haiku-5-5", "nome": "Haiku 5.5 (quase de graça, validar qualidade)"},
]
ELEVEN = {  # US$ por mil caracteres
    "eleven_multilingual_v2": 0.08,
    "eleven_flash_v2_5": 0.04,
    "eleven_turbo_v2_5": 0.04,
}
ELEVEN_MUSIC_USD_MIN = 0.15  # Eleven Music via API, preço de tabela de 09/10/2026
MODELOS_ELEVEN = [
    {"id": "eleven_multilingual_v2", "nome": "Multilingual v2 (melhor qualidade)"},
    {"id": "eleven_flash_v2_5", "nome": "Flash v2.5 (metade do preço, mais rápido)"},
]

# Base do caso real: vídeo de 279,3 s.
BASE_S = 279.3
TOKENS = {  # etapa: (entrada, saída, escala com a duração?)
    "entendimento": (37_000, 6_000, True),
    "roteiro": (46_000, 15_000, True),
    "qa": (19_000, 2_000, False),
}


def custo_claude(modelo: str, entrada: int, saida: int) -> float:
    pe, ps = CLAUDE.get(modelo, CLAUDE["claude-opus-5-5"])
    return entrada / 1e6 * pe + saida / 1e6 * ps


def custo_voz(motor: str, modelo: str, caracteres: int) -> float:
    if motor != "elevenlabs":
        return 0.0
    return caracteres / 1000 * ELEVEN.get(modelo, 0.08)


def estimar(duracao_s: float, cfg: dict, car_s: float) -> dict:
    fator = max(duracao_s, 20) / BASE_S
    itens, total_claude = [], 0.0
    for etapa, (e, s, escala) in TOKENS.items():
        f = fator if escala else 1.0
        modelo = cfg["claude"]["modelos"][etapa]
        c = custo_claude(modelo, int(e * f), int(s * f))
        total_claude += c
        itens.append({"item": f"Claude · {etapa}", "modelo": modelo, "usd": round(c, 3)})
    # caracteres narrados: ≈ 75% do orçamento total da duração, + 1 rodada de revisão (≈ 50%)
    # + calibração automática (≈ 250 car.) e encurtamento automático de falas que não couberem
    car = int(duracao_s * car_s * 0.9 * 0.75 * 1.5) + 250
    motor = cfg["voz"]["motor"]
    modelo_voz = cfg["voz"]["elevenlabs"]["modelo"]
    cv = custo_voz(motor, modelo_voz, car)
    itens.append({"item": "Voz", "modelo": motor if motor != "elevenlabs" else modelo_voz,
                  "caracteres": car, "usd": round(cv, 3)})
    total = total_claude + cv
    return {
        "duracao_s": round(duracao_s, 1), "itens": itens,
        "claude_usd": round(total_claude, 3), "voz_usd": round(cv, 3),
        "total_usd": round(total, 2),
        "por_minuto_usd": round(total / max(duracao_s / 60, 0.1), 2),
        "limite_usd": cfg["privacidade"]["limite_custo_usd"],
        "acima_do_limite": total > float(cfg["privacidade"]["limite_custo_usd"] or 0),
    }
