"""Catálogo de músicas livres via Openverse (api.openverse.org).

A Openverse indexa áudio com licenças Creative Commons (Jamendo, Freesound, ccMixter,
Wikimedia). Não exige chave para uso anônimo (limite de 20 resultados por página).

Licenças aceitas para música de fundo em vídeo:
- cc0 e pdm: uso livre, sem atribuição;
- by: uso livre com atribuição (o crédito é gerado e guardado automaticamente).
Ficam de fora: NC (não comercial), ND (sem obras derivadas) e SA (obriga a mesma licença no vídeo).
"""
import re
import time
import unicodedata
from pathlib import Path

import httpx

from . import jsonio, midia
from .caminhos import MODO_TESTE, MUSICA

URL = "https://api.openverse.org/v1/audio/"
CABECALHO = {"User-Agent": "VideoComposer/0.3 (local demo video app)"}  # cabeçalhos HTTP só aceitam ASCII
LICENCAS = {"livre": "cc0,pdm", "atribuicao": "by", "todas": "cc0,pdm,by"}
SUGESTOES = ["corporate", "technology", "inspiring", "ambient", "lofi", "piano", "upbeat", "acoustic", "cinematic", "minimal"]


class ErroCatalogo(RuntimeError):
    pass


def _slug(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-").lower()[:60] or "musica"


def _item(r: dict) -> dict:
    return {
        "id": r.get("id"), "titulo": r.get("title") or "Sem título", "autor": r.get("creator") or "",
        "duracao_s": round((r.get("duration") or 0) / 1000, 1),
        "licenca": (r.get("license") or "").lower(), "licenca_versao": r.get("license_version") or "",
        "licenca_url": r.get("license_url") or "", "atribuicao": r.get("attribution") or "",
        "generos": r.get("genres") or [], "fonte": r.get("source") or r.get("provider") or "",
        "pagina": r.get("foreign_landing_url") or "", "arquivo_url": r.get("url") or "",
        "tipo": r.get("filetype") or "", "capa": r.get("thumbnail") or "",
        "exige_atribuicao": (r.get("license") or "").lower() == "by",
    }


def buscar(termo: str, licenca: str = "livre", duracao: str = "medium,long", pagina: int = 1) -> dict:
    if MODO_TESTE:
        return _busca_de_teste(termo)
    params = {"q": termo or "background", "category": "music", "license": LICENCAS.get(licenca, LICENCAS["todas"]),
              "page_size": 20, "page": max(1, int(pagina)), "filter_dead": "true", "mature": "false"}
    if duracao:
        params["length"] = duracao
    try:
        r = httpx.get(URL, params=params, headers=CABECALHO, timeout=25, follow_redirects=True)
    except httpx.HTTPError as e:
        raise ErroCatalogo(f"Sem conexão com o catálogo de músicas (Openverse): {e}") from e
    if r.status_code == 429:
        raise ErroCatalogo("O catálogo limitou as buscas por alguns minutos. Tente de novo em instantes.")
    if r.status_code != 200:
        raise ErroCatalogo(f"O catálogo respondeu {r.status_code}: {r.text[:200]}")
    d = r.json()
    itens = [_item(x) for x in d.get("results", [])]
    itens = [i for i in itens if i["arquivo_url"] and i["licenca"] in ("cc0", "pdm", "by")]
    return {"itens": itens, "total": d.get("result_count", len(itens)), "paginas": d.get("page_count", 1), "pagina": pagina}


def baixar(item: dict) -> dict:
    """Baixa a faixa para trabalho/musica e grava o comprovante de licença (.txt) e os metadados (.json)."""
    if item.get("licenca") not in ("cc0", "pdm", "by"):
        raise ErroCatalogo("Licença não permitida para uso comercial em vídeo")
    url = item.get("arquivo_url", "")
    if not url.startswith(("http://", "https://")):
        raise ErroCatalogo("Endereço da faixa inválido")
    ext = (item.get("tipo") or Path(url.split("?")[0]).suffix.lstrip(".") or "mp3").lower()
    if ext not in ("mp3", "wav", "ogg", "flac", "m4a", "aac"):
        ext = "mp3"
    base = f"{_slug(item.get('titulo', ''))}-{_slug(item.get('autor', ''))}"[:90]
    destino = MUSICA / f"{base}.{ext}"
    MUSICA.mkdir(parents=True, exist_ok=True)
    if MODO_TESTE and url.startswith("http://teste"):
        midia.rodar(["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=262:duration=40", "-f", "lavfi", "-i",
                     "sine=frequency=392:duration=40", "-filter_complex", "amix=inputs=2,volume=0.5", "-ac", "2", destino])
    else:
        try:
            with httpx.stream("GET", url, headers=CABECALHO, timeout=120, follow_redirects=True) as r:
                if r.status_code != 200:
                    raise ErroCatalogo(f"Não foi possível baixar a faixa ({r.status_code})")
                tam = 0
                with open(destino, "wb") as f:
                    for parte in r.iter_bytes():
                        tam += len(parte)
                        if tam > 80 * 1_048_576:
                            raise ErroCatalogo("Faixa grande demais (mais de 80 MB)")
                        f.write(parte)
        except httpx.HTTPError as e:
            destino.unlink(missing_ok=True)
            raise ErroCatalogo(f"Falha ao baixar a faixa: {e}") from e
    try:
        dur = midia.duracao(destino)
    except Exception as e:  # noqa: BLE001
        destino.unlink(missing_ok=True)
        raise ErroCatalogo("O arquivo baixado não é um áudio válido") from e
    lic = {"cc0": "CC0", "by": "CC BY", "pdm": "Domínio público (PDM)"}[item["licenca"]]
    credito = f"Música: \"{item.get('titulo','')}\" por {item.get('autor','') or 'autor desconhecido'} ({lic} {item.get('licenca_versao','')})".strip()
    texto = [
        "COMPROVANTE DE LICENÇA DE MÚSICA",
        f"Baixado em: {time.strftime('%d/%m/%Y %H:%M')} pelo Video Composer, via Openverse",
        f"Faixa: {item.get('titulo','')}",
        f"Autor: {item.get('autor','')}",
        f"Licença: {lic} {item.get('licenca_versao','')}  {item.get('licenca_url','')}",
        f"Página da obra: {item.get('pagina','')}",
        f"Fonte: {item.get('fonte','')}",
        f"Arquivo: {url}",
        "",
        f"Atribuição: {item.get('atribuicao','')}",
        "",
        ("Esta licença EXIGE crédito ao autor. O Video Composer coloca o crédito no encerramento e no arquivo de créditos exportado."
         if item["licenca"] == "by" else "Esta licença não exige crédito ao autor."),
        "Atenção: licenças Creative Commons não impedem que o YouTube identifique a faixa pelo Content ID.",
        "Guarde este comprovante para contestar uma reivindicação, se ocorrer.",
    ]
    destino.with_suffix(".txt").write_text("\n".join(texto) + "\n", encoding="utf-8")
    meta = dict(item, arquivo=destino.name, credito=credito, baixado_em=time.strftime("%Y-%m-%d %H:%M"), duracao_s=dur,
                origem="catalogo_aberto", verificada=False)
    jsonio.gravar(destino.with_suffix(".json"), meta)
    return meta


def metadados(arquivo: str) -> dict:
    meta = jsonio.ler((MUSICA / arquivo).with_suffix(".json"), {}) or {}
    if not meta and (MUSICA / arquivo).exists():
        meta = {"arquivo": arquivo, "origem": "enviada", "verificada": False}
    return meta


def confirmar_licenca(arquivo: str, origem_licenca: str = "") -> dict:
    """O usuário confirma que conferiu a licença na fonte (ou que a empresa licenciou a faixa)."""
    meta = metadados(arquivo)
    if not meta:
        raise FileNotFoundError("Faixa não encontrada")
    meta["verificada"] = True
    meta["verificada_em"] = time.strftime("%Y-%m-%d %H:%M")
    if origem_licenca:
        meta["origem_licenca"] = origem_licenca[:200]
    jsonio.gravar((MUSICA / arquivo).with_suffix(".json"), meta)
    txt = (MUSICA / arquivo).with_suffix(".txt")
    linha = f"\nLicença confirmada pelo usuário em {time.strftime('%d/%m/%Y %H:%M')}" + (f": {origem_licenca}" if origem_licenca else "") + "\n"
    with open(txt, "a", encoding="utf-8") as f:
        f.write(linha)
    return meta


def _busca_de_teste(termo: str) -> dict:
    itens = []
    for i in range(6):
        itens.append({
            "id": f"teste-{i}", "titulo": f"{termo or 'Trilha'} {i + 1}", "autor": "Autor de Teste",
            "duracao_s": 95 + i * 10, "licenca": "by" if i % 2 else "cc0", "licenca_versao": "4.0" if i % 2 else "1.0",
            "licenca_url": "https://creativecommons.org/", "atribuicao": f"\"{termo} {i + 1}\" by Autor de Teste is licensed under CC BY 4.0.",
            "generos": ["electronic"], "fonte": "teste", "pagina": "", "arquivo_url": f"http://teste/{i}.mp3",
            "tipo": "mp3", "capa": "", "exige_atribuicao": bool(i % 2),
        })
    return {"itens": itens, "total": 6, "paginas": 1, "pagina": 1}
