"""Etapa 6: trilha. Prepara a faixa (corta fade e silêncio do fim), emenda sem buracos,
nivela e abaixa sob a voz. Guarda o comprovante de licença junto do projeto."""
import math
import shutil
import tempfile
from pathlib import Path

from ..core import catalogo_musica, config, jsonio, midia
from ..core.caminhos import MUSICA, pasta_projeto
from . import cartoes, linha_do_tempo

EXT_MUSICA = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"}


def listar_musicas() -> list:
    res = []
    for p in sorted(MUSICA.glob("*")):
        if p.suffix.lower() in EXT_MUSICA:
            lic = _licenca(p)
            try:
                d = midia.duracao(p)
            except Exception:  # noqa: BLE001
                d = 0
            meta = catalogo_musica.metadados(p.name)
            res.append({"arquivo": p.name, "duracao_s": d, "tem_licenca": bool(lic),
                        "licenca": lic.name if lic else "", "titulo": meta.get("titulo", ""),
                        "autor": meta.get("autor", ""), "tipo_licenca": meta.get("licenca", ""),
                        "exige_atribuicao": bool(meta.get("exige_atribuicao")), "credito": meta.get("credito", ""),
                        "origem": meta.get("origem", "enviada"), "verificada": bool(meta.get("verificada")),
                        "aviso_plano": meta.get("aviso_plano", ""), "pagina": meta.get("pagina", "")})
    return res


def _licenca(musica: Path):
    candidatos = [musica.with_suffix(".txt"), musica.with_name(musica.stem + "_licenca.txt"),
                  musica.with_name(musica.stem + ".licenca.txt")]
    for c in candidatos:
        if c.exists():
            return c
    return None


def _envelope(segs, g_fundo, g_voz, subida=0.35, descida=0.5) -> str:
    if not segs:
        return f"{g_fundo:.5f}"
    termos = [f"clip(min((t-{a - subida:.3f})/{subida},({b + descida:.3f}-t)/{descida}),0,1)" for a, b in segs]
    expr = termos[0]
    for t in termos[1:]:
        expr = f"max({expr},{t})"
    return f"{g_fundo:.5f}+({g_voz - g_fundo:.5f})*{expr}"


def executar(tarefa, video_id: str) -> dict:
    cfg = config.carregar()
    proj = pasta_projeto(video_id)
    saida = proj / "trilha_final.wav"
    mus = cfg["musica"]
    if not mus.get("arquivo"):
        saida.unlink(missing_ok=True)
        tarefa.etapa("Sem música de fundo configurada", 0.1)
        return {"musica": None}
    origem = MUSICA / mus["arquivo"]
    if not origem.exists():
        raise RuntimeError(f"Música não encontrada na pasta de músicas: {mus['arquivo']}")
    perfil = jsonio.ler(proj / "perfil_video.json")
    encaixe = jsonio.ler(proj / "audio" / "encaixe.json", {}) or {}
    lt = linha_do_tempo.calcular(cartoes.carregar(video_id, cfg), perfil, encaixe)
    total = lt["total_s"]
    emenda = float(mus["emenda_s"])
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        tarefa.etapa("Preparando a música: removendo fade e silêncio do fim", 0.05)
        bruto = tmp / "bruto.wav"
        midia.rodar(["ffmpeg", "-y", "-i", origem, "-ac", "2", "-ar", "44100", bruto])  # lê do arquivo (m4a incluso)
        dur = midia.duracao(bruto)
        fim_util = midia.silencio_final(bruto) or dur
        if fim_util - float(mus["cortar_fim_s"]) > 20:
            fim_util -= float(mus["cortar_fim_s"])
        base = tmp / "base.wav"
        midia.rodar(["ffmpeg", "-y", "-i", bruto, "-t", f"{fim_util:.3f}", base])
        passo = max(fim_util - emenda, 5)
        n = max(1, math.ceil((total + 2) / passo) + 1) if fim_util < total + 2 else 1
        tarefa.etapa(f"Emendando a faixa {n} vez(es) com {emenda:.0f} s de transição", 0.1)
        emendada = tmp / "emendada.wav"
        if n == 1:
            shutil.copy(base, emendada)
        else:
            entradas = []
            for _ in range(n):
                entradas += ["-i", base]
            filtro, ant = [], "[0:a]"
            for k in range(1, n):
                rot = f"[e{k}]"
                filtro.append(f"{ant}[{k}:a]acrossfade=d={emenda:.2f}:c1=tri:c2=tri{rot}")
                ant = rot
            midia.rodar(["ffmpeg", "-y", *entradas, "-filter_complex", ";".join(filtro), "-map", ant, emendada])
        g_fundo = 10 ** (float(mus["nivel_fundo_db"]) / 20)
        g_voz = 10 ** (float(mus["nivel_sob_voz_db"]) / 20)
        segs = linha_do_tempo.segmentos_de_fala(encaixe, lt)
        script = tmp / "filtro.txt"
        script.write_text(
            f"[0:a]atrim=0:{total:.3f},asetpts=N/SR/TB,loudnorm=I=-16:TP=-1.5:LRA=11,"
            f"aresample=44100,aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,volume='{_envelope(segs, g_fundo, g_voz)}':eval=frame,"
            f"afade=t=in:d=1.5,afade=t=out:st={max(total - 2.5, 0):.3f}:d=2.5[s]", encoding="utf-8")
        tarefa.etapa("Nivelando e abaixando a música sob a voz", 0.15)
        try:
            midia.rodar(["ffmpeg", "-y", "-i", emendada, "-filter_complex", script.read_text(encoding="utf-8"), "-map", "[s]",
                         "-ac", "2", "-ar", "44100", saida])
        except RuntimeError:
            # plano B: volume fixo (sem abaixar sob a voz), para a montagem nunca parar por causa da música
            tarefa.etapa("Ajuste fino de volume indisponível neste FFmpeg; usando volume fixo", 0.15)
            midia.rodar(["ffmpeg", "-y", "-i", emendada, "-af",
                         f"atrim=0:{total:.3f},asetpts=N/SR/TB,aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,"
                         f"volume={g_voz:.4f},afade=t=in:d=1.5,afade=t=out:st={max(total - 2.5, 0):.3f}:d=2.5",
                         "-ac", "2", "-ar", "44100", saida])
    lic = _licenca(origem)
    destino = proj / "licenca_musica.txt"
    if lic:
        shutil.copy(lic, destino)
    else:
        destino.write_text(f"Comprovante de licença NÃO encontrado para {origem.name}.\n"
                           f"Coloque um arquivo {origem.stem}.txt ao lado da música com a licença e a data do download.\n",
                           encoding="utf-8")
    return {"musica": origem.name, "licenca": bool(lic), "emendas": n - 1, "duracao_s": total}
