"""Video Composer: API e interface web (porta 8898)."""
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

from fastapi import Body, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from .core import catalogo_musica, claude, eleven_music, finalidades, kokoro, config, elevenlabs, jsonio, midia, precos, segredos, tarefas
from .core.caminhos import (APP, EXPORTADOS, MARCAS, MODO_TESTE, MUSICA, TRABALHO, dentro, garantir_pastas,
                            nome_seguro, pasta_projeto, pasta_video)
from .etapas import (capa, cartoes, e0_gravacao, linha_do_tempo, e1_perfil, e2_entendimento, e3_roteiro, e4_legendas, e5_voz, e6_trilha,
                     e7_edicao, e8_qa)

garantir_pastas()
app = FastAPI(title="Video Composer", docs_url="/api/docs", openapi_url="/api/openapi.json")


@app.exception_handler(ValueError)
async def _erro_valor(_req, exc):
    return JSONResponse({"detail": str(exc)}, status_code=400)


@app.exception_handler(FileNotFoundError)
async def _erro_arquivo(_req, exc):
    return JSONResponse({"detail": str(exc) or "Não encontrado"}, status_code=404)


@app.exception_handler(RuntimeError)
async def _erro_execucao(_req, exc):
    return JSONResponse({"detail": str(exc)}, status_code=409)


def _video_existe(video_id: str):
    if not e0_gravacao.meta(video_id):
        raise HTTPException(404, "Vídeo não encontrado")


async def _receber(request: Request, destino: Path, limite_mb: int = 8000) -> int:
    total = 0
    with open(destino, "wb") as f:
        async for parte in request.stream():
            total += len(parte)
            if total > limite_mb * 1_048_576:
                f.close()
                destino.unlink(missing_ok=True)
                raise HTTPException(413, "Arquivo grande demais")
            f.write(parte)
    return total


# ---------------- sistema e configurações ----------------

@app.get("/api/sistema")
def sistema():
    host = os.environ.get("VC_PASTA_HOST", "")
    uso = shutil.disk_usage(TRABALHO)
    alerta_nuvem = ""
    h = host.lower()
    if any(x in h for x in ("mobile documents", "icloud", "onedrive", "dropbox", "google drive", "googledrive")):
        alerta_nuvem = "A pasta de trabalho está numa pasta sincronizada na nuvem. Vídeos são grandes e podem travar a sincronização."
    elif "/documents/" in h or "/desktop/" in h:
        alerta_nuvem = ("A pasta de trabalho está em Documentos ou Mesa. Se \"Mesa e Documentos do iCloud\" estiver ligado "
                        "no Mac, ela sincroniza com a nuvem e vídeos grandes podem travar a sincronização.")
    try:
        ff = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True).stdout.split("\n")[0]
    except OSError:
        ff = "FFmpeg não encontrado"
    return {"pasta_trabalho_host": host or str(TRABALHO), "pasta_trabalho": str(TRABALHO),
            "livre_gb": round(uso.free / 1e9, 1), "alerta_nuvem": alerta_nuvem, "ffmpeg": ff,
            "modo_teste": MODO_TESTE, "versao": "versão 0.4"}


@app.get("/api/config")
def ler_config():
    cfg = config.carregar()
    car_s, calibrado = config.ritmo_voz(cfg)
    return {"config": cfg, "segredos": segredos.resumo(), "modelos_claude": precos.MODELOS_CLAUDE,
            "modelos_eleven": precos.MODELOS_ELEVEN, "vozes_piper": e5_voz.VOZES_PIPER,
            "vozes_kokoro": kokoro.VOZES, "kokoro_instalado": kokoro.disponivel(),
            "ritmo": {"car_s": car_s, "calibrado": calibrado, "chave": config.chave_voz(cfg)}}


@app.put("/api/config")
def gravar_config(dados: dict = Body(...)):
    return {"config": config.salvar(dados)}


@app.put("/api/segredos")
def gravar_segredos(dados: dict = Body(...)):
    for nome in ("claude", "elevenlabs"):
        if nome in dados and dados[nome] is not None:
            segredos.definir(nome, str(dados[nome]))
    return segredos.resumo()


@app.post("/api/testar/{servico}")
def testar(servico: str):
    if servico == "claude":
        return claude.testar()
    if servico == "elevenlabs":
        return elevenlabs.testar()
    raise HTTPException(404, "Serviço desconhecido")


