"""Capa do vídeo (thumbnail): automática, quadro escolhido ou imagem enviada.

A capa é embutida no MP4 (aparece como miniatura no Finder, Explorer e players) e exportada
como JPG 1920x1080 para subir no YouTube, LinkedIn ou na plataforma de treinamento.
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from ..core import config, jsonio, midia
from ..core.caminhos import MARCAS, pasta_projeto
from . import e0_gravacao, e4_legendas

W, H = 1920, 1080
EXT = {".png", ".jpg", ".jpeg", ".webp"}


def carregar(video_id: str) -> dict:
    proj = pasta_projeto(video_id)
    salvo = jsonio.ler(proj / "capa.json", {}) or {}
    mapa = jsonio.ler(proj / "mapa_de_cenas.json", {}) or {}
    cartoes = jsonio.ler(proj / "cartoes.json", {}) or {}
    m = e0_gravacao.meta(video_id) or {}
    titulo_padrao = ((cartoes.get("abertura") or {}).get("titulo") or mapa.get("produto") or m.get("nome") or "")
    c = {"modo": "automatica", "t_s": None, "imagem": "", "titulo": titulo_padrao, "subtitulo": "",
         "mostrar_texto": True}
    c.update({k: v for k, v in salvo.items() if k in c})
    return c


def salvar(video_id: str, dados: dict) -> dict:
    proj = pasta_projeto(video_id)
    atual = jsonio.ler(proj / "capa.json", {}) or {}
    if "modo" in dados and dados["modo"] in ("automatica", "quadro", "imagem"):
        atual["modo"] = dados["modo"]
    if "t_s" in dados:
        atual["t_s"] = None if dados["t_s"] in (None, "") else max(0.0, float(dados["t_s"]))
    for k in ("titulo", "subtitulo"):
        if k in dados:
            atual[k] = str(dados[k] or "")[:120]
    if "mostrar_texto" in dados:
        atual["mostrar_texto"] = bool(dados["mostrar_texto"])
    jsonio.gravar(proj / "capa.json", atual)
    return carregar(video_id)


def guardar_imagem(video_id: str, nome: str, conteudo: bytes) -> dict:
    ext = Path(nome).suffix.lower()
    if ext not in EXT:
        raise ValueError("Use PNG, JPG ou WEBP")
    proj = pasta_projeto(video_id)
    for antigo in proj.glob("capa_enviada.*"):
        antigo.unlink()
    arq = proj / f"capa_enviada{ext}"
    arq.write_bytes(conteudo)
    Image.open(arq).verify()
    atual = jsonio.ler(proj / "capa.json", {}) or {}
    atual.update({"modo": "imagem", "imagem": arq.name})
    jsonio.gravar(proj / "capa.json", atual)
    return carregar(video_id)


def melhor_instante(video_id: str) -> float:
    """Quadro mais representativo: meio da primeira cena de resultado com importância alta,
    senão a primeira de resultado, senão 40% do vídeo."""
    proj = pasta_projeto(video_id)
    mapa = jsonio.ler(proj / "mapa_de_cenas.json", {}) or {}
    cenas = mapa.get("cenas") or []
    for filtro in (lambda c: c["tipo"] == "resultado" and c["importancia"] == "alta",
                   lambda c: c["tipo"] == "resultado", lambda c: c["importancia"] == "alta"):
        cand = [c for c in cenas if filtro(c)]
        if cand:
            return round((cand[0]["inicio_s"] + cand[0]["fim_s"]) / 2, 2)
    perfil = jsonio.ler(proj / "perfil_video.json", {}) or {}
    dur = perfil.get("duracao_s") or (e0_gravacao.meta(video_id) or {}).get("duracao_s") or 10
    return round(dur * 0.4, 2)


def _fonte(tam):
    from PIL import ImageFont
    for f in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(f, tam)
        except OSError:
            continue
    return ImageFont.load_default()


def _cor(hexa, padrao):
    try:
        h = hexa.lstrip("#")
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    except Exception:  # noqa: BLE001
        return padrao


def gerar(video_id: str, saida: Path | None = None) -> Path:
    cfg = config.carregar()
    m = config.marca(cfg)
    c = carregar(video_id)
    proj = pasta_projeto(video_id)
    saida = saida or proj / "capa.jpg"
    if c["modo"] == "imagem" and c["imagem"] and (proj / c["imagem"]).exists():
        img = Image.open(proj / c["imagem"]).convert("RGB")
        # preenche 16:9 sem distorcer
        esc = max(W / img.width, H / img.height)
        img = img.resize((int(img.width * esc), int(img.height * esc)))
        x, y = (img.width - W) // 2, (img.height - H) // 2
        img.crop((x, y, x + W, y + H)).save(saida, quality=90)
        return saida
    base = proj / "base.mp4"
    origem = base if base.exists() else proj.parent / "video.mp4"
    t = c["t_s"] if c["modo"] == "quadro" and c["t_s"] is not None else melhor_instante(video_id)
    tmp = proj / "capa_quadro.jpg"
    midia.quadro(origem, t, tmp, W, 2)
    img = Image.open(tmp).convert("RGB").resize((W, H))
    if c["mostrar_texto"] and (c["titulo"] or c["subtitulo"]):
        # faixa inferior escurecida para o texto ficar legível sobre qualquer tela
        sombra = Image.new("L", (W, H), 0)
        ds = ImageDraw.Draw(sombra)
        for i in range(460):
            ds.line([(0, H - i), (W, H - i)], fill=int(215 * (1 - i / 460) ** 1.4))
        escuro = Image.new("RGB", (W, H), (0, 0, 0))
        img = Image.composite(escuro, img, sombra)
        d = ImageDraw.Draw(img)
        cor = (255, 255, 255)
        y = H - 110
        linhas_sub = e4_legendas.quebrar_linhas(c["subtitulo"], 60)[:1] if c["subtitulo"] else []
        linhas_tit = e4_legendas.quebrar_linhas(c["titulo"], 28)[:2] if c["titulo"] else []
        f_sub, f_tit = _fonte(44), _fonte(96)
        for ln in reversed(linhas_sub):
            d.text((96, y - 44), ln, fill=(225, 230, 235), font=f_sub)
            y -= 64
        for ln in reversed(linhas_tit):
            d.text((96, y - 100), ln, fill=cor, font=f_tit)
            y -= 112
        d.rectangle([96, y - 30, 96 + 140, y - 18], fill=_cor(m.get("cor_texto_cartao", "#FFFFFF"), (255, 255, 255)))
    logo = MARCAS / m["logotipo"] if m.get("logotipo") else None
    if logo and logo.exists():
        lg = Image.open(logo).convert("RGBA")
        lg.thumbnail((300, 140))
        img.paste(lg, (W - lg.width - 72, 64), lg)
    img.filter(ImageFilter.SHARPEN).save(saida, quality=90)
    return saida


def embutir(video: Path, capa: Path):
    """Embute a capa no MP4 como miniatura (attached picture), sem recodificar o vídeo."""
    tmp = video.with_suffix(".capa.mp4")
    midia.rodar(["ffmpeg", "-y", "-i", video, "-i", capa, "-map", "0:v:0", "-map", "0:a?", "-map", "0:s?", "-map", "1", "-c", "copy",
                 "-c:v:1", "mjpeg", "-disposition:v:1", "attached_pic", "-movflags", "+faststart", tmp])
    tmp.replace(video)
