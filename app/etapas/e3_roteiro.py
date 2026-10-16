"""Etapa 3: roteiro. A IA escreve; o código calcula janelas e orçamentos e valida."""
import json
import math
import re
import unicodedata

from ..core import claude, config, jsonio
from ..core.caminhos import APP, MODO_TESTE, pasta_projeto, pasta_video

MARGEM_S = 0.15
FATOR = 0.9
JANELA_MIN_S = 2.5
JANELA_MAX_S = 12.0


def orcamento(janela_s: float, car_s: float) -> int:
    """R1: (janela − 0,15 s) × ritmo da voz × 0,9."""
    return max(0, int(math.floor((janela_s - MARGEM_S) * car_s * FATOR)))


def calcular_janelas(mapa: dict, car_s: float) -> list[dict]:
    blocos = [{"inicio_s": c["inicio_s"], "fim_s": c["fim_s"], "cenas": [c["id"]]} for c in mapa["cenas"]]
    # junta cenas curtas com a vizinha
    i = 0
    while i < len(blocos) and len(blocos) > 1:
        b = blocos[i]
        if b["fim_s"] - b["inicio_s"] < JANELA_MIN_S:
            alvo = i + 1 if i + 1 < len(blocos) else i - 1
            a, z = sorted((i, alvo))
            blocos[a] = {"inicio_s": blocos[a]["inicio_s"], "fim_s": blocos[z]["fim_s"],
                         "cenas": blocos[a]["cenas"] + blocos[z]["cenas"]}
            del blocos[z]
            i = max(0, a - 1)
            continue
        i += 1
    # divide janelas longas em partes iguais
    janelas = []
    for b in blocos:
        dur = b["fim_s"] - b["inicio_s"]
        n = max(1, math.ceil(dur / JANELA_MAX_S))
        passo = dur / n
        for k in range(n):
            ini = b["inicio_s"] + k * passo
            fim = b["fim_s"] if k == n - 1 else b["inicio_s"] + (k + 1) * passo
            janelas.append({"inicio_s": round(ini, 2), "fim_s": round(fim, 2), "cenas": b["cenas"],
                            "parte": f"{k + 1}/{n}" if n > 1 else ""})
    for i, j in enumerate(janelas, 1):
        j["id"] = f"j{i:02d}"
        j["orcamento_caracteres"] = orcamento(j["fim_s"] - j["inicio_s"], car_s)
    return janelas


def aplicar_glossario(texto: str, glossario: list) -> str:
    for g in glossario or []:
        termo, falado = (g.get("termo") or "").strip(), (g.get("falado") or "").strip()
        if termo and falado:
            texto = re.sub(rf"(?<!\w){re.escape(termo)}(?!\w)", falado, texto, flags=re.IGNORECASE)
    return texto


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", s).strip()


def _numeros_do_mapa(mapa: dict, briefing: dict) -> set:
    nums = set()
    def add_texto(t):
        for n in re.findall(r"\d+(?:[.,]\d+)*", str(t)):
            for variante in (n.replace(",", "."), n.replace(".", "").replace(",", "."), n.replace(",", "")):
                try:
                    nums.add(float(variante))
                except ValueError:
                    pass
            for parte in re.split(r"[.,]", n):  # "18/23" ou "1.234" também valem por partes
                if parte:
                    nums.add(float(parte))
    for c in mapa["cenas"]:
        for v in c.get("numeros_visiveis", {}).values():
            add_texto(v)
        for t in c.get("texto_visivel", []):
            add_texto(t)
    add_texto(json.dumps(briefing or {}, ensure_ascii=False))
    return nums


