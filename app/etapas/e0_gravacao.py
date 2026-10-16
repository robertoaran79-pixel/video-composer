"""Etapa 0: gravação da aba, importação e biblioteca."""
import secrets
import shutil
import time
from pathlib import Path

from ..core import config, jsonio, midia
from ..core.caminhos import BIBLIOTECA, nome_seguro, pasta_video

EXTENSOES_IMPORT = {".mov", ".mp4", ".webm", ".m4v", ".mkv"}


def novo_id() -> str:
    return time.strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(2)


def meta(video_id: str) -> dict:
    return jsonio.ler(pasta_video(video_id) / "gravacao.json", None)


def salvar_meta(video_id: str, dados: dict):
    jsonio.gravar(pasta_video(video_id) / "gravacao.json", dados)


def criar(nome: str, origem: str, url_inicial: str = "") -> dict:
    vid = novo_id()
    pasta = pasta_video(vid)
    pasta.mkdir(parents=True)
    nome = (nome or "").strip() or time.strftime("Gravação %d-%m-%Y %Hh%M")
    dados = {
        "id": vid, "nome": nome, "arquivo": "video.mp4", "origem": origem,
        "url_inicial": url_inicial, "criado_em": time.strftime("%Y-%m-%d %H:%M:%S"),
        "situacao_arquivo": "gravando" if origem == "aba do Chrome" else "enviando",
        "duracao_s": 0, "resolucao": "", "fps": 0, "tamanho_mb": 0,
        "cortes": {"inicio_s": 0.0, "fim_s": None}, "marcadores": [], "eventos": [],
    }
    salvar_meta(vid, dados)
    return dados


def anexar_bloco(video_id: str, seq: int, dados: bytes) -> int:
    pasta = pasta_video(video_id)
    controle = pasta / ".blocos"
    ultimo = int(controle.read_text()) if controle.exists() else -1
    if seq <= ultimo:
        return ultimo  # bloco repetido (reenvio): ignora
    if seq != ultimo + 1:
        raise ValueError(f"Bloco fora de ordem: esperado {ultimo + 1}, recebido {seq}")
    with open(pasta / "bruto.webm", "ab") as f:
        f.write(dados)
    controle.write_text(str(seq))
    return seq


def converter(tarefa, video_id: str, entrada_nome: str, extras: dict | None = None):
    """Converte para MP4 H.264, 1920x1080, 30 quadros constantes, sem áudio."""
    cfg = config.carregar()
    pasta = pasta_video(video_id)
    entrada = pasta / entrada_nome
    m = meta(video_id)
    m["situacao_arquivo"] = "convertendo"
    if extras:
        for k in ("marcadores", "url_inicial", "eventos"):
            if extras.get(k):
                m[k] = extras[k]
    salvar_meta(video_id, m)
    try:
        tarefa.etapa("Analisando o arquivo de origem", 0.05)
        info_origem = midia.sondar(entrada)
        tarefa.etapa(f"Comprimindo {info_origem.get('resolucao','')} para MP4 H.264 1080p a 30 quadros", 0.1)
        saida_tmp = pasta / "video.tmp.mp4"
        vf = ("scale=1920:1080:force_original_aspect_ratio=decrease:flags=lanczos,"
              "pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=black,fps=30,format=yuv420p")
        midia.rodar(["ffmpeg", "-y", "-i", entrada, "-vf", vf, "-c:v", "libx264", "-preset", "medium",
                     "-crf", cfg["gravacao"]["crf"], "-tune", "stillimage", "-r", "30", "-fps_mode", "cfr",
                     "-an", "-movflags", "+faststart", saida_tmp], timeout=7200)
        saida_tmp.replace(pasta / "video.mp4")
        tarefa.etapa("Gerando miniatura", 0.9)
        info = midia.sondar(pasta / "video.mp4")
        midia.quadro(pasta / "video.mp4", min(2.0, info["duracao_s"] / 3), pasta / "miniatura.jpg", 480)
        m = meta(video_id)
        m.update({
            "duracao_s": info["duracao_s"], "resolucao": info["resolucao"], "fps": 30,
            "tamanho_mb": info["tamanho_mb"], "situacao_arquivo": "pronto",
            "origem_info": {"resolucao": info_origem.get("resolucao"), "fps": info_origem.get("fps"),
                            "taxa_variavel": info_origem.get("taxa_variavel"),
                            "tamanho_mb": info_origem.get("tamanho_mb")},
        })
        if m["cortes"].get("fim_s") is None or m["cortes"]["fim_s"] > info["duracao_s"]:
            m["cortes"]["fim_s"] = info["duracao_s"]
        salvar_meta(video_id, m)
        if cfg["gravacao"]["apagar_bruto"]:
            entrada.unlink(missing_ok=True)
        (pasta / ".blocos").unlink(missing_ok=True)
        mb_min = info["tamanho_mb"] / max(info["duracao_s"] / 60, 0.01)
        return {"video_id": video_id, "tamanho_mb": info["tamanho_mb"], "mb_por_minuto": round(mb_min, 1)}
    except Exception:
        m = meta(video_id)
        m["situacao_arquivo"] = "erro"
        salvar_meta(video_id, m)
        raise


