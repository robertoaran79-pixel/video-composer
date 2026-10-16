"""Etapa 5: voz. Sintetiza fala por fala com contexto das vizinhas, apara o silêncio,
encaixa na janela (até 30% de aceleração) e guarda em cache."""
import hashlib
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from ..core import claude, config, elevenlabs, jsonio, kokoro, midia, precos, segredos
from ..core.caminhos import MODO_TESTE, PIPER_DIR, pasta_projeto
from . import e3_roteiro, e4_legendas

FRASES_CALIBRACAO = [
    "Nesta tela, o sistema mostra todos os fornecedores cadastrados e a situação de cada um.",
    "Ao clicar em aprovar, a solicitação segue para a próxima etapa do fluxo de validação.",
    "O relatório consolida os resultados do período e destaca o que precisa de atenção.",
]
VOZES_PIPER = [
    {"id": "pt_BR-faber-medium", "nome": "Faber (masculina)"},
    {"id": "pt_BR-cadu-medium", "nome": "Cadu (masculina)"},
    {"id": "pt_BR-jeff-medium", "nome": "Jeff (masculina)"},
    {"id": "pt_BR-edresson-low", "nome": "Edresson (masculina, qualidade baixa)"},
]
MARGEM_S = 0.15
ACELERACAO_LOCAL_DIRETA = 1.10  # até aqui, só ajuste local; acima, pede velocidade à API


def motor_atual(cfg):
    m = cfg["voz"]["motor"]
    if MODO_TESTE and m == "elevenlabs" and not cfg["voz"]["elevenlabs"].get("voice_id"):
        return "teste"
    return m


def _piper_modelo(nome: str) -> Path:
    onnx = PIPER_DIR / f"{nome}.onnx"
    if not onnx.exists():
        PIPER_DIR.mkdir(parents=True, exist_ok=True)
        p = subprocess.run([sys.executable, "-m", "piper.download_voices", nome, "--data-dir", str(PIPER_DIR)],
                           capture_output=True, text=True, timeout=600)
        if p.returncode != 0 or not onnx.exists():
            raise RuntimeError(f"Não foi possível baixar a voz Piper {nome}: {p.stderr[-300:]}")
    return onnx


def sintetizar(cfg, texto: str, saida: Path, velocidade: float = 1.0, anterior: str = "", seguinte: str = "",
               registro: Path | None = None, etapa: str = "voz") -> Path:
    """Gera WAV mono 44,1 kHz já aparado."""
    motor = motor_atual(cfg)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        if motor == "elevenlabs":
            v = cfg["voz"]["elevenlabs"]
            audio = elevenlabs.sintetizar(texto, v["voice_id"], v["modelo"], velocidade, anterior, seguinte)
            (tmp / "a.mp3").write_bytes(audio)
            midia.para_wav(tmp / "a.mp3", saida, aparar=True)
            if registro:
                claude.registrar(registro, {"etapa": etapa, "servico": "elevenlabs", "modelo": v["modelo"],
                                            "caracteres": len(texto),
                                            "usd": round(precos.custo_voz("elevenlabs", v["modelo"], len(texto)), 4)})
        elif motor == "piper":
            modelo = _piper_modelo(cfg["voz"]["piper"]["modelo"])
            p = subprocess.run([sys.executable, "-m", "piper", "-m", str(modelo), "--data-dir", str(PIPER_DIR),
                                "-f", str(tmp / "a.wav"), "--length-scale", f"{1 / max(velocidade, 0.5):.3f}"],
                               input=texto, capture_output=True, text=True, timeout=300)
            if p.returncode != 0:
                raise RuntimeError(f"Piper falhou: {p.stderr[-300:]}")
            midia.para_wav(tmp / "a.wav", saida, aparar=True)
        elif motor == "kokoro":
            kokoro.sintetizar(texto, cfg["voz"].get("kokoro", {}).get("voz", "pf_dora"), tmp / "a.wav", velocidade)
            midia.para_wav(tmp / "a.wav", saida, aparar=True)
        elif motor == "teste":
            midia.tom_de_teste(texto, saida, 11.0, velocidade)
        else:
            raise RuntimeError(f"Motor de voz desconhecido: {motor}")
    return saida


def calibrar(tarefa, video_id: str | None = None) -> dict:
    cfg = config.carregar()
    registro = pasta_projeto(video_id) / "custos.json" if video_id else None
    total_car, total_s, amostras = 0, 0.0, []
    with tempfile.TemporaryDirectory() as tmp:
        for i, frase in enumerate(FRASES_CALIBRACAO, 1):
            tarefa.etapa(f"Calibrando a voz: frase {i} de 3", i / 4)
            arq = sintetizar(cfg, frase, Path(tmp) / f"c{i}.wav", registro=registro, etapa="calibração")
            d = midia.dur_wav(arq)
            amostras.append({"frase": frase, "caracteres": len(frase), "duracao_s": round(d, 2),
                             "car_s": round(len(frase) / d, 2)})
            total_car += len(frase)
            total_s += d
    car_s = round(total_car / total_s, 2)
    chave = config.chave_voz(cfg)
    config.salvar({"voz": {"calibracoes": {chave: {"car_s": car_s, "data": time.strftime("%Y-%m-%d %H:%M"),
                                                   "amostras": amostras}}}})
    return {"chave": chave, "car_s": car_s, "amostras": amostras}