def validar(roteiro: dict, mapa: dict, briefing: dict, perfil: dict) -> list[dict]:
    problemas = []
    briefing = briefing or {}
    nums = _numeros_do_mapa(mapa, briefing)
    textos = [roteiro.get("abertura", {})] + roteiro["falas"]
    ab = roteiro.get("abertura", {})
    if ab and len(ab.get("texto_falado", "")) > ab.get("orcamento_caracteres", 10**6):
        problemas.append({"tipo": "estouro", "fala": "abertura",
                          "detalhe": f"abertura com {len(ab['texto_falado'])} caracteres; orçamento {ab['orcamento_caracteres']}"})
    for f in roteiro["falas"]:
        n = len(f["texto_falado"])
        if n > f["orcamento_caracteres"]:
            problemas.append({"tipo": "estouro", "fala": f["janela"],
                              "detalhe": f"{n} caracteres no texto falado; orçamento {f['orcamento_caracteres']} (passou {n - f['orcamento_caracteres']})"})
        citados = list((f.get("numeros_citados") or {}).values())
        citados += re.findall(r"\d+(?:,\d+)?", f["texto_legenda"])
        for v in citados:
            try:
                fv = float(str(v).replace(",", "."))
            except ValueError:
                continue
            if fv not in nums:
                problemas.append({"tipo": "numero", "fala": f["janela"],
                                  "detalhe": f"o número {v} não aparece no mapa de cenas nem no briefing"})
    for termo in briefing.get("nao_mencionar") or []:
        nt = _norm(termo)
        if not nt:
            continue
        for f in textos:
            if nt in _norm(f.get("texto_legenda", "")) or nt in _norm(f.get("texto_falado", "")):
                problemas.append({"tipo": "nao_mencionar", "fala": f.get("janela", "abertura"),
                                  "detalhe": f"menciona \"{termo}\", que está na lista do que não mencionar"})
    falas_por_janela = {f["janela"] for f in roteiro["falas"]}
    janelas = roteiro["janelas"]
    for mk in perfil.get("marcadores", []):
        perto = sorted(janelas, key=lambda j: 0 if j["inicio_s"] <= mk["t_s"] < j["fim_s"]
                       else min(abs(mk["t_s"] - j["inicio_s"]), abs(mk["t_s"] - j["fim_s"])))[:2]
        if not any(j["id"] in falas_por_janela for j in perto):
            problemas.append({"tipo": "marcador", "fala": perto[0]["id"] if perto else "",
                              "detalhe": f"o marcador em {mk['t_s']:.1f} s (\"{mk.get('nota','')}\") ficou sem fala na janela"})
    tudo = _norm(" ".join(f.get("texto_legenda", "") for f in textos))
    for ponto in briefing.get("pontos_obrigatorios") or []:
        palavras = [p for p in _norm(ponto).split() if len(p) >= 4]
        if palavras and not all(p in tudo for p in palavras):
            problemas.append({"tipo": "ponto_obrigatorio", "fala": "",
                              "detalhe": f"o ponto obrigatório \"{ponto}\" não aparece claramente no roteiro"})
    return problemas


def montar(resposta: dict, janelas: list, cfg: dict, car_s: float, calibrado: bool, abertura_info: dict) -> dict:
    por_id = {j["id"]: j for j in janelas}
    glossario = cfg["narracao"].get("glossario", [])
    falas = []
    vistos = set()
    for f in resposta.get("falas", []):
        j = por_id.get(str(f.get("janela")))
        if not j or j["id"] in vistos:
            continue
        vistos.add(j["id"])
        legenda = str(f.get("texto_legenda", "")).strip()
        falado = aplicar_glossario(str(f.get("texto_falado", "") or legenda).strip(), glossario)
        if not legenda and not falado:
            continue
        falas.append({
            "janela": j["id"], "cena": ",".join(j["cenas"]),
            "inicio_s": j["inicio_s"], "fim_s": j["fim_s"],
            "orcamento_caracteres": j["orcamento_caracteres"],
            "texto_legenda": legenda, "texto_falado": falado,
            "numeros_citados": f.get("numeros_citados") or {},
        })
    falas.sort(key=lambda x: x["inicio_s"])
    for i, f in enumerate(falas, 1):
        f["id"] = i
    ab = resposta.get("abertura") or {}
    abertura = dict(abertura_info)
    abertura["texto_legenda"] = str(ab.get("texto_legenda", "")).strip()
    abertura["texto_falado"] = aplicar_glossario(str(ab.get("texto_falado", "") or abertura["texto_legenda"]).strip(), glossario)
    if not abertura.get("orcamento_caracteres"):
        abertura["texto_legenda"] = abertura["texto_falado"] = ""
    v = cfg["voz"]
    return {
        "voz": {"motor": v["motor"],
                "nome": {"elevenlabs": v["elevenlabs"].get("nome"), "kokoro": v.get("kokoro", {}).get("voz")}.get(
                    v["motor"], v["piper"].get("modelo")),
                "ritmo_car_s": round(car_s, 2), "calibrado": calibrado},
        "premissas": [str(p) for p in resposta.get("premissas", []) if str(p).strip()],
        "abertura": abertura,
        "falas": falas,
        "janelas": janelas,
    }


