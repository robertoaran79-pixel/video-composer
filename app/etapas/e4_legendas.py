"""Etapa 4: legendas. Texto exibido (no máximo 2 linhas de 42 caracteres) e texto falado."""
from ..core.caminhos import pasta_projeto

MAX_LINHA = 42
MAX_LINHAS = 2


def quebrar_linhas(texto: str, largura: int = MAX_LINHA) -> list[str]:
    palavras, linhas, atual = texto.split(), [], ""
    for p in palavras:
        if not atual:
            atual = p
        elif len(atual) + 1 + len(p) <= largura:
            atual += " " + p
        else:
            linhas.append(atual)
            atual = p
    if atual:
        linhas.append(atual)
    return linhas


def equilibrar(texto: str) -> list[str]:
    """Duas linhas de tamanho parecido, cada uma com até 42 caracteres."""
    linhas = quebrar_linhas(texto)
    if len(linhas) != 2:
        return linhas
    palavras = texto.split()
    melhor = linhas
    for i in range(1, len(palavras)):
        a, b = " ".join(palavras[:i]), " ".join(palavras[i:])
        if len(a) <= MAX_LINHA and len(b) <= MAX_LINHA and abs(len(a) - len(b)) < abs(len(melhor[0]) - len(melhor[1])):
            melhor = [a, b]
    return melhor


def blocos_de_legenda(texto: str) -> list[list[str]]:
    """Divide um texto longo em blocos de até 2 linhas, preferindo cortar em fim de frase ou vírgula."""
    texto = " ".join(texto.split())
    if len(quebrar_linhas(texto)) <= MAX_LINHAS:
        return [equilibrar(texto)]
    import re
    frases = [f.strip() for f in re.split(r"(?<=[.!?;:,])\s+", texto) if f.strip()]
    blocos, atual = [], ""
    for f in frases:
        tentativa = (atual + " " + f).strip()
        if len(quebrar_linhas(tentativa)) <= MAX_LINHAS:
            atual = tentativa
            continue
        if atual:
            blocos.append(atual)
        if len(quebrar_linhas(f)) <= MAX_LINHAS:
            atual = f
        else:  # frase longa: corta por palavras
            linhas = quebrar_linhas(f)
            for k in range(0, len(linhas), MAX_LINHAS):
                blocos.append(" ".join(linhas[k:k + MAX_LINHAS]))
            atual = ""
    if atual:
        blocos.append(atual)
    return [equilibrar(b) for b in blocos]


def deixas(roteiro: dict, duracoes: dict | None = None, deslocamento: float = 0.0,
           incluir_abertura: bool = False, deslocamento_abertura: float = 0.0) -> list[dict]:
    """Lista de deixas {ini, fim, linhas}. `duracoes`: {id_fala: duração real em s}."""
    car_s = roteiro["voz"]["ritmo_car_s"] or 12
    falas = sorted(roteiro["falas"], key=lambda f: f["inicio_s"])
    res = []
    itens = []
    if incluir_abertura and roteiro.get("abertura", {}).get("texto_legenda"):
        ab = roteiro["abertura"]
        d = (duracoes or {}).get("abertura") or len(ab["texto_falado"]) / car_s
        itens.append((ab["inicio_s"] + deslocamento_abertura, d, ab["fim_s"] + deslocamento_abertura + 0.3,
                      ab["texto_legenda"], None))
    for i, f in enumerate(falas):
        d = (duracoes or {}).get(f["id"]) or len(f["texto_falado"]) / car_s
        # a fala pode ter usado o silêncio até a próxima fala: a legenda acompanha
        limite = (falas[i + 1]["inicio_s"] - 0.05 if i + 1 < len(falas) else f["fim_s"]) + deslocamento
        itens.append((f["inicio_s"] + deslocamento, d, limite, f["texto_legenda"], f["id"]))
    for ini, d, limite, texto, fid in itens:
        fim = min(ini + d + 0.35, limite)
        fim = max(fim, ini + 0.8)
        blocos = blocos_de_legenda(texto)
        total = sum(len(" ".join(b)) for b in blocos) or 1
        t = ini
        for b in blocos:
            dur_b = (fim - ini) * len(" ".join(b)) / total
            res.append({"ini": round(t, 3), "fim": round(t + dur_b, 3), "linhas": b, "fala": fid})
            t += dur_b
    return res


def _tc(s: float) -> str:
    s = max(0.0, s)
    h, r = divmod(int(round(s * 1000)), 3_600_000)
    m, r = divmod(r, 60_000)
    sec, ms = divmod(r, 1000)
    return f"{h:02d}:{m:02d}:{sec:02d},{ms:03d}"


def srt(deixas_: list[dict]) -> str:
    out = []
    for i, d in enumerate(deixas_, 1):
        out.append(f"{i}\n{_tc(d['ini'])} --> {_tc(d['fim'])}\n" + "\n".join(d["linhas"]) + "\n")
    return "\n".join(out)


def executar(video_id: str, roteiro: dict, duracoes: dict | None = None):
    proj = pasta_projeto(video_id)
    (proj / "legendas.srt").write_text(srt(deixas(roteiro, duracoes)), encoding="utf-8")
    car_s = roteiro["voz"]["ritmo_car_s"] or 12
    narr = []
    for f in roteiro["falas"]:
        d = (duracoes or {}).get(f["id"]) or len(f["texto_falado"]) / car_s
        narr.append({"ini": f["inicio_s"], "fim": f["inicio_s"] + d, "linhas": [f["texto_falado"]]})
    (proj / "narracao.srt").write_text(srt(narr), encoding="utf-8")