@app.get("/api/vozes")
def vozes():
    return {"vozes": elevenlabs.listar_vozes()}


@app.post("/api/voz/calibrar")
def calibrar(dados: dict = Body(default={})):
    t = tarefas.iniciar("calibrar", None, e5_voz.calibrar, dados.get("video_id"))
    return t.dict()


@app.get("/api/voz/amostra")
def amostra_voz():
    """Gera uma frase de exemplo com a voz configurada (para ouvir antes de escolher)."""
    cfg = config.carregar()
    destino = TRABALHO / ".amostra_voz.wav"
    e5_voz.sintetizar(cfg, e5_voz.FRASES_CALIBRACAO[0], destino)
    return FileResponse(destino, media_type="audio/wav", headers={"Cache-Control": "no-store"})


# ---------------- arquivos de marca e música ----------------

EXT_MARCA = {".png", ".jpg", ".jpeg", ".webp"}


@app.get("/api/marcas/arquivos")
def arquivos_marca():
    return {"arquivos": sorted(p.name for p in MARCAS.glob("*") if p.suffix.lower() in EXT_MARCA)}


@app.post("/api/marcas/arquivos")
async def enviar_marca(request: Request, nome: str):
    nome = nome_seguro(nome)
    if Path(nome).suffix.lower() not in EXT_MARCA:
        raise HTTPException(400, "Use PNG, JPG ou WEBP")
    await _receber(request, MARCAS / nome, 50)
    return {"arquivo": nome}


@app.get("/api/marcas/arquivo/{nome}")
def ver_marca(nome: str):
    return FileResponse(dentro(MARCAS, nome))


@app.get("/api/musicas")
def musicas():
    return {"musicas": e6_trilha.listar_musicas()}


@app.post("/api/musicas")
async def enviar_musica(request: Request, nome: str):
    nome = nome_seguro(nome)
    if Path(nome).suffix.lower() not in e6_trilha.EXT_MUSICA | {".txt"}:
        raise HTTPException(400, "Use MP3, WAV, M4A, AAC, FLAC, OGG ou TXT (licença)")
    await _receber(request, MUSICA / nome, 300)
    return {"arquivo": nome}


@app.get("/api/musicas/catalogo")
def catalogo(q: str = "", licenca: str = "livre", duracao: str = "medium,long", pagina: int = 1):
    try:
        return catalogo_musica.buscar(q, licenca, duracao, pagina)
    except catalogo_musica.ErroCatalogo as e:
        raise HTTPException(502, str(e)) from e


@app.get("/api/musicas/catalogo/sugestoes")
def sugestoes_musica():
    return {"sugestoes": catalogo_musica.SUGESTOES}


@app.post("/api/musicas/catalogo/baixar")
def baixar_musica(dados: dict = Body(...)):
    def baixar(tarefa, item, usar):
        tarefa.etapa(f"Baixando \"{item.get('titulo', '')}\"", 0.2)
        meta = catalogo_musica.baixar(item)
        if usar:
            config.salvar({"musica": {"arquivo": meta["arquivo"]}})
        return meta
    t = tarefas.iniciar("download de música", None, baixar, dados.get("item") or {}, bool(dados.get("usar")))
    return t.dict()


@app.get("/api/musicas/gerar/info")
def info_musica_gerada(video_id: str = ""):
    estilos = [{"id": k, "nome": v[0]} for k, v in eleven_music.ESTILOS.items()]
    dur = 0.0
    if video_id:
        perfil = jsonio.ler(pasta_projeto(video_id) / "perfil_video.json")
        if perfil:
            dur = linha_do_tempo.do_projeto(video_id)["total_s"]
        else:
            m = e0_gravacao.meta(video_id) or {}
            dur = float(m.get("duracao_s") or 0) + 6
    return {"estilos": estilos, "plano": eleven_music.plano() if segredos.obter("elevenlabs") or MODO_TESTE else
            {"tier": "", "erro": "Informe a chave da ElevenLabs em Configurações"},
            "duracao_s": round(dur, 1), "custo_usd": round(max(dur, 10) / 60 * precos.ELEVEN_MUSIC_USD_MIN, 2)}