def abertura_info(video_id: str, cfg: dict, car_s: float) -> dict:
    from . import cartoes
    c = cartoes.carregar(video_id, cfg)
    # sem cartão, com fala escrita pelo usuário ou com a fala automática desligada: a IA não escreve a abertura
    if not c["abertura"]["ativo"] or c["abertura"].get("fala") or not c["abertura"].get("fala_auto", True):
        return {"inicio_s": 0.0, "fim_s": 0.0, "orcamento_caracteres": 0, "ativa": False}
    A = float(c["abertura"]["duracao_s"])
    T = min(float(c.get("transicao_s", 0.8)), A - 0.5)
    ini, fim = 0.3, max(1.0, A - max(T, 0) / 2)
    return {"inicio_s": ini, "fim_s": round(fim, 2), "orcamento_caracteres": orcamento(fim - ini, car_s), "ativa": True}


def _roteiro_de_teste(janelas):
    falas = []
    for j in janelas:
        n = int(j["orcamento_caracteres"] * 0.8)
        frase = ("Nesta tela o sistema mostra o próximo passo do fluxo de cadastro e validação. " * 6)[:n].rsplit(" ", 1)[0] + "."
        falas.append({"janela": j["id"], "texto_legenda": frase, "texto_falado": frase, "numeros_citados": {}})
    return {"premissas": ["Modo de teste: roteiro simulado"],
            "abertura": {"texto_legenda": "Produto Demo.", "texto_falado": "Produto Demo."}, "falas": falas}


def executar(tarefa, video_id: str, perfil: dict, instrucoes: str = "") -> dict:
    cfg = config.carregar()
    proj = pasta_projeto(video_id)
    mapa = jsonio.ler(proj / "mapa_de_cenas.json")
    if not mapa:
        raise RuntimeError("Gere o mapa de cenas antes do roteiro")
    briefing = jsonio.ler(pasta_video(video_id) / "briefing.json", {}) or {}
    car_s, calibrado = config.ritmo_voz(cfg)
    janelas = calcular_janelas(mapa, car_s)
    ab_info = abertura_info(video_id, cfg, car_s)
    tarefa.etapa(f"{len(janelas)} janelas de fala; ritmo da voz {car_s:.1f} car/s"
                 + ("" if calibrado else " (voz não calibrada: valor padrão)"), 0.5)
    contexto = {
        "janelas": [{k: j[k] for k in ("id", "inicio_s", "fim_s", "cenas", "orcamento_caracteres", "parte")} for j in janelas],
        "abertura": {"orcamento_caracteres": ab_info["orcamento_caracteres"]},
        "mapa_de_cenas": mapa,
        "briefing": briefing,
        "marcadores": perfil.get("marcadores", []),
        "eventos": perfil.get("eventos", [])[:300],
        "padroes": {k: cfg["narracao"][k] for k in ("idioma", "tom", "persona", "publico")},
        "glossario": cfg["narracao"].get("glossario", []),
        "voz": {"ritmo_car_s": car_s},
    }
    if instrucoes:
        contexto["instrucoes_do_revisor"] = instrucoes
    roteiro_ant = jsonio.ler(proj / "roteiro.json")
    if instrucoes and roteiro_ant:
        contexto["roteiro_anterior"] = {"abertura": roteiro_ant.get("abertura"), "falas": [
            {k: f[k] for k in ("janela", "texto_legenda", "texto_falado")} for f in roteiro_ant.get("falas", [])]}

    modelo = cfg["claude"]["modelos"]["roteiro"]
    prompt = (APP / "prompts" / "roteiro.md").read_text(encoding="utf-8")
    prompt = prompt.replace("{{CONTEXTO}}", json.dumps(contexto, ensure_ascii=False, indent=1))
    if MODO_TESTE:
        resposta = _roteiro_de_teste(janelas)
    else:
        tarefa.etapa(f"Escrevendo o roteiro com {modelo}", 0.55)
        resposta = claude.extrair_json(claude.chamar(
            modelo, prompt, [claude.texto("Escreva o roteiro. Devolva só o JSON.")], 16000,
            proj / "custos.json", "roteiro"))
    roteiro = montar(resposta, janelas, cfg, car_s, calibrado, ab_info)
    problemas = validar(roteiro, mapa, briefing, perfil)
    rodada = 0
    while problemas and rodada < 2 and not MODO_TESTE:
        rodada += 1
        tarefa.etapa(f"Revisão {rodada}: corrigindo {len(problemas)} problema(s)", 0.6 + 0.1 * rodada)
        pedido = ("Seu roteiro tem estes problemas:\n" + "\n".join(f"- [{p['fala']}] {p['detalhe']}" for p in problemas)
                  + "\n\nCorrija somente o necessário e devolva o JSON completo no mesmo formato.\n\nRoteiro atual:\n"
                  + json.dumps({"premissas": roteiro["premissas"],
                                "abertura": {k: roteiro["abertura"][k] for k in ("texto_legenda", "texto_falado")},
                                "falas": [{k: f[k] for k in ("janela", "texto_legenda", "texto_falado", "numeros_citados")}
                                          for f in roteiro["falas"]]}, ensure_ascii=False))
        resposta = claude.extrair_json(claude.chamar(modelo, prompt, [claude.texto(pedido)], 16000,
                                                     proj / "custos.json", f"roteiro revisão {rodada}"))
        roteiro = montar(resposta, janelas, cfg, car_s, calibrado, ab_info)
        problemas = validar(roteiro, mapa, briefing, perfil)
    roteiro["problemas"] = problemas
    jsonio.gravar(proj / "roteiro.json", roteiro)
    # roteiro novo invalida a aprovação anterior
    apr = jsonio.ler(proj / "aprovacoes.json", {}) or {}
    for k in ("roteiro", "voz", "final"):
        apr.pop(k, None)
    jsonio.gravar(proj / "aprovacoes.json", apr)
    tarefa.etapa(f"Roteiro com {len(roteiro['falas'])} falas; {len(problemas)} aviso(s)", 0.9)
    return roteiro