def _hash(*partes) -> str:
    return hashlib.sha1(json.dumps(partes, ensure_ascii=False).encode()).hexdigest()[:16]


def garantir_calibracao(tarefa, video_id: str | None = None) -> float:
    """Calibra a voz automaticamente se a voz escolhida ainda não tiver ritmo medido."""
    cfg = config.carregar()
    car_s, calibrado = config.ritmo_voz(cfg)
    if calibrado:
        return car_s
    tarefa.etapa("Calibrando o ritmo da voz escolhida (automático)", None)
    return calibrar(tarefa, video_id)["car_s"]


CARTOES = ("abertura", "encerramento")


def _itens(roteiro: dict, falas_cartoes: dict, duracao_video: float) -> list[dict]:
    """falas_cartoes: {'abertura': texto falado, 'encerramento': texto falado}. Os cartões esticam
    para caber a fala, então essas duas falas não têm limite de tempo."""
    itens = []
    if falas_cartoes.get("abertura"):
        itens.append({"id": "abertura", "texto": falas_cartoes["abertura"], "inicio_s": 0.3, "fim_s": 60.3,
                      "limite_s": 60.3, "orcamento": 0})
    falas = sorted(roteiro["falas"], key=lambda x: x["inicio_s"])
    for k, f in enumerate(falas):
        # pode ocupar o silêncio até a próxima fala começar (ou até o fim do vídeo)
        limite = falas[k + 1]["inicio_s"] if k + 1 < len(falas) else duracao_video
        itens.append({"id": f["id"], "texto": f["texto_falado"], "inicio_s": f["inicio_s"], "fim_s": f["fim_s"],
                      "limite_s": max(limite, f["fim_s"]), "orcamento": f["orcamento_caracteres"]})
    if falas_cartoes.get("encerramento"):
        itens.append({"id": "encerramento", "texto": falas_cartoes["encerramento"], "inicio_s": 0.0, "fim_s": 60.0,
                      "limite_s": 60.0, "orcamento": 0})
    for i, it in enumerate(itens):
        it["anterior"] = itens[i - 1]["texto"] if i > 0 else ""
        it["seguinte"] = itens[i + 1]["texto"] if i + 1 < len(itens) else ""
    return itens


def encaixar(cfg, it: dict, pasta_audio: Path, registro: Path) -> dict:
    """Encaixe em duas passadas, sem intervenção do usuário:
    1) ritmo natural, usando também o silêncio até a próxima fala;
    2) ajuste local de até 10%; se não bastar, velocidade pedida à API + ajuste local (limite configurado)."""
    motor = motor_atual(cfg)
    chave_voz = config.chave_voz(cfg)
    janela_propria = it["fim_s"] - it["inicio_s"] - MARGEM_S
    janela = it["limite_s"] - it["inicio_s"] - MARGEM_S
    acel_max = float(cfg["voz"]["aceleracao_max"])
    cache = pasta_audio / "cache"
    cache.mkdir(parents=True, exist_ok=True)

    def gerar_audio(vel):
        arq = cache / f"{_hash(chave_voz, it['texto'], round(vel, 3), it['anterior'], it['seguinte'])}.wav"
        novo = not arq.exists()
        if novo:
            sintetizar(cfg, it["texto"], arq, vel, it["anterior"], it["seguinte"], registro)
        return arq, midia.dur_wav(arq), novo

    arq, d1, novo = gerar_audio(1.0)
    vel_api, d_atual, regerada = 1.0, d1, False
    razao = d1 / janela if janela > 0 else 99
    if razao > ACELERACAO_LOCAL_DIRETA and motor in ("elevenlabs", "kokoro", "piper"):
        vel_api = min(1.2, razao)
        arq, d_atual, n2 = gerar_audio(vel_api)
        novo = novo or n2
        regerada = True
    fator_local = max(1.0, d_atual / janela) if janela > 0 else 1.0
    situacao = "ok"
    if vel_api * fator_local > acel_max + 1e-6:
        fator_local = acel_max / vel_api
        situacao = "ESTOURA"
    saida = pasta_audio / f"fala_{it['id']}.wav"
    midia.acelerar(arq, saida, fator_local)
    dur_final = midia.dur_wav(saida)
    if dur_final > janela + 0.02:
        situacao = "ESTOURA"
    return {"id": it["id"], "inicio_s": it["inicio_s"], "janela_s": round(janela_propria + MARGEM_S, 2),
            "disponivel_s": round(janela + MARGEM_S, 2),
            "emprestou_s": round(max(0.0, dur_final - janela_propria), 2),
            "duracao_natural_s": round(d1, 2), "duracao_s": round(dur_final, 2),
            "velocidade": round(vel_api * fator_local, 3), "velocidade_api": round(vel_api, 3),
            "regerada_por_velocidade": regerada, "situacao": situacao, "gerada_agora": novo,
            "caracteres": len(it["texto"]), "orcamento": it["orcamento"], "texto": it["texto"],
            "arquivo": saida.name}


