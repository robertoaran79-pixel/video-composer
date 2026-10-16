"""Etapa 7: edição final. Abertura, transição, legendas, mixagem, encerramento e exportação."""
import shutil
import tempfile
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from ..core import catalogo_musica, config, jsonio, midia
from ..core.caminhos import EXPORTADOS, MARCAS, nome_seguro, pasta_projeto
from . import capa, cartoes, e0_gravacao, e4_legendas, linha_do_tempo

W, H = 1920, 1080


def _cor(hexa: str, padrao=(15, 23, 42)):
    try:
        h = hexa.lstrip("#")
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    except Exception:  # noqa: BLE001
        return padrao


def _fonte(nome: str, tam: int):
    candidatos = []
    if "mono" in nome.lower():
        candidatos.append("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf")
    candidatos += ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "DejaVuSans-Bold.ttf"]
    for c in candidatos:
        try:
            return ImageFont.truetype(c, tam)
        except OSError:
            continue
    return ImageFont.load_default()


def cartao(m: dict, imagem, titulo: str, subtitulo: str, saida: Path, rodape: str = "",
           texto_sobre_imagem: bool = True) -> Path:
    """Imagem 1920x1080. Com imagem (do vídeo ou da marca): preenche a tela e, se pedido, escreve título e
    subtítulo numa faixa escura embaixo. Sem imagem: cor de fundo + logotipo + texto centralizado."""
    fundo = Image.new("RGB", (W, H), _cor(m["cor_fundo_cartao"]))
    arq = (imagem if isinstance(imagem, Path) else MARCAS / imagem) if imagem else None
    if arq and arq.exists():
        img = Image.open(arq).convert("RGB")
        esc = max(W / img.width, H / img.height)
        img = img.resize((max(W, int(img.width * esc)), max(H, int(img.height * esc))))
        x, y0 = (img.width - W) // 2, (img.height - H) // 2
        fundo.paste(img.crop((x, y0, x + W, y0 + H)), (0, 0))
        if texto_sobre_imagem and (titulo or subtitulo):
            sombra = Image.new("L", (W, H), 0)
            ds = ImageDraw.Draw(sombra)
            for i in range(560):
                ds.line([(0, H - i), (W, H - i)], fill=int(215 * (1 - i / 560) ** 1.2))
            fundo = Image.composite(Image.new("RGB", (W, H), (0, 0, 0)), fundo, sombra)
            d = ImageDraw.Draw(fundo)
            y = H - 230  # deixa espaço embaixo para a legenda da fala do cartão
            for texto, tam, larg in ((subtitulo, 42, 64), (titulo, 84, 32)):
                if not texto:
                    continue
                f = _fonte(m.get("fonte", ""), tam)
                for ln in reversed(e4_legendas.quebrar_linhas(texto, larg)[:2]):
                    d.text((96, y - tam), ln, fill=(255, 255, 255), font=f)
                    y -= int(tam * 1.2)
                y -= 10
        _rodape(fundo, m, rodape)
        fundo.save(saida)
        return saida
    d = ImageDraw.Draw(fundo)
    y = H // 2 - 60
    logo = MARCAS / m["logotipo"] if m.get("logotipo") else None
    if logo and logo.exists():
        lg = Image.open(logo).convert("RGBA")
        lg.thumbnail((520, 260))
        fundo.paste(lg, ((W - lg.width) // 2, H // 2 - lg.height - 30), lg)
        y = H // 2 + 10
    cor = _cor(m["cor_texto_cartao"], (255, 255, 255))
    for texto, tam in ((titulo, 76), (subtitulo, 40)):
        if not texto:
            continue
        f = _fonte(m.get("fonte", ""), tam)
        linhas = e4_legendas.quebrar_linhas(texto, 38 if tam > 50 else 70)[:2]
        for ln in linhas:
            bw = d.textlength(ln, font=f)
            d.text(((W - bw) / 2, y), ln, fill=cor, font=f)
            y += int(tam * 1.25)
        y += 16
    _rodape(fundo, m, rodape)
    fundo.save(saida)
    return saida


def _rodape(img, m: dict, texto: str):
    """Crédito da música (licença CC BY) na parte de baixo do cartão de encerramento."""
    if not texto:
        return
    d = ImageDraw.Draw(img)
    f = _fonte("", 26)
    for i, ln in enumerate(e4_legendas.quebrar_linhas(texto, 110)[:2]):
        bw = d.textlength(ln, font=f)
        x, y = (W - bw) / 2, H - 90 + i * 34
        d.rectangle([x - 12, y - 4, x + bw + 12, y + 30], fill=(0, 0, 0))
        d.text((x, y), ln, fill=(235, 235, 235), font=f)


def rodape_encerramento(cfg: dict, cart: dict, proj: Path) -> str:
    meta = credito_musica(cfg)
    if cart["encerramento"].get("credito_musica", True) and meta.get("exige_atribuicao") and \
            (proj / "trilha_final.wav").exists():
        return meta.get("credito", "")
    return ""


def credito_musica(cfg: dict) -> dict:
    arq = cfg["musica"].get("arquivo")
    return catalogo_musica.metadados(arq) if arq else {}


def _ass_cor(hexa: str, opacidade: float = 1.0) -> str:
    r, g, b = _cor(hexa, (255, 255, 255))
    a = int(round((1 - max(0.0, min(1.0, opacidade))) * 255))
    return f"&H{a:02X}{b:02X}{g:02X}{r:02X}"


def _ass_tc(s: float) -> str:
    s = max(0.0, s)
    h = int(s // 3600)
    m = int(s % 3600 // 60)
    sec = s % 60
    return f"{h}:{m:02d}:{sec:05.2f}"


def gerar_ass(deixas: list, m: dict, saida: Path, largura: int = W, altura: int = H):
    estilo = (f"Style: Padrao,{m.get('fonte') or 'DejaVu Sans'},{int(m['tamanho_fonte'])},"
              f"{_ass_cor(m['cor_legenda'])},{_ass_cor(m['cor_legenda'])},"
              f"{_ass_cor(m['cor_fundo_legenda'], float(m['opacidade_fundo_legenda']))},"
              f"{_ass_cor(m['cor_fundo_legenda'], float(m['opacidade_fundo_legenda']))},"
              "0,0,0,0,100,100,0,0,3,14,0,2,80,80,64,1")
    linhas = ["[Script Info]", "ScriptType: v4.00+", f"PlayResX: {largura}", f"PlayResY: {altura}",
              "WrapStyle: 2", "ScaledBorderAndShadow: yes", "", "[V4+ Styles]",
              "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
              "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
              "Alignment, MarginL, MarginR, MarginV, Encoding", estilo, "", "[Events]",
              "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
    for d in deixas:
        txt = "\\N".join(l.replace("\\", "/").replace("{", "(").replace("}", ")") for l in d["linhas"])
        linhas.append(f"Dialogue: 0,{_ass_tc(d['ini'])},{_ass_tc(d['fim'])},Padrao,,0,0,0,,{txt}")
    saida.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    return saida


def _esc_filtro(caminho: Path) -> str:
    return str(caminho).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def compor(tarefa, video_id: str, saida: Path, com_narracao: bool = True, legenda: str | None = None) -> dict:
    cfg = config.carregar()
    m = config.marca(cfg)
    proj = pasta_projeto(video_id)
    perfil = jsonio.ler(proj / "perfil_video.json")
    roteiro = jsonio.ler(proj / "roteiro.json")
    encaixe = jsonio.ler(proj / "audio" / "encaixe.json", {}) or {}
    if com_narracao and not (proj / "narracao.wav").exists():
        raise RuntimeError("Gere a voz antes de montar o vídeo")
    legenda = legenda or cfg["exportacao"]["legenda"]
    cart = cartoes.carregar(video_id, cfg)
    lt = linha_do_tempo.calcular(cart, perfil, encaixe)
    A, T, E, T2, V, D, total = (lt["abertura_s"], lt["transicao_s"], lt["encerramento_s"], lt["transicao_fim_s"],
                                lt["video_s"], lt["deslocamento_video_s"], lt["total_s"])
    duracoes = {r["id"]: r["duracao_s"] for r in encaixe.get("falas", [])}
    deixas = e4_legendas.deixas(roteiro, duracoes, deslocamento=D) if roteiro and roteiro.get("falas") else []
    # falas dos cartões viram legenda também (acessibilidade), no tempo em que são ditas
    textos_cart = cartoes.textos_fala(video_id, cart, roteiro, cfg)
    for k, ini in (("abertura", lt["abertura_fala_s"] if A > 0 else None), ("encerramento", lt["encerramento_fala_s"])):
        leg = textos_cart[k][0]
        if ini is None or not leg or not duracoes.get(k):
            continue
        blocos = e4_legendas.blocos_de_legenda(leg)
        tot = sum(len(" ".join(b)) for b in blocos) or 1
        t, dur = ini, duracoes[k] + 0.3
        for b in blocos:
            d = dur * len(" ".join(b)) / tot
            deixas.append({"ini": round(t, 3), "fim": round(t + d, 3), "linhas": b, "fala": k})
            t += d
    deixas.sort(key=lambda x: x["ini"])
    (proj / "legendas_final.srt").write_text(e4_legendas.srt(deixas), encoding="utf-8")

    with tempfile.TemporaryDirectory(dir=proj) as tmp:
        tmp = Path(tmp)
        entradas, f, n = [], [], 0
        norm = "scale=1920:1080,setsar=1,fps=30,format=yuv420p,settb=AVTB"
        if A > 0:
            cartao(m, cartoes.caminho_imagem(video_id, "abertura", cart, m), cart["abertura"]["titulo"],
                   cart["abertura"]["subtitulo"], tmp / "abertura.png",
                   texto_sobre_imagem=cart["abertura"].get("texto_sobre_imagem", True))
            entradas += ["-loop", "1", "-framerate", "30", "-t", f"{A:.3f}", "-i", tmp / "abertura.png"]
            f.append(f"[{n}:v]{norm}[ab]")
            n += 1
        entradas += ["-i", proj / "base.mp4"]
        f.append(f"[{n}:v]tpad=stop_mode=clone:stop_duration=1,trim=0:{V:.3f},setpts=PTS-STARTPTS,{norm}[vg]")
        n += 1
        ult = "[vg]"
        if A > 0:
            f.append(f"[ab][vg]xfade=transition=fade:duration={max(T, 0.04):.3f}:offset={A - max(T, 0.04):.3f}[v1]")
            ult = "[v1]"
        if E > 0:
            rodape = rodape_encerramento(cfg, cart, proj)
            cartao(m, cartoes.caminho_imagem(video_id, "encerramento", cart, m), cart["encerramento"]["titulo"],
                   cart["encerramento"]["subtitulo"], tmp / "encerramento.png", rodape,
                   texto_sobre_imagem=cart["encerramento"].get("texto_sobre_imagem", True))
            entradas += ["-loop", "1", "-framerate", "30", "-t", f"{E:.3f}", "-i", tmp / "encerramento.png"]
            f.append(f"[{n}:v]{norm}[en]")
            n += 1
            f.append(f"{ult}[en]xfade=transition=fade:duration={max(T2, 0.04):.3f}:offset={D + V - max(T2, 0.04):.3f}[v2]")
            ult = "[v2]"
        if legenda == "gravada" and deixas:
            ass = gerar_ass(deixas, m, tmp / "legendas.ass")
            f.append(f"{ult}subtitles='{_esc_filtro(ass)}':fontsdir=/usr/share/fonts[v3]")
            ult = "[v3]"
        f.append(f"{ult}fade=t=out:st={max(total - 1.2, 0):.3f}:d=1.2,trim=0:{total:.3f}[vout]")
        idx = n

        # áudio
        audios = []
        if com_narracao:
            faixas = [(proj / "narracao.wav", D)]
            if A > 0 and duracoes.get("abertura") and (proj / "abertura.wav").exists():
                faixas.append((proj / "abertura.wav", lt["abertura_fala_s"]))
            if E > 0 and duracoes.get("encerramento") and (proj / "encerramento.wav").exists():
                faixas.append((proj / "encerramento.wav", lt["encerramento_fala_s"]))
            rotulos = []
            for i_f, (arq, ini) in enumerate(faixas):
                entradas += ["-i", arq]
                ms = int(ini * 1000)
                f.append(f"[{idx}:a]aformat=sample_rates=44100:channel_layouts=stereo,adelay={ms}|{ms}[n{i_f}]")
                rotulos.append(f"[n{i_f}]")
                idx += 1
            pre = f"{''.join(rotulos)}amix=inputs={len(rotulos)}:normalize=0:duration=longest," if len(rotulos) > 1 \
                else f"{rotulos[0]}"
            f.append(f"{pre}loudnorm=I=-16:TP=-1.5:LRA=11,aresample=44100,aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[narr]")
            audios = ["[narr]"]
        if (proj / "trilha_final.wav").exists():
            entradas += ["-i", proj / "trilha_final.wav"]
            f.append(f"[{idx}:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[mu]")
            audios.append("[mu]")
            idx += 1
        if not audios:
            f.append(f"anullsrc=r=44100:cl=stereo,atrim=0:{total:.3f}[aout]")
        else:
            mix = f"{audios[0]}anull" if len(audios) == 1 else f"{''.join(audios)}amix=inputs={len(audios)}:normalize=0:duration=longest"
            f.append(f"{mix},apad,atrim=0:{total:.3f},alimiter=limit=0.89:level=false,"
                     f"afade=t=out:st={max(total - 1.5, 0):.3f}:d=1.5[aout]")
        script = tmp / "grafo.txt"
        script.write_text(";\n".join(f), encoding="utf-8")
        cmd = ["ffmpeg", "-y", *entradas]
        mapas = ["-map", "[vout]", "-map", "[aout]"]
        if legenda == "selecionavel" and deixas:
            cmd += ["-i", proj / "legendas_final.srt"]
            mapas += ["-map", f"{idx}:s", "-c:s", "mov_text", "-metadata:s:s:0", "language=por"]
        cmd += ["-filter_complex", script.read_text(encoding="utf-8"), *mapas, "-c:v", "libx264", "-preset", "medium", "-crf", "21",
                "-pix_fmt", "yuv420p", "-r", "30", "-c:a", "aac", "-b:a", "160k", "-t", f"{total:.3f}",
                "-movflags", "+faststart", tmp / "saida.mp4"]
        tarefa.etapa(f"Renderizando {total:.0f} s de vídeo (abertura, transição, legendas e mixagem)", None)
        midia.rodar(cmd, timeout=7200)
        shutil.move(str(tmp / "saida.mp4"), saida)
    return {"duracao_esperada_s": total, "linha_do_tempo": lt}


def executar(tarefa, video_id: str) -> dict:
    proj = pasta_projeto(video_id)
    res = compor(tarefa, video_id, proj / "video_final.mp4")
    tarefa.etapa("Gerando a capa e embutindo no vídeo", None)
    capa.embutir(proj / "video_final.mp4", capa.gerar(video_id))
    info = midia.sondar(proj / "video_final.mp4")
    res["duracao_real_s"] = info["duracao_s"]
    res["tamanho_mb"] = info["tamanho_mb"]
    apr = jsonio.ler(proj / "aprovacoes.json", {}) or {}
    apr.pop("final", None)
    jsonio.gravar(proj / "aprovacoes.json", apr)
    jsonio.gravar(proj / "montagem.json", res)
    return res


def exportar(tarefa, video_id: str, opcoes: dict) -> dict:
    proj = pasta_projeto(video_id)
    final = proj / "video_final.mp4"
    if not final.exists():
        raise RuntimeError("Monte o vídeo final antes de exportar")
    m = e0_gravacao.meta(video_id)
    pasta = EXPORTADOS / nome_seguro(m["nome"])
    pasta.mkdir(parents=True, exist_ok=True)
    carimbo = time.strftime("%Y-%m-%d %Hh%M")
    base = nome_seguro(m["nome"])
    gerados = []
    if opcoes.get("horizontal", True):
        tarefa.etapa("Exportando 16:9", 0.1)
        dst = pasta / f"{base} - 16x9 - {carimbo}.mp4"
        shutil.copy(final, dst)
        capa.embutir(dst, capa.gerar(video_id))  # capa sempre atualizada
        gerados.append(dst)
    if opcoes.get("vertical"):
        tarefa.etapa("Exportando vertical 9:16", 0.3)
        dst = pasta / f"{base} - 9x16 - {carimbo}.mp4"
        midia.rodar(["ffmpeg", "-y", "-i", final, "-filter_complex",
                     "[0:v:0]split[a][b];[a]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
                     "boxblur=24:2[bg];[b]scale=1080:-2[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2,format=yuv420p[v]",
                     "-map", "[v]", "-map", "0:a", "-c:v", "libx264", "-preset", "medium", "-crf", "22",
                     "-c:a", "copy", "-movflags", "+faststart", dst], timeout=7200)
        gerados.append(dst)
    if opcoes.get("sem_narracao"):
        tarefa.etapa("Exportando versão sem narração e sem legenda", 0.6)
        dst = pasta / f"{base} - sem narracao - {carimbo}.mp4"
        compor(tarefa, video_id, dst, com_narracao=False, legenda="nenhuma")
        gerados.append(dst)
    if opcoes.get("srt_separado", True) and (proj / "legendas_final.srt").exists():
        dst = pasta / f"{base} - legendas - {carimbo}.srt"
        shutil.copy(proj / "legendas_final.srt", dst)
        gerados.append(dst)
    tarefa.etapa("Exportando a capa", 0.9)
    dst = pasta / f"{base} - capa - {carimbo}.jpg"
    shutil.copy(capa.gerar(video_id), dst)
    gerados.append(dst)
    meta_mus = credito_musica(config.carregar())
    if meta_mus.get("credito") and (proj / "trilha_final.wav").exists():
        dst = pasta / f"{base} - creditos.txt"
        dst.write_text(meta_mus["credito"] + "\n" + meta_mus.get("atribuicao", "") + "\n" +
                       f"Licença: {meta_mus.get('licenca_url', '')}\nObra: {meta_mus.get('pagina', '')}\n", encoding="utf-8")
        gerados.append(dst)
    if (proj / "licenca_musica.txt").exists():
        dst = pasta / f"{base} - licenca da musica.txt"
        shutil.copy(proj / "licenca_musica.txt", dst)
        gerados.append(dst)
    return {"pasta": str(pasta.relative_to(EXPORTADOS.parent)),
            "arquivos": [{"nome": g.name, "caminho": str(g.relative_to(EXPORTADOS)),
                          "tamanho_mb": round(g.stat().st_size / 1_048_576, 1)} for g in gerados]}