@app.post("/api/projetos/{video_id}/musica/gerar")
def gerar_musica(video_id: str, dados: dict = Body(default={})):
    _video_existe(video_id)

    def gerar(tarefa):
        perfil = jsonio.ler(pasta_projeto(video_id) / "perfil_video.json")
        if perfil:
            dur = linha_do_tempo.do_projeto(video_id)["total_s"]
        else:
            dur = float((e0_gravacao.meta(video_id) or {}).get("duracao_s") or 60) + 6
        tarefa.etapa(f"Compondo {dur:.0f} s de música no Eleven Music", 0.2)
        meta = eleven_music.compor(dados.get("estilo", "corporativo"), dados.get("descricao", ""), dur,
                                   video_id[-4:], pasta_projeto(video_id) / "custos.json")
        config.salvar({"musica": {"arquivo": meta["arquivo"]}})
        return meta
    t = tarefas.iniciar("música gerada", video_id, gerar)
    return t.dict()


@app.post("/api/musicas/{nome}/confirmar")
def confirmar_licenca(nome: str, dados: dict = Body(default={})):
    dentro(MUSICA, nome)
    return catalogo_musica.confirmar_licenca(nome, str(dados.get("origem_licenca", "")))


@app.delete("/api/musicas/{nome}")
def apagar_musica(nome: str):
    arq = dentro(MUSICA, nome)
    for p in (arq, arq.with_suffix(".txt"), arq.with_suffix(".json")):
        p.unlink(missing_ok=True)
    if config.carregar()["musica"].get("arquivo") == nome:
        config.salvar({"musica": {"arquivo": ""}})
    return {"ok": True}


@app.get("/api/musicas/{nome}")
def ouvir_musica(nome: str):
    return FileResponse(dentro(MUSICA, nome))


# ---------------- gravação e biblioteca ----------------

@app.post("/api/gravacoes")
def iniciar_gravacao(dados: dict = Body(default={})):
    return e0_gravacao.criar(dados.get("nome", ""), "aba do Chrome", dados.get("url_inicial", ""))


@app.post("/api/gravacoes/{video_id}/bloco")
async def bloco(video_id: str, seq: int, request: Request):
    _video_existe(video_id)
    corpo = await request.body()
    return {"seq": e0_gravacao.anexar_bloco(video_id, seq, corpo)}


@app.post("/api/gravacoes/{video_id}/finalizar")
def finalizar_gravacao(video_id: str, dados: dict = Body(default={})):
    _video_existe(video_id)
    if not (pasta_video(video_id) / "bruto.webm").exists():
        raise HTTPException(400, "Nenhum bloco de vídeo recebido")
    t = tarefas.iniciar("converter", video_id, e0_gravacao.converter, video_id, "bruto.webm", dados)
    return t.dict()


@app.post("/api/biblioteca/importar")
async def importar(request: Request, nome: str):
    m, destino = e0_gravacao.preparar_importacao(nome)
    try:
        await _receber(request, destino)
    except Exception:
        e0_gravacao.apagar(m["id"])
        raise
    t = tarefas.iniciar("converter", m["id"], e0_gravacao.converter, m["id"], destino.name)
    return {"video": m, "tarefa": t.dict()}


@app.get("/api/biblioteca")
def biblioteca():
    return {"videos": e0_gravacao.listar()}


@app.patch("/api/biblioteca/{video_id}")
def atualizar_video(video_id: str, dados: dict = Body(...)):
    return e0_gravacao.atualizar(video_id, dados)


@app.delete("/api/biblioteca/{video_id}")
def apagar_video(video_id: str):
    t = tarefas.do_video(video_id)
    if t and t.situacao == "rodando":
        raise HTTPException(409, "Há uma tarefa em andamento para este vídeo")
    e0_gravacao.apagar(video_id)
    return {"ok": True}


@app.get("/api/biblioteca/{video_id}/video")
def ver_video(video_id: str):
    p = pasta_video(video_id) / "video.mp4"
    if not p.exists():
        raise HTTPException(404, "Vídeo ainda não convertido")
    return FileResponse(p, media_type="video/mp4")


@app.get("/api/biblioteca/{video_id}/miniatura")
def miniatura(video_id: str):
    p = pasta_video(video_id) / "miniatura.jpg"
    if not p.exists():
        raise HTTPException(404)
    return FileResponse(p, media_type="image/jpeg")


