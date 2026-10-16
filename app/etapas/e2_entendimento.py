"""Etapa 2: entendimento do vídeo.

Determinístico: detecção de trocas de cena, amostragem adaptativa (1 quadro a
cada 2 s + quadros logo após cada troca + marcadores), pranchas de 12 quadros
com o instante escrito em cada um e quadros em alta resolução nos pontos-chave.
IA de visão: lê as pranchas e devolve o mapa_de_cenas.json.
"""
import json
import shutil
from concurrent.futures import ThreadPoolExecutor

from PIL import Image, ImageDraw, ImageFont

from ..core import claude, config, jsonio, midia
from ..core.caminhos import APP, MODO_TESTE, pasta_projeto, pasta_video

COLS, LINHAS = 4, 3
TILE_W, TILE_H, BARRA = 480, 270, 26
ALTA_RES = 1568
TIPOS = {"abertura", "navegacao", "preenchimento", "espera", "resultado", "transicao"}


def _fonte(tam):
    for f in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(f, tam)
        except OSError:
            continue
    return ImageFont.load_default()


def escolher_tempos(dur: float, trocas, marcadores, eventos) -> list[dict]:
    cand = []
    t = 1.0
    while t < dur - 0.3:
        cand.append({"t": round(t, 2), "motivo": "amostra"})
        t += 2.0
    for tt, _s in trocas:
        if 0.3 < tt + 0.4 < dur - 0.1:
            cand.append({"t": round(tt + 0.4, 2), "motivo": "troca de cena"})
    for mk in marcadores:
        cand.append({"t": round(min(max(mk["t_s"], 0.1), dur - 0.2), 2), "motivo": "marcador"})
    for ev in eventos:
        if ev.get("tipo") in ("clique", "navegacao"):
            cand.append({"t": round(min(ev["t_s"] + 0.6, dur - 0.2), 2), "motivo": "evento"})
    cand.append({"t": round(max(dur - 0.3, 0), 2), "motivo": "fim"})
    prioridade = {"marcador": 0, "fim": 1, "troca de cena": 2, "evento": 3, "amostra": 4}
    cand.sort(key=lambda c: (c["t"], prioridade[c["motivo"]]))
    res = []
    for c in cand:
        if res and c["t"] - res[-1]["t"] < 0.8:
            if prioridade[c["motivo"]] < prioridade[res[-1]["motivo"]]:
                res[-1] = c
            continue
        res.append(c)
    return res


