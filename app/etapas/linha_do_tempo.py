"""Linha do tempo do vídeo final, compartilhada pelas etapas 5 a 8, pelo editor e pela música.

Os cartões de abertura e encerramento esticam para caber a fala de cada um.
"""
from ..core import jsonio
from ..core.caminhos import pasta_projeto


def calcular(cartoes: dict, perfil: dict, encaixe: dict | None = None) -> dict:
    ab, en = cartoes["abertura"], cartoes["encerramento"]
    durs = {str(r["id"]): r["duracao_s"] for r in (encaixe or {}).get("falas", [])}
    T_base = float(cartoes.get("transicao_s", 0.8))
    A = float(ab["duracao_s"]) if ab["ativo"] else 0.0
    E = float(en["duracao_s"]) if en["ativo"] else 0.0
    if A > 0 and durs.get("abertura"):
        A = max(A, 0.3 + durs["abertura"] + 0.5 + T_base)
    if E > 0 and durs.get("encerramento"):
        E = max(E, T_base + 0.3 + durs["encerramento"] + 0.9)
    T_ab = max(min(T_base, A - 0.5), 0.0) if A > 0 else 0.0
    T_en = max(min(T_base, E - 0.5), 0.0) if E > 0 else 0.0
    V = float(perfil["duracao_s"])
    D = A - T_ab                    # instante do vídeo final em que começa o vídeo gravado
    fim_video = D + V
    total = fim_video + (E - T_en if E > 0 else 0)
    return {"abertura_s": round(A, 3), "encerramento_s": round(E, 3), "transicao_s": T_ab, "transicao_fim_s": T_en,
            "video_s": V, "deslocamento_video_s": round(D, 3), "fim_video_s": round(fim_video, 3),
            "total_s": round(total, 3), "abertura_fala_s": 0.3,
            "encerramento_fala_s": round(fim_video - T_en + 0.3, 3) if E > 0 else None}


def do_projeto(video_id: str, cfg: dict | None = None) -> dict | None:
    from . import cartoes as _cartoes
    proj = pasta_projeto(video_id)
    perfil = jsonio.ler(proj / "perfil_video.json")
    if not perfil:
        return None
    encaixe = jsonio.ler(proj / "audio" / "encaixe.json", {}) or {}
    return calcular(_cartoes.carregar(video_id, cfg), perfil, encaixe)


def inicio_final(r: dict, lt: dict) -> float | None:
    """Instante, no vídeo final, em que uma fala do relatório de encaixe começa."""
    if r["id"] == "abertura":
        return lt["abertura_fala_s"] if lt["abertura_s"] > 0 else None
    if r["id"] == "encerramento":
        return lt["encerramento_fala_s"]
    return r["inicio_s"] + lt["deslocamento_video_s"]


def segmentos_de_fala(encaixe: dict, lt: dict) -> list[tuple[float, float]]:
    """Intervalos (no tempo do vídeo final) em que há narração."""
    segs = []
    for r in (encaixe or {}).get("falas", []):
        ini = inicio_final(r, lt)
        if ini is None:
            continue
        segs.append((round(ini, 3), round(ini + r["duracao_s"], 3)))
    return sorted(segs)
