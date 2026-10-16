"""Abertura e encerramento do vídeo: opcionais e editáveis por vídeo.

Cada cartão tem título, subtítulo, imagem (própria do vídeo, da marca ou gerada com cor e texto)
e uma fala opcional. A fala pode ser escrita pelo usuário (lida exatamente como escrita) ou,
na abertura, escrita pela IA junto com o roteiro. A duração do cartão estica para caber a fala.
"""
from pathlib import Path

from PIL import Image

from ..core import config, jsonio
from ..core.caminhos import MARCAS, pasta_projeto

QUAIS = ("abertura", "encerramento")
EXT_IMAGEM = {".png", ".jpg", ".jpeg", ".webp"}


def carregar(video_id: str, cfg: dict | None = None) -> dict:
    cfg = cfg or config.carregar()
    m = config.marca(cfg)
    proj = pasta_projeto(video_id)
    salvo = jsonio.ler(proj / "cartoes.json", {}) or {}
    mapa = jsonio.ler(proj / "mapa_de_cenas.json", {}) or {}
    from . import e0_gravacao
    nome_video = (e0_gravacao.meta(video_id) or {}).get("nome", "")
    produto = mapa.get("produto") or m.get("nome", "") or nome_video
    padrao = {
        "abertura": {"ativo": float(m["duracao_abertura_s"]) > 0, "titulo": nome_video or produto, "subtitulo": "",
                     "duracao_s": float(m["duracao_abertura_s"]) or 3.5, "imagem": "", "fala": "", "fala_auto": True,
                     "texto_sobre_imagem": True},
        "encerramento": {"ativo": float(m["duracao_encerramento_s"]) > 0, "titulo": produto, "subtitulo": "",
                         "duracao_s": float(m["duracao_encerramento_s"]) or 3.0, "imagem": "", "fala": "",
                         "fala_auto": False, "credito_musica": True, "texto_sobre_imagem": True},
        "transicao_s": float(m["duracao_transicao_s"]),
    }
    for k in QUAIS:
        padrao[k].update({x: v for x, v in (salvo.get(k) or {}).items() if x in padrao[k]})
        img = padrao[k]["imagem"]
        padrao[k]["imagem_url"] = f"/api/projetos/{video_id}/arquivo/{img}" if img and (proj / img).exists() else ""
        marca_img = m.get(f"{k}_imagem", "")
        padrao[k]["imagem_marca"] = marca_img if marca_img and (MARCAS / marca_img).exists() else ""
    if "transicao_s" in salvo:
        padrao["transicao_s"] = float(salvo["transicao_s"])
    return padrao


def salvar(video_id: str, dados: dict) -> dict:
    proj = pasta_projeto(video_id)
    atual = jsonio.ler(proj / "cartoes.json", {}) or {}
    for k in QUAIS:
        if k not in dados:
            continue
        d = dados[k] or {}
        c = dict(atual.get(k) or {})
        if "ativo" in d:
            c["ativo"] = bool(d["ativo"])
        for campo, limite in (("titulo", 120), ("subtitulo", 160), ("fala", 400)):
            if campo in d:
                c[campo] = str(d.get(campo) or "").strip()[:limite]
        if "duracao_s" in d:
            c["duracao_s"] = max(1.0, min(15.0, float(d.get("duracao_s") or 3)))
        if "fala_auto" in d:
            c["fala_auto"] = bool(d["fala_auto"])
        for campo in ("credito_musica", "texto_sobre_imagem"):
            if campo in d:
                c[campo] = bool(d[campo])
        if "imagem" in d and not d["imagem"]:  # remover imagem própria
            for antigo in proj.glob(f"cartao_{k}.*"):
                antigo.unlink()
            c["imagem"] = ""
        atual[k] = c
    if "transicao_s" in dados:
        atual["transicao_s"] = max(0.0, min(3.0, float(dados["transicao_s"] or 0)))
    jsonio.gravar(proj / "cartoes.json", atual)
    return carregar(video_id)


def guardar_imagem(video_id: str, qual: str, nome: str, conteudo: bytes) -> dict:
    if qual not in QUAIS:
        raise ValueError("Cartão inválido")
    ext = Path(nome).suffix.lower()
    if ext not in EXT_IMAGEM:
        raise ValueError("Use PNG, JPG ou WEBP")
    proj = pasta_projeto(video_id)
    for antigo in proj.glob(f"cartao_{qual}.*"):
        antigo.unlink()
    arq = proj / f"cartao_{qual}{ext}"
    arq.write_bytes(conteudo)
    Image.open(arq).verify()
    atual = jsonio.ler(proj / "cartoes.json", {}) or {}
    atual.setdefault(qual, {})["imagem"] = arq.name
    jsonio.gravar(proj / "cartoes.json", atual)
    return carregar(video_id)


def caminho_imagem(video_id: str, qual: str, cart: dict, m: dict) -> Path | None:
    """Imagem do cartão: a própria do vídeo; senão a da marca; senão nenhuma (cartão gerado)."""
    proj = pasta_projeto(video_id)
    img = cart[qual].get("imagem")
    if img and (proj / img).exists():
        return proj / img
    marca_img = m.get(f"{qual}_imagem", "")
    if marca_img and (MARCAS / marca_img).exists():
        return MARCAS / marca_img
    return None


def textos_fala(video_id: str, cart: dict, roteiro: dict | None, cfg: dict) -> dict:
    """Fala de cada cartão: {'abertura': (legenda, falado), 'encerramento': (legenda, falado)}."""
    from .e3_roteiro import aplicar_glossario
    glossario = cfg["narracao"].get("glossario", [])
    res = {}
    for k in QUAIS:
        c = cart[k]
        if not c["ativo"]:
            res[k] = ("", "")
        elif c.get("fala"):
            res[k] = (c["fala"], aplicar_glossario(c["fala"], glossario))
        elif k == "abertura" and c.get("fala_auto") and roteiro:
            ab = roteiro.get("abertura") or {}
            res[k] = (ab.get("texto_legenda", ""), ab.get("texto_falado", ""))
        else:
            res[k] = ("", "")
    return res