def _encurtar_local(texto: str, maximo: int) -> str:
    if len(texto) <= maximo:
        return texto
    corte = texto[:maximo].rsplit(" ", 1)[0].rstrip(",;: ")
    return corte + ("." if not corte.endswith((".", "!", "?")) else "")


def encurtar_estouros(tarefa, video_id: str, roteiro: dict, estouros: list[dict], itens: dict, cfg) -> int:
    """Pede à IA versões mais curtas das falas que não couberam, com o tamanho medido na voz real."""
    pedidos = []
    for r in estouros:
        if r["id"] in CARTOES:
            continue
        it = itens[r["id"]]
        taxa = max(r["caracteres"] / max(r["duracao_natural_s"], 0.1), 5.0)
        disponivel = it["limite_s"] - it["inicio_s"] - MARGEM_S
        maximo = max(8, int(disponivel * taxa * 0.92))
        if maximo >= r["caracteres"]:
            maximo = r["caracteres"] - max(4, int(r["caracteres"] * 0.12))
        alvo = roteiro["abertura"] if r["id"] == "abertura" else next(f for f in roteiro["falas"] if f["id"] == r["id"])
        pedidos.append({"id": r["id"], "maximo_caracteres_falado": maximo,
                        "texto_legenda": alvo["texto_legenda"], "texto_falado": alvo["texto_falado"], "_alvo": alvo})
    if not pedidos:
        return 0
    proj = pasta_projeto(video_id)
    if MODO_TESTE or not segredos.obter("claude"):
        for p in pedidos:
            p["_alvo"]["texto_falado"] = _encurtar_local(p["texto_falado"], p["maximo_caracteres_falado"])
            p["_alvo"]["texto_legenda"] = _encurtar_local(p["texto_legenda"], max(p["maximo_caracteres_falado"] + 6, 10))
    else:
        tarefa.etapa(f"Encurtando {len(pedidos)} fala(s) que não couberam no tempo da cena", None)
        corpo = [{k: v for k, v in p.items() if not k.startswith("_")} for p in pedidos]
        sistema = ("Você edita narrações de vídeos de demonstração. Reescreva cada fala para caber no limite de "
                   "caracteres do texto falado, mantendo o sentido, os números e a grafia (texto_legenda normal; "
                   "texto_falado com siglas soletradas e números por extenso). Não acrescente informação.")
        pedido = ("Falas que passaram do tempo da cena:\n" + json.dumps(corpo, ensure_ascii=False, indent=1) +
                  '\n\nResponda só com JSON: {"falas": [{"id": ..., "texto_legenda": "...", "texto_falado": "..."}]}')
        resp = claude.extrair_json(claude.chamar(cfg["claude"]["modelos"]["roteiro"], sistema, [claude.texto(pedido)],
                                                 4000, proj / "custos.json", "voz: encurtar falas"))
        novos = {str(f.get("id")): f for f in resp.get("falas", [])}
        for p in pedidos:
            n = novos.get(str(p["id"]))
            if not n:
                continue
            falado = e3_roteiro.aplicar_glossario(str(n.get("texto_falado", "")).strip(), cfg["narracao"].get("glossario", []))
            if not falado:
                continue
            if len(falado) > p["maximo_caracteres_falado"]:
                falado = _encurtar_local(falado, p["maximo_caracteres_falado"])
            p["_alvo"]["texto_falado"] = falado
            p["_alvo"]["texto_legenda"] = str(n.get("texto_legenda", "")).strip() or falado
    for p in pedidos:
        p["_alvo"]["ajustada_automaticamente"] = True
    return len(pedidos)


