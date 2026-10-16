"""Etapa 8: controle de qualidade. Determinístico + checagem visual opcional por IA."""
import time

from ..core import claude, config, jsonio, midia, segredos
from ..core.caminhos import MODO_TESTE, pasta_projeto, pasta_video
from . import cartoes, e3_roteiro, linha_do_tempo

OK, AVISO, ERRO = "✅ OK", "⚠️ ATENÇÃO", "❌ FALHA"


def executar(tarefa, video_id: str) -> dict:
    cfg = config.carregar()
    proj = pasta_projeto(video_id)
    final = proj / "video_final.mp4"
    perfil = jsonio.ler(proj / "perfil_video.json")
    roteiro = jsonio.ler(proj / "roteiro.json") or {"falas": []}
    mapa = jsonio.ler(proj / "mapa_de_cenas.json", {"cenas": []})
    encaixe = jsonio.ler(proj / "audio" / "encaixe.json", {}) or {}
    briefing = jsonio.ler(pasta_video(video_id) / "briefing.json", {}) or {}
    lt = linha_do_tempo.calcular(cartoes.carregar(video_id, cfg), perfil, encaixe)
    itens = []

    def item(nome, situacao, detalhe):
        itens.append({"verificacao": nome, "situacao": situacao, "detalhe": detalhe})

    tarefa.etapa("QA: conferindo encaixe das falas", 0.92)
    falas = [r for r in encaixe.get("falas", []) if r["id"] not in ("abertura", "encerramento")]
    estouros = [r for r in encaixe.get("falas", []) if r["situacao"] == "ESTOURA"]
    item("Falas que estouram a cena (meta: 0)", OK if not estouros else ERRO,
         "nenhuma" if not estouros else "falas " + ", ".join(str(r["id"]) for r in estouros))
    if falas:
        nat = sum(1 for r in falas if r["velocidade"] <= 1.001)
        pct = nat / len(falas) * 100
        item("Falas no ritmo natural da voz (meta: ≥ 80%)", OK if pct >= 80 else AVISO,
             f"{nat} de {len(falas)} ({pct:.0f}%)")

    info = midia.sondar(final)
    dif = abs(info["duracao_s"] - lt["total_s"])
    item("Duração do vídeo final", OK if dif < 0.25 else ERRO,
         f"{info['duracao_s']:.2f} s (esperado {lt['total_s']:.2f} s, diferença {dif:.2f} s)")
    item("Resolução e quadros", OK if info.get("resolucao") == "1920x1080" and abs(info.get("fps", 0) - 30) < 0.5 else AVISO,
         f"{info.get('resolucao')} a {info.get('fps')} quadros/s")

    tarefa.etapa("QA: picos de áudio e trechos pretos", 0.94)
    pico = midia.pico_db(final)
    item("Picos de áudio (meta: abaixo de −1 dB)", OK if pico <= -1.0 else AVISO, f"pico de {pico:.1f} dB")
    pretos = [p for p in midia.trechos_pretos(final) if p[0] > 0.5 and p[1] < lt["total_s"] - 1.5]
    item("Trechos pretos no meio do vídeo", OK if not pretos else AVISO,
         "nenhum" if not pretos else "; ".join(f"{a:.1f} a {b:.1f} s" for a, b in pretos))

    nums = e3_roteiro._numeros_do_mapa(mapa, briefing)
    divergentes = []
    for f in roteiro["falas"]:
        for rot, v in (f.get("numeros_citados") or {}).items():
            try:
                if float(str(v).replace(",", ".")) not in nums:
                    divergentes.append(f"fala {f['id']}: {rot} = {v}")
            except ValueError:
                pass
    item("Números citados que batem com a tela (meta: 100%)", OK if not divergentes else ERRO,
         "todos conferem com o mapa de cenas" if not divergentes else "; ".join(divergentes))
    vetados = [p for p in e3_roteiro.validar(roteiro, mapa, briefing, perfil) if p["tipo"] == "nao_mencionar"]
    if briefing.get("nao_mencionar"):
        item("Lista \"não mencionar\"", OK if not vetados else ERRO,
             "nada mencionado" if not vetados else "; ".join(p["detalhe"] for p in vetados))
    lic = proj / "licenca_musica.txt"
    if (proj / "trilha_final.wav").exists():
        from ..core import catalogo_musica
        meta_m = catalogo_musica.metadados(cfg["musica"].get("arquivo", ""))
        tem = lic.exists() and "NÃO encontrado" not in lic.read_text(encoding="utf-8")
        if meta_m.get("origem") == "eleven_music":
            individual = any(str(meta_m.get("plano", "")).startswith(p) for p in ("free", "starter", "creator", "pro"))
            item("Licença da música", AVISO if individual else OK,
                 meta_m.get("aviso_plano") if individual else "gerada pelo Eleven Music; comprovante guardado no projeto")
        elif meta_m.get("verificada"):
            item("Licença da música", OK if tem else AVISO, "licença confirmada" + ("" if tem else "; falta o comprovante .txt"))
        else:
            origem = "catálogo aberto" if meta_m.get("origem") == "catalogo_aberto" else "faixa enviada"
            item("Licença da música", AVISO, f"{origem} com licença não confirmada: confira a fonte e clique em Confirmar licença")

    from . import e7_edicao
    meta_mus = e7_edicao.credito_musica(cfg)
    if meta_mus.get("exige_atribuicao") and (proj / "trilha_final.wav").exists():
        c = cartoes.carregar(video_id, cfg)["encerramento"]
        no_video = c["ativo"] and c.get("credito_musica", True)
        item("Crédito da música (licença CC BY)", OK if no_video else AVISO,
             "no encerramento e em creditos.txt" if no_video
             else "o encerramento está desligado: publique o crédito na descrição (creditos.txt na exportação)")

    tarefa.etapa("QA: quadros-chave", 0.96)
    pasta = proj / "qa"
    pasta.mkdir(exist_ok=True)
    chaves = [("abertura", lt["abertura_s"] / 2), ("transicao", lt["abertura_s"] - lt["transicao_s"] / 2)] \
        if lt["abertura_s"] > 0 else [("inicio", 0.5)]
    if roteiro["falas"]:
        f0 = roteiro["falas"][min(1, len(roteiro["falas"]) - 1)]
        chaves.append(("legenda", lt["deslocamento_video_s"] + f0["inicio_s"] + 1.0))
    chaves.append(("fim", max(lt["total_s"] - 1.6, 0)))
    quadros = []
    for nome, t in chaves:
        midia.quadro(final, t, pasta / f"{nome}.jpg", 960, 3)
        quadros.append({"nome": nome, "t_s": round(t, 2), "arquivo": f"qa/{nome}.jpg"})

    visao = ""
    if segredos.obter("claude") and not MODO_TESTE:
        try:
            modelo = cfg["claude"]["modelos"]["qa"]
            conteudo = []
            for q in quadros:
                conteudo.append(claude.texto(f"Quadro '{q['nome']}' em t={q['t_s']} s:"))
                conteudo.append(claude.imagem(proj / q["arquivo"]))
            conteudo.append(claude.texto(
                "Para cada quadro, diga em uma linha se está correto: abertura com a marca visível; transição sem "
                "quadro preto ou corrompido; legenda legível, dentro da tela, no máximo 2 linhas; fim limpo. "
                "Responda em JSON: {\"quadros\": [{\"nome\": \"...\", \"ok\": true, \"observacao\": \"...\"}]}"))
            r = claude.extrair_json(claude.chamar(modelo, "Você revisa vídeos de demonstração antes da publicação.",
                                                  conteudo, 1500, proj / "custos.json", "qa"))
            for q in r.get("quadros", []):
                item(f"Visual: {q.get('nome')}", OK if q.get("ok") else AVISO, q.get("observacao", ""))
        except Exception as e:  # noqa: BLE001
            visao = f"Checagem visual por IA não executada: {e}"

    custos = jsonio.ler(proj / "custos.json", []) or []
    total_usd = sum(c.get("usd", 0) for c in custos)
    falhas = sum(1 for i in itens if i["situacao"] == ERRO)
    avisos = sum(1 for i in itens if i["situacao"] == AVISO)
    linhas = ["# Relatório de QA", "", f"Gerado em {time.strftime('%d/%m/%Y %H:%M')}.", "",
              f"**Resultado:** {falhas} falha(s), {avisos} atenção(ões), {len(itens) - falhas - avisos} OK.", "",
              "| Verificação | Situação | Detalhe |", "|---|---|---|"]
    for i in itens:
        linhas.append(f"| {i['verificacao']} | {i['situacao']} | {i['detalhe']} |")
    if visao:
        linhas += ["", visao]
    linhas += ["", f"**Custo de API registrado neste projeto:** US$ {total_usd:.2f}", "",
               "Quadros-chave: " + ", ".join(f"{q['nome']} ({q['t_s']} s)" for q in quadros)]
    (proj / "relatorio_qa.md").write_text("\n".join(linhas) + "\n", encoding="utf-8")
    res = {"itens": itens, "falhas": falhas, "avisos": avisos, "quadros": quadros, "custo_usd": round(total_usd, 3)}
    jsonio.gravar(proj / "qa.json", res)
    return res