@app.get("/api/biblioteca/{video_id}/quadro")
def quadro(video_id: str, t: float, base: int = 1, largura: int = 320):
    """Quadro do vídeo-base do projeto (base=1) ou do vídeo original (base=0)."""
    pv = pasta_video(video_id)
    origem = pv / "projeto" / "base.mp4" if base and (pv / "projeto" / "base.mp4").exists() else pv / "video.mp4"
    cache = pv / "projeto" / "cache_quadros"
    cache.mkdir(parents=True, exist_ok=True)
    largura = max(120, min(int(largura), 1280))
    arq = cache / f"{'b' if base else 'o'}_{t:.2f}_{largura}.jpg"
    if not arq.exists():
        midia.quadro(origem, t, arq, largura)
    return FileResponse(arq, media_type="image/jpeg")


# ---------------- projeto (pipeline) ----------------

def _estimativa(video_id: str) -> dict:
    cfg = config.carregar()
    m = e0_gravacao.meta(video_id)
    cortes = m["cortes"] if m.get("cortes_manuais") or not m.get("cortes_automaticos") else m["cortes_automaticos"]
    ini = float(cortes.get("inicio_s") or 0)
    fim = float(cortes.get("fim_s") or m["duracao_s"] or 0)
    car_s, _ = config.ritmo_voz(cfg)
    return precos.estimar(max(fim - ini, 1), cfg, car_s)


@app.get("/api/projetos/{video_id}")
def projeto(video_id: str):
    _video_existe(video_id)
    pv = pasta_video(video_id)
    proj = pasta_projeto(video_id)
    t = tarefas.do_video(video_id)
    custos = jsonio.ler(proj / "custos.json", []) or []
    qa_md = (proj / "relatorio_qa.md").read_text(encoding="utf-8") if (proj / "relatorio_qa.md").exists() else ""
    return {
        "video": e0_gravacao.meta(video_id),
        "situacao": e0_gravacao.situacao_projeto(video_id),
        "briefing": jsonio.ler(pv / "briefing.json", {}) or {},
        "perfil": jsonio.ler(proj / "perfil_video.json"),
        "mapa": jsonio.ler(proj / "mapa_de_cenas.json"),
        "roteiro": jsonio.ler(proj / "roteiro.json"),
        "previa": jsonio.ler(proj / "audio" / "previa.json"),
        "encaixe": jsonio.ler(proj / "audio" / "encaixe.json"),
        "montagem": jsonio.ler(proj / "montagem.json"),
        "qa": jsonio.ler(proj / "qa.json"),
        "qa_md": qa_md,
        "aprovacoes": jsonio.ler(proj / "aprovacoes.json", {}) or {},
        "tem_video_final": (proj / "video_final.mp4").exists(),
        "cartoes": cartoes.carregar(video_id),
        "capa": capa.carregar(video_id),
        "custos": {"itens": custos, "total_usd": round(sum(c.get("usd", 0) for c in custos), 3)},
        "estimativa": _estimativa(video_id),
        "tarefa": t.dict() if t else None,
    }


@app.put("/api/projetos/{video_id}/briefing")
def salvar_briefing(video_id: str, dados: dict = Body(...)):
    _video_existe(video_id)
    campos = {"texto_livre": "", "finalidade": "", "publico": "", "objetivo": "", "pontos_obrigatorios": [],
              "nao_mencionar": [], "tom": "", "idioma": "", "duracao_alvo_s": None}
    b = {}
    for k, padrao in campos.items():
        v = dados.get(k, padrao)
        if k == "finalidade" and v and v not in finalidades.POR_ID:
            v = ""
        if isinstance(padrao, list):
            v = [str(x).strip() for x in (v or []) if str(x).strip()]
        elif k == "duracao_alvo_s":
            v = float(v) if v not in (None, "") else None
        else:
            v = str(v or "").strip()
        b[k] = v
    b = finalidades.aplicar(b)
    jsonio.gravar(pasta_video(video_id) / "briefing.json", b)
    return b


@app.get("/api/finalidades")
def lista_finalidades():
    return {"finalidades": finalidades.FINALIDADES}