def montar_pranchas(quadros: list[dict], pasta) -> list[dict]:
    fonte = _fonte(17)
    por = COLS * LINHAS
    pranchas = []
    for i in range(0, len(quadros), por):
        grupo = quadros[i:i + por]
        img = Image.new("RGB", (COLS * TILE_W, LINHAS * (TILE_H + BARRA)), (20, 20, 20))
        d = ImageDraw.Draw(img)
        for j, q in enumerate(grupo):
            x = (j % COLS) * TILE_W
            y = (j // COLS) * (TILE_H + BARRA)
            try:
                tile = Image.open(q["arquivo"]).convert("RGB")
                tile.thumbnail((TILE_W, TILE_H))
                img.paste(tile, (x, y + BARRA))
            except OSError:
                pass
            rot = f"#{q['n']}  t={q['t']:.1f} s" + ("  ★ marcador" if q["motivo"] == "marcador" else "")
            d.rectangle([x, y, x + TILE_W - 1, y + BARRA - 1], fill=(0, 0, 0))
            d.text((x + 8, y + 4), rot, fill=(255, 230, 80), font=fonte)
            d.rectangle([x, y, x + TILE_W - 1, y + TILE_H + BARRA - 1], outline=(70, 70, 70))
        nome = pasta / f"prancha_{len(pranchas) + 1:02d}.jpg"
        img.save(nome, quality=82)
        pranchas.append({"arquivo": nome, "quadros": [(q["n"], q["t"]) for q in grupo]})
    return pranchas


def escolher_alta_res(trocas, marcadores, dur, maximo=4) -> list[float]:
    ts = [mk["t_s"] for mk in marcadores][:maximo]
    for tt, _s in sorted(trocas, key=lambda x: -x[1]):
        if len(ts) >= maximo - 1:
            break
        alvo = min(tt + 1.0, dur - 0.3)
        if all(abs(alvo - x) > 3 for x in ts):
            ts.append(alvo)
    fim = max(dur - 0.5, 0)
    if all(abs(fim - x) > 3 for x in ts) and len(ts) < maximo:
        ts.append(fim)
    return sorted(round(t, 2) for t in ts)


def normalizar_mapa(bruto: dict, perfil: dict) -> dict:
    dur = perfil["duracao_s"]
    cenas = []
    for c in sorted(bruto.get("cenas", []), key=lambda x: float(x.get("inicio_s", 0))):
        ini = max(0.0, min(float(c.get("inicio_s", 0)), dur))
        fim = max(0.0, min(float(c.get("fim_s", ini)), dur))
        if fim - ini < 0.3:
            continue
        nums = {}
        for k, v in (c.get("numeros_visiveis") or {}).items():
            if isinstance(v, (int, float)) or (isinstance(v, str) and v.strip()):
                nums[str(k)] = v
        tipo = str(c.get("tipo", "navegacao")).lower()
        cenas.append({
            "inicio_s": round(ini, 2), "fim_s": round(fim, 2),
            "tela": str(c.get("tela", ""))[:120], "acao": str(c.get("acao", ""))[:400],
            "texto_visivel": [str(x)[:200] for x in (c.get("texto_visivel") or [])][:25],
            "numeros_visiveis": nums,
            "tipo": tipo if tipo in TIPOS else "navegacao",
            "importancia": c.get("importancia") if c.get("importancia") in ("alta", "media", "baixa") else "media",
            "observacoes": str(c.get("observacoes", ""))[:300],
        })
    if not cenas:
        raise RuntimeError("O modelo não devolveu cenas válidas")
    # contiguidade: sem buracos nem sobreposição
    cenas[0]["inicio_s"] = 0.0
    for a, b in zip(cenas, cenas[1:]):
        meio = round((a["fim_s"] + b["inicio_s"]) / 2, 2) if a["fim_s"] < b["inicio_s"] else b["inicio_s"]
        a["fim_s"] = meio
        b["inicio_s"] = meio
    cenas[-1]["fim_s"] = round(dur, 2)
    cenas = [c for c in cenas if c["fim_s"] - c["inicio_s"] >= 0.3]
    for i, c in enumerate(cenas, 1):
        c["id"] = f"c{i:02d}"
    return {
        "video": {"duracao_s": dur, "fps_real": perfil["fps"], "resolucao": perfil["resolucao"],
                  "taxa_variavel_na_origem": perfil.get("taxa_variavel", False)},
        "resumo": str(bruto.get("resumo", ""))[:400],
        "produto": str(bruto.get("produto", ""))[:80],
        "cenas": cenas,
    }


def _mapa_de_teste(perfil, trocas):
    dur = perfil["duracao_s"]
    limites = [0.0] + [t for t, _ in trocas if 3 < t < dur - 3] + [dur]
    cenas, ini = [], 0.0
    for b in limites[1:]:
        if b - ini < 4 and b != dur:
            continue
        cenas.append({"inicio_s": ini, "fim_s": b, "tela": f"Tela {len(cenas) + 1}",
                      "acao": "Usuário navega pelo sistema (modo de teste)", "texto_visivel": [],
                      "numeros_visiveis": {"itens": len(cenas) + 3} if len(cenas) % 3 == 2 else {},
                      "tipo": "resultado" if len(cenas) % 3 == 2 else "navegacao", "importancia": "media"})
        ini = b
    return {"resumo": "Demonstração (modo de teste)", "produto": "Produto Demo", "cenas": cenas}


def executar(tarefa, video_id: str, perfil: dict) -> dict:
    cfg = config.carregar()
    proj = pasta_projeto(video_id)
    base = proj / "base.mp4"
    pasta_q = proj / "quadros"
    if pasta_q.exists():
        shutil.rmtree(pasta_q)
    pasta_q.mkdir()
    dur = perfil["duracao_s"]

    tarefa.etapa("Detectando trocas de cena", 0.08)
    trocas = midia.trocas_de_cena(base)
    tempos = escolher_tempos(dur, trocas, perfil["marcadores"], perfil["eventos"])
    tarefa.etapa(f"Extraindo {len(tempos)} quadros ({len(trocas)} trocas de cena)", 0.15)
    for i, q in enumerate(tempos, 1):
        q["n"] = i
        q["arquivo"] = pasta_q / f"q{i:03d}.jpg"
    with ThreadPoolExecutor(max_workers=4) as ex:
        list(ex.map(lambda q: midia.quadro(base, q["t"], q["arquivo"], TILE_W), tempos))
    pranchas = montar_pranchas(tempos, pasta_q)
    alta = escolher_alta_res(trocas, perfil["marcadores"], dur)
    arquivos_alta = []
    for i, t in enumerate(alta, 1):
        arq = pasta_q / f"alta_{i}.jpg"
        midia.quadro(base, t, arq, ALTA_RES, qualidade=3)
        arquivos_alta.append((t, arq))
    tarefa.etapa(f"{len(pranchas)} pranchas e {len(arquivos_alta)} quadros em alta resolução prontos", 0.22)

    briefing = jsonio.ler(pasta_video(video_id) / "briefing.json", {}) or {}
    contexto = {
        "duracao_s": dur,
        "trocas_de_cena_detectadas_s": [t for t, _ in trocas][:200],
        "pranchas": [{"prancha": i + 1, "quadros": [{"n": n, "t_s": t} for n, t in p["quadros"]]}
                     for i, p in enumerate(pranchas)],
        "quadros_alta_resolucao_s": [t for t, _ in arquivos_alta],
        "marcadores_do_usuario": perfil["marcadores"],
        "eventos_de_navegacao": perfil["eventos"][:300],
        "briefing": briefing,
    }

    if MODO_TESTE:
        tarefa.etapa("Modo de teste: mapa de cenas simulado", 0.4)
        bruto = _mapa_de_teste(perfil, trocas)
    else:
        prompt = (APP / "prompts" / "entendimento.md").read_text(encoding="utf-8")
        prompt = prompt.replace("{{CONTEXTO}}", json.dumps(contexto, ensure_ascii=False, indent=1))
        conteudo = []
        for i, p in enumerate(pranchas, 1):
            conteudo.append(claude.texto(f"Prancha {i}:"))
            conteudo.append(claude.imagem(p["arquivo"]))
        for t, arq in arquivos_alta:
            conteudo.append(claude.texto(f"Quadro em alta resolução, t={t:.1f} s:"))
            conteudo.append(claude.imagem(arq))
        conteudo.append(claude.texto("Devolva somente o JSON do mapa de cenas."))
        modelo = cfg["claude"]["modelos"]["entendimento"]
        tarefa.etapa(f"Lendo a tela com {modelo} ({len(pranchas)} pranchas)", 0.3)
        resposta = claude.chamar(modelo, prompt, conteudo, max_tokens=16000,
                                 registro=proj / "custos.json", etapa="entendimento")
        try:
            bruto = claude.extrair_json(resposta)
        except claude.ErroClaude:
            tarefa.etapa("JSON inválido, pedindo de novo", 0.4)
            conteudo.append(claude.texto("Sua resposta anterior não era um JSON válido. Responda só com o JSON."))
            bruto = claude.extrair_json(claude.chamar(modelo, prompt, conteudo, 16000, proj / "custos.json", "entendimento"))
    mapa = normalizar_mapa(bruto, perfil)
    jsonio.gravar(proj / "mapa_de_cenas.json", mapa)
    tarefa.etapa(f"Mapa de cenas com {len(mapa['cenas'])} cenas", 0.45)
    return mapa