def salvar_edicao(video_id: str, dados: dict) -> dict:
    """Salva o roteiro editado na interface, recalculando contagens e avisos."""
    cfg = config.carregar()
    proj = pasta_projeto(video_id)
    rot = jsonio.ler(proj / "roteiro.json")
    if not rot:
        raise RuntimeError("Roteiro não encontrado")
    por_janela = {j["id"]: j for j in rot["janelas"]}
    novas = []
    for f in dados.get("falas", []):
        j = por_janela.get(f.get("janela"))
        if not j:
            continue
        leg = str(f.get("texto_legenda", "")).strip()
        fal = str(f.get("texto_falado", "")).strip()
        if not leg and not fal:
            continue
        novas.append({"janela": j["id"], "cena": ",".join(j["cenas"]), "inicio_s": j["inicio_s"], "fim_s": j["fim_s"],
                      "orcamento_caracteres": j["orcamento_caracteres"], "texto_legenda": leg or fal,
                      "texto_falado": aplicar_glossario(fal or leg, cfg["narracao"].get("glossario", [])),
                      "numeros_citados": f.get("numeros_citados") or {}})
    novas.sort(key=lambda x: x["inicio_s"])
    for i, f in enumerate(novas, 1):
        f["id"] = i
    rot["falas"] = novas
    if "abertura" in dados:
        rot["abertura"]["texto_legenda"] = str(dados["abertura"].get("texto_legenda", "")).strip()
        rot["abertura"]["texto_falado"] = str(dados["abertura"].get("texto_falado", "")).strip()
    if "premissas" in dados:
        rot["premissas"] = [str(p) for p in dados["premissas"] if str(p).strip()]
    mapa = jsonio.ler(proj / "mapa_de_cenas.json", {"cenas": []})
    briefing = jsonio.ler(pasta_video(video_id) / "briefing.json", {}) or {}
    perfil = jsonio.ler(proj / "perfil_video.json", {}) or {}
    rot["problemas"] = validar(rot, mapa, briefing, perfil)
    jsonio.gravar(proj / "roteiro.json", rot)
    apr = jsonio.ler(proj / "aprovacoes.json", {}) or {}
    apr.pop("roteiro", None)
    apr.pop("final", None)
    jsonio.gravar(proj / "aprovacoes.json", apr)
    return rot