@app.post("/api/biblioteca/{video_id}/herdar")
def herdar(video_id: str, dados: dict = Body(...)):
    """Nova versão de um vídeo: copia finalidade, briefing, cartões e capa da versão anterior."""
    _video_existe(video_id)
    origem = str(dados.get("de", ""))
    _video_existe(origem)
    pv_o, pv_n = pasta_video(origem), pasta_video(video_id)
    if (pv_o / "briefing.json").exists():
        shutil.copy(pv_o / "briefing.json", pv_n / "briefing.json")
    proj_o, proj_n = pasta_projeto(origem), pasta_projeto(video_id)
    for padrao in ("cartoes.json", "capa.json", "cartao_*", "capa_enviada.*"):
        for arq in proj_o.glob(padrao):
            shutil.copy(arq, proj_n / arq.name)
    m_o, m_n = e0_gravacao.meta(origem), e0_gravacao.meta(video_id)
    base = m_o.get("versao_de") or origem
    versoes = [v for v in e0_gravacao.listar() if (v.get("versao_de") or v["id"]) == base]
    m_n["versao_de"] = base
    m_n["versao"] = max([int(v.get("versao") or 1) for v in versoes] + [1]) + 1
    if dados.get("renomear", True):
        nome_base = re.sub(r"\s+v\d+$", "", m_o.get("nome", "")).strip()
        m_n["nome"] = f"{nome_base} v{m_n['versao']}"
    e0_gravacao.salvar_meta(video_id, m_n)
    return m_n


@app.get("/api/sistema/pasta")
def ver_pasta():
    pendente = ""
    arq = Path("/config/pasta.env")
    if arq.exists():
        for linha in arq.read_text(encoding="utf-8").splitlines():
            if linha.startswith("PASTA_TRABALHO="):
                pendente = linha.split("=", 1)[1].strip().strip('"')
    atual = os.environ.get("VC_PASTA_HOST", "")
    return {"atual": atual, "configurada": pendente or atual, "precisa_reiniciar": bool(pendente and pendente != atual),
            "pode_alterar": Path("/config").is_dir()}


@app.put("/api/sistema/pasta")
def mudar_pasta(dados: dict = Body(...)):
    caminho = str(dados.get("caminho", "")).strip().strip('"')
    if not caminho or not (caminho.startswith("/") or re.match(r"^[A-Za-z]:[\\/]", caminho) or caminho.startswith("~")):
        raise HTTPException(400, "Informe o caminho completo da pasta (ex.: /Users/voce/Videos/VideoComposer ou C:\\Videos)")
    if not Path("/config").is_dir():
        raise HTTPException(409, "Esta instalação não permite trocar a pasta pela tela. Rode o instalador de novo.")
    caminho = caminho.replace("\\", "/")
    Path("/config/pasta.env").write_text(f'PASTA_TRABALHO="{caminho}"\n', encoding="utf-8")
    return ver_pasta()


def _checar_privacidade_e_custo(video_id: str, dados: dict):
    cfg = config.carregar()
    if not cfg["privacidade"]["aviso_aceito"] and not MODO_TESTE:
        raise HTTPException(428, "Aceite o aviso de privacidade antes de enviar quadros do vídeo para a IA")
    est = _estimativa(video_id)
    if est["acima_do_limite"] and not dados.get("confirmado"):
        raise HTTPException(402, f"A estimativa (US$ {est['total_usd']:.2f}) passa do limite por vídeo "
                                 f"(US$ {est['limite_usd']:.2f}). Confirme para continuar.")


def _aprovar_auto(video_id: str, *etapas):
    proj = pasta_projeto(video_id)
    apr = jsonio.ler(proj / "aprovacoes.json", {}) or {}
    for e in etapas:
        apr.setdefault(e, "automático " + time.strftime("%Y-%m-%d %H:%M:%S"))
    jsonio.gravar(proj / "aprovacoes.json", apr)


def _fluxo_roteiro(tarefa, video_id: str, entender: bool, instrucoes: str = ""):
    e5_voz.garantir_calibracao(tarefa, video_id)
    perfil = e1_perfil.executar(tarefa, video_id)
    proj = pasta_projeto(video_id)
    if entender or not (proj / "mapa_de_cenas.json").exists():
        e2_entendimento.executar(tarefa, video_id, perfil)
    rot = e3_roteiro.executar(tarefa, video_id, perfil, instrucoes)
    e4_legendas.executar(video_id, rot)
    return {"falas": len(rot["falas"]), "avisos": len(rot.get("problemas", []))}