def gerar(tarefa, video_id: str, somente_previa: bool = False, corrigir: bool = True) -> dict:
    from . import cartoes
    cfg = config.carregar()
    proj = pasta_projeto(video_id)
    roteiro = jsonio.ler(proj / "roteiro.json")
    if not roteiro:
        raise RuntimeError("Gere o roteiro antes da voz")
    perfil = jsonio.ler(proj / "perfil_video.json")
    cart = cartoes.carregar(video_id, cfg)

    def falas_cartoes():
        t = cartoes.textos_fala(video_id, cart, roteiro, cfg)
        return {k: t[k][1] for k in CARTOES}
    pasta_audio = proj / "audio"
    pasta_audio.mkdir(exist_ok=True)

    def rodada(lista, base, peso):
        res = []
        for n, it in enumerate(lista, 1):
            tarefa.etapa(f"Voz: fala {it['id']} ({n} de {len(lista)})", base + peso * n / max(len(lista), 1))
            res.append(encaixar(cfg, it, pasta_audio, proj / "custos.json"))
        return res

    itens = _itens(roteiro, falas_cartoes(), perfil["duracao_s"])
    if somente_previa:
        resultados = rodada([i for i in itens if i["id"] not in CARTOES][:3], 0.05, 0.9)
        jsonio.gravar(pasta_audio / "previa.json", resultados)
        return {"previa": resultados}

    resultados = rodada(itens, 0.05, 0.6)
    ajustadas = 0
    for volta in range(2):
        estouros = [r for r in resultados if r["situacao"] == "ESTOURA"]
        if not estouros or not corrigir:
            break
        ajustadas += encurtar_estouros(tarefa, video_id, roteiro, estouros, {i["id"]: i for i in itens}, cfg)
        mapa = jsonio.ler(proj / "mapa_de_cenas.json", {"cenas": []})
        from ..core.caminhos import pasta_video
        briefing = jsonio.ler(pasta_video(video_id) / "briefing.json", {}) or {}
        roteiro["problemas"] = e3_roteiro.validar(roteiro, mapa, briefing, perfil)
        jsonio.gravar(proj / "roteiro.json", roteiro)
        itens = _itens(roteiro, falas_cartoes(), perfil["duracao_s"])
        resultados = rodada(itens, 0.65 + 0.12 * volta, 0.12)

    for r in resultados:
        if r["id"] in CARTOES:  # cartões esticam para caber a fala: sem janela fixa
            r["janela_s"] = r["disponivel_s"] = r["duracao_s"]
            r["emprestou_s"] = 0.0
    tarefa.etapa("Montando a faixa de narração", 0.93)
    trechos = [(r["inicio_s"], pasta_audio / r["arquivo"]) for r in resultados if r["id"] not in CARTOES]
    midia.montar_linha_do_tempo(trechos, perfil["duracao_s"], proj / "narracao.wav")
    for k in CARTOES:
        r = next((x for x in resultados if x["id"] == k), None)
        if r:
            (proj / f"{k}.wav").write_bytes((pasta_audio / r["arquivo"]).read_bytes())
        else:
            (proj / f"{k}.wav").unlink(missing_ok=True)
    linhas = ["fala\tinicio_s\tjanela_s\tdisponivel_s\tduracao_s\tvelocidade\tsituacao\ttexto"]
    for r in resultados:
        linhas.append(f"{r['id']}\t{r['inicio_s']:.2f}\t{r['janela_s']:.2f}\t{r['disponivel_s']:.2f}\t{r['duracao_s']:.2f}\t"
                      f"{r['velocidade']:.3f}\t{r['situacao']}\t{r['texto']}")
    (proj / "relatorio_encaixe.tsv").write_text("\n".join(linhas) + "\n", encoding="utf-8")
    falas = [r for r in resultados if r["id"] not in CARTOES]
    medidas = [r["caracteres"] / r["duracao_natural_s"] for r in falas if r["duracao_natural_s"] > 0.5]
    resumo = {
        "falas": len(falas),
        "no_ritmo_natural": sum(1 for r in falas if r["velocidade"] <= 1.001),
        "aceleradas": sum(1 for r in falas if r["velocidade"] > 1.001),
        "usaram_silencio_seguinte": sum(1 for r in falas if r["emprestou_s"] > 0.05),
        "encurtadas_pela_ia": ajustadas,
        "estouros": sum(1 for r in resultados if r["situacao"] == "ESTOURA"),
        "geradas_agora": sum(1 for r in resultados if r["gerada_agora"]),
        "do_cache": sum(1 for r in resultados if not r["gerada_agora"]),
        "ritmo_medido_car_s": round(sum(medidas) / len(medidas), 2) if medidas else None,
    }
    jsonio.gravar(pasta_audio / "encaixe.json", {"resumo": resumo, "falas": resultados,
                                                 "voz": config.chave_voz(cfg)})
    duracoes = {r["id"]: r["duracao_s"] for r in resultados}
    e4_legendas.executar(video_id, roteiro, duracoes)
    apr = jsonio.ler(proj / "aprovacoes.json", {}) or {}
    apr.pop("voz", None)
    apr.pop("final", None)
    jsonio.gravar(proj / "aprovacoes.json", apr)
    return resumo