def situacao_projeto(video_id: str) -> str:
    p = pasta_video(video_id) / "projeto"
    apr = jsonio.ler(p / "aprovacoes.json", {}) or {}
    if apr.get("final"):
        return "aprovado"
    if (p / "video_final.mp4").exists():
        return "narrado"
    if (p / "roteiro.json").exists():
        return "roteiro pronto"
    return "bruto"


def listar() -> list:
    itens = []
    for pasta in sorted(BIBLIOTECA.glob("*/"), reverse=True):
        m = jsonio.ler(pasta / "gravacao.json")
        if not m:
            continue
        m["situacao"] = situacao_projeto(m["id"]) if m.get("situacao_arquivo") == "pronto" else m.get("situacao_arquivo")
        m["tem_miniatura"] = (pasta / "miniatura.jpg").exists()
        itens.append(m)
    return itens


def atualizar(video_id: str, dados: dict) -> dict:
    m = meta(video_id)
    if not m:
        raise FileNotFoundError("Vídeo não encontrado")
    if "nome" in dados:
        m["nome"] = (dados["nome"] or "").strip()[:150] or m["nome"]
    if "cortes" in dados and dados["cortes"] is None:
        m["cortes_manuais"] = False
        m["cortes"] = {"inicio_s": 0.0, "fim_s": m["duracao_s"]}
    elif "cortes" in dados:
        m["cortes_manuais"] = True
        ini = max(0.0, float(dados["cortes"].get("inicio_s") or 0))
        fim = dados["cortes"].get("fim_s")
        fim = m["duracao_s"] if fim in (None, "") else min(float(fim), m["duracao_s"])
        if fim - ini < 2:
            raise ValueError("O trecho cortado precisa ter pelo menos 2 segundos")
        m["cortes"] = {"inicio_s": round(ini, 2), "fim_s": round(fim, 2)}
    if "marcadores" in dados:
        mk = []
        for x in dados["marcadores"]:
            mk.append({"t_s": round(float(x["t_s"]), 2), "nota": str(x.get("nota", ""))[:300]})
        m["marcadores"] = sorted(mk, key=lambda x: x["t_s"])
    salvar_meta(video_id, m)
    return m


def apagar(video_id: str):
    pasta = pasta_video(video_id)
    if pasta.exists():
        shutil.rmtree(pasta)


def preparar_importacao(nome_arquivo: str) -> tuple[dict, Path]:
    ext = Path(nome_arquivo).suffix.lower()
    if ext not in EXTENSOES_IMPORT:
        raise ValueError(f"Formato não aceito: {ext}. Use .mov, .mp4, .webm, .m4v ou .mkv")
    m = criar(Path(nome_seguro(nome_arquivo)).stem, "importado")
    return m, pasta_video(m["id"]) / f"original{ext}"