def _fluxo_completo(tarefa, video_id: str, instrucoes: str = ""):
    """Do vídeo bruto ao vídeo final, sem intervenção: calibra a voz, corta, entende, escreve, narra
    (resolvendo o encaixe sozinho), monta e confere. O usuário só assiste e aprova o corte final."""
    tarefa.etapa("1/4 Preparando a voz e o vídeo", 0.01)
    _fluxo_roteiro(tarefa, video_id, True, instrucoes)
    _aprovar_auto(video_id, "roteiro")
    tarefa.etapa("2/4 Gerando a narração e resolvendo o sincronismo", 0.5)
    voz = e5_voz.gerar(tarefa, video_id, False, True)
    _aprovar_auto(video_id, "voz")
    tarefa.etapa("3/4 Montando o vídeo", 0.75)
    res = _fluxo_montagem(tarefa, video_id)
    res["voz"] = voz
    return res


@app.post("/api/projetos/{video_id}/completo")
def gerar_completo(video_id: str, dados: dict = Body(default={})):
    _video_existe(video_id)
    _checar_privacidade_e_custo(video_id, dados)
    t = tarefas.iniciar("vídeo completo", video_id, _fluxo_completo, video_id, dados.get("instrucoes", ""))
    return t.dict()


@app.get("/api/projetos/{video_id}/cartoes")
def ler_cartoes(video_id: str):
    _video_existe(video_id)
    return cartoes.carregar(video_id)


@app.put("/api/projetos/{video_id}/cartoes")
def gravar_cartoes(video_id: str, dados: dict = Body(...)):
    _video_existe(video_id)
    return cartoes.salvar(video_id, dados)


@app.get("/api/projetos/{video_id}/cartoes/{qual}.png")
def previa_cartao(video_id: str, qual: str):
    if qual not in ("abertura", "encerramento"):
        raise HTTPException(404)
    cfg = config.carregar()
    m = config.marca(cfg)
    cart = cartoes.carregar(video_id, cfg)
    c = cart[qual]
    proj = pasta_projeto(video_id)
    destino = proj / f"previa_{qual}.png"
    rodape = e7_edicao.rodape_encerramento(cfg, cart, proj) if qual == "encerramento" else ""
    e7_edicao.cartao(m, cartoes.caminho_imagem(video_id, qual, cart, m), c["titulo"], c["subtitulo"], destino, rodape,
                     texto_sobre_imagem=c.get("texto_sobre_imagem", True))
    return FileResponse(destino, media_type="image/png", headers={"Cache-Control": "no-store"})


@app.post("/api/projetos/{video_id}/cartoes/{qual}/imagem")
async def enviar_imagem_cartao(video_id: str, qual: str, request: Request, nome: str):
    _video_existe(video_id)
    corpo = await request.body()
    if len(corpo) > 20 * 1_048_576:
        raise HTTPException(413, "Imagem grande demais")
    return cartoes.guardar_imagem(video_id, qual, nome_seguro(nome), corpo)


@app.get("/api/projetos/{video_id}/capa")
def ler_capa(video_id: str):
    _video_existe(video_id)
    return {"capa": capa.carregar(video_id), "instante_automatico": capa.melhor_instante(video_id)}


@app.put("/api/projetos/{video_id}/capa")
def gravar_capa(video_id: str, dados: dict = Body(...)):
    _video_existe(video_id)
    return {"capa": capa.salvar(video_id, dados)}


@app.post("/api/projetos/{video_id}/capa/imagem")
async def enviar_capa(video_id: str, request: Request, nome: str):
    _video_existe(video_id)
    corpo = await request.body()
    if len(corpo) > 20 * 1_048_576:
        raise HTTPException(413, "Imagem grande demais")
    return {"capa": capa.guardar_imagem(video_id, nome_seguro(nome), corpo)}


@app.get("/api/projetos/{video_id}/capa.jpg")
def ver_capa(video_id: str):
    _video_existe(video_id)
    destino = pasta_projeto(video_id) / "capa_previa.jpg"
    capa.gerar(video_id, destino)
    return FileResponse(destino, media_type="image/jpeg", headers={"Cache-Control": "no-store"})


@app.get("/api/projetos/{video_id}/linha-do-tempo")
def linha_tempo(video_id: str):
    """Dados para o editor em trilhas: tudo no tempo do vídeo final."""
    _video_existe(video_id)
    cfg = config.carregar()
    proj = pasta_projeto(video_id)
    perfil = jsonio.ler(proj / "perfil_video.json")
    if not perfil:
        return {"pronto": False}
    roteiro = jsonio.ler(proj / "roteiro.json") or {"falas": [], "abertura": {}, "voz": {"ritmo_car_s": 12}}
    encaixe = jsonio.ler(proj / "audio" / "encaixe.json", {}) or {}
    cart = cartoes.carregar(video_id, cfg)
    lt = linha_do_tempo.calcular(cart, perfil, encaixe)
    D = lt["deslocamento_video_s"]
    por_id = {str(r["id"]): r for r in encaixe.get("falas", [])}
    falas = []
    for f in roteiro.get("falas", []):
        r = por_id.get(str(f["id"]))
        dur = r["duracao_s"] if r else len(f["texto_falado"]) / (roteiro["voz"].get("ritmo_car_s") or 12)
        falas.append({"id": f["id"], "janela": f["janela"], "ini": round(f["inicio_s"] + D, 3), "dur": round(dur, 3),
                      "janela_ini": round(f["inicio_s"] + D, 3), "janela_fim": round(f["fim_s"] + D, 3),
                      "texto_legenda": f["texto_legenda"], "texto_falado": f["texto_falado"],
                      "orcamento": f["orcamento_caracteres"], "situacao": r["situacao"] if r else "sem voz",
                      "velocidade": r["velocidade"] if r else None, "emprestou_s": r.get("emprestou_s", 0) if r else 0,
                      "ajustada": bool(f.get("ajustada_automaticamente"))})
    textos_cart = cartoes.textos_fala(video_id, cart, roteiro, cfg)
    for k in ("abertura", "encerramento"):
        r = por_id.get(k)
        ini = linha_do_tempo.inicio_final(r, lt) if r else None
        if r and ini is not None:
            bloco = {"id": k, "janela": k, "ini": ini, "dur": r["duracao_s"], "texto_legenda": textos_cart[k][0],
                     "texto_falado": textos_cart[k][1], "orcamento": 0, "situacao": r["situacao"],
                     "velocidade": r["velocidade"], "emprestou_s": 0, "ajustada": False}
            if k == "abertura":
                falas.insert(0, bloco)
            else:
                falas.append(bloco)
    duracoes = {r["id"]: r["duracao_s"] for r in encaixe.get("falas", [])}
    deixas = e4_legendas.deixas(roteiro, duracoes, deslocamento=D) if roteiro.get("falas") else []
    mapa = jsonio.ler(proj / "mapa_de_cenas.json", {}) or {}
    cenas = [{"id": c["id"], "ini": round(c["inicio_s"] + D, 3), "fim": round(c["fim_s"] + D, 3), "tela": c["tela"],
              "tipo": c["tipo"], "t_base": round((c["inicio_s"] + c["fim_s"]) / 2, 2)} for c in mapa.get("cenas", [])]
    meta_mus = e7_edicao.credito_musica(cfg)
    musica = None
    if (proj / "trilha_final.wav").exists() and cfg["musica"].get("arquivo"):
        musica = {"nome": meta_mus.get("titulo") or cfg["musica"]["arquivo"], "autor": meta_mus.get("autor", ""),
                  "ini": 0, "fim": lt["total_s"]}
    return {"pronto": True, "lt": lt, "falas": falas, "deixas": deixas, "cenas": cenas, "musica": musica,
            "cartoes": cart, "tem_video_final": (proj / "video_final.mp4").exists()}


def _fluxo_refazer(tarefa, video_id: str):
    tarefa.etapa("Refazendo as falas alteradas", 0.05)
    voz = e5_voz.gerar(tarefa, video_id, False, True)
    _aprovar_auto(video_id, "voz")
    res = _fluxo_montagem(tarefa, video_id)
    res["voz"] = voz
    return res


@app.post("/api/projetos/{video_id}/refazer")
def refazer(video_id: str):
    _video_existe(video_id)
    t = tarefas.iniciar("ajuste", video_id, _fluxo_refazer, video_id)
    return t.dict()


@app.post("/api/projetos/{video_id}/roteiro/gerar")
def gerar_roteiro(video_id: str, dados: dict = Body(default={})):
    _video_existe(video_id)
    _checar_privacidade_e_custo(video_id, dados)
    entender = bool(dados.get("reanalisar_video", True))
    t = tarefas.iniciar("roteiro", video_id, _fluxo_roteiro, video_id, entender, dados.get("instrucoes", ""))
    return t.dict()


@app.put("/api/projetos/{video_id}/roteiro")
def editar_roteiro(video_id: str, dados: dict = Body(...)):
    _video_existe(video_id)
    rot = e3_roteiro.salvar_edicao(video_id, dados)
    e4_legendas.executar(video_id, rot)
    return rot


@app.post("/api/projetos/{video_id}/voz/previa")
def previa_voz(video_id: str):
    _video_existe(video_id)
    t = tarefas.iniciar("prévia de voz", video_id, e5_voz.gerar, video_id, True)
    return t.dict()


@app.post("/api/projetos/{video_id}/voz/gerar")
def gerar_voz(video_id: str):
    _video_existe(video_id)
    if not (pasta_projeto(video_id) / "roteiro.json").exists():
        raise HTTPException(409, "Gere o roteiro antes da voz")
    _aprovar_auto(video_id, "roteiro")
    t = tarefas.iniciar("voz", video_id, e5_voz.gerar, video_id, False)
    return t.dict()


def _fluxo_montagem(tarefa, video_id: str):
    tarefa.etapa("Etapa 6: trilha", 0.02)
    trilha = e6_trilha.executar(tarefa, video_id)
    tarefa.etapa("Etapa 7: edição final", 0.2)
    montagem = e7_edicao.executar(tarefa, video_id)
    tarefa.etapa("Etapa 8: controle de qualidade", 0.9)
    qa = e8_qa.executar(tarefa, video_id)
    return {"trilha": trilha, "montagem": montagem, "qa": {"falhas": qa["falhas"], "avisos": qa["avisos"]}}


@app.post("/api/projetos/{video_id}/montar")
def montar(video_id: str):
    _video_existe(video_id)
    proj = pasta_projeto(video_id)
    if not (proj / "narracao.wav").exists():
        raise HTTPException(409, "Gere a voz antes de montar o vídeo")
    t = tarefas.iniciar("montagem", video_id, _fluxo_montagem, video_id)
    return t.dict()


@app.post("/api/projetos/{video_id}/aprovar")
def aprovar(video_id: str, dados: dict = Body(...)):
    _video_existe(video_id)
    etapa = dados.get("etapa")
    if etapa not in ("roteiro", "voz", "final"):
        raise HTTPException(400, "Etapa inválida")
    proj = pasta_projeto(video_id)
    if etapa == "roteiro":
        rot = jsonio.ler(proj / "roteiro.json") or {}
        estouros = [p for p in rot.get("problemas", []) if p["tipo"] == "estouro"]
        if estouros and not dados.get("forcar"):
            raise HTTPException(409, f"{len(estouros)} fala(s) passam do orçamento. Ajuste ou aprove mesmo assim.")
    apr = jsonio.ler(proj / "aprovacoes.json", {}) or {}
    apr[etapa] = time.strftime("%Y-%m-%d %H:%M:%S")
    jsonio.gravar(proj / "aprovacoes.json", apr)
    return apr


@app.post("/api/projetos/{video_id}/exportar")
def exportar(video_id: str, dados: dict = Body(default={})):
    _video_existe(video_id)
    t = tarefas.iniciar("exportação", video_id, e7_edicao.exportar, video_id, dados)
    return t.dict()


@app.get("/api/projetos/{video_id}/arquivo/{caminho:path}")
def arquivo_projeto(video_id: str, caminho: str):
    p = dentro(pasta_projeto(video_id), caminho)
    if not p.exists():
        raise HTTPException(404)
    if p.suffix in (".md", ".tsv", ".srt", ".txt"):
        return PlainTextResponse(p.read_text(encoding="utf-8"))
    return FileResponse(p, headers={"Cache-Control": "no-cache"})


@app.get("/api/exportados/{caminho:path}")
def baixar_exportado(caminho: str):
    p = dentro(EXPORTADOS, caminho)
    if not p.exists():
        raise HTTPException(404)
    return FileResponse(p, filename=p.name)


# ---------------- tarefas ----------------

@app.get("/api/tarefas/{tid}")
def tarefa(tid: str):
    t = tarefas.obter(tid)
    if not t:
        raise HTTPException(404, "Tarefa não encontrada")
    return t.dict()


@app.get("/api/tarefas")
def lista_tarefas():
    return {"tarefas": tarefas.recentes()}


app.mount("/", StaticFiles(directory=APP / "web", html=True), name="web")
