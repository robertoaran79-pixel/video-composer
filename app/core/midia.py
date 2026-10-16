"""Utilitários de FFmpeg e áudio. Tudo determinístico."""
import array
import json
import re
import subprocess
import wave
from fractions import Fraction
from pathlib import Path

TAXA = 44100  # Hz, mono 16 bits para narração


class ErroMidia(RuntimeError):
    pass


def rodar(cmd: list, timeout: int = 3600) -> subprocess.CompletedProcess:
    cmd = [str(c) for c in cmd]
    if cmd[0] == "ffmpeg" and "-nostdin" not in cmd:
        cmd = [cmd[0], "-nostdin", "-hide_banner", "-loglevel", "error"] + cmd[1:]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if p.returncode != 0:
        cauda = (p.stderr or "").strip().splitlines()[-12:]
        raise ErroMidia(f"Falha ao executar {cmd[0]}: " + " | ".join(cauda))
    return p


def sondar(caminho: Path) -> dict:
    p = rodar(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", caminho])
    d = json.loads(p.stdout)
    fmt = d.get("format", {})
    v = next((s for s in d.get("streams", []) if s.get("codec_type") == "video"), None)
    a = next((s for s in d.get("streams", []) if s.get("codec_type") == "audio"), None)
    out = {
        "duracao_s": round(float(fmt.get("duration") or 0), 3),
        "tamanho_mb": round(int(fmt.get("size") or 0) / 1_048_576, 2),
        "tem_audio": a is not None,
    }
    if v:
        r = _fr(v.get("r_frame_rate"))
        avg = _fr(v.get("avg_frame_rate"))
        out.update({
            "largura": v.get("width"), "altura": v.get("height"),
            "resolucao": f"{v.get('width')}x{v.get('height')}",
            "codec": v.get("codec_name"),
            "fps": round(avg or r or 0, 3),
            "fps_nominal": round(r or 0, 3),
            "taxa_variavel": bool(r and avg and abs(r - avg) > 0.5),
        })
        if not out["duracao_s"] and v.get("duration"):
            out["duracao_s"] = round(float(v["duration"]), 3)
    return out


def _fr(s):
    try:
        f = Fraction(s)
        return float(f) if f else 0.0
    except Exception:  # noqa: BLE001
        return 0.0


def duracao(caminho: Path) -> float:
    return sondar(caminho)["duracao_s"]


def quadro(video: Path, t: float, saida: Path, largura: int = 480, qualidade: int = 4):
    saida.parent.mkdir(parents=True, exist_ok=True)
    rodar(["ffmpeg", "-y", "-ss", f"{max(0, t):.3f}", "-i", video, "-frames:v", "1",
           "-vf", f"scale={largura}:-2", "-q:v", qualidade, saida])
    return saida


def trocas_de_cena(video: Path, limiar: float = 0.06) -> list[tuple[float, float]]:
    """Retorna [(t, score)] das trocas de cena (vídeo reduzido para acelerar)."""
    cmd = ["ffmpeg", "-nostdin", "-hide_banner", "-i", str(video), "-an",
           "-vf", f"scale=480:-2,select='gt(scene,{limiar})',metadata=print", "-f", "null", "-"]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
    res, t = [], None
    for linha in p.stderr.splitlines():
        m = re.search(r"pts_time:([\d.]+)", linha)
        if m:
            t = float(m.group(1))
        m = re.search(r"lavfi\.scene_score=([\d.]+)", linha)
        if m and t is not None:
            res.append((round(t, 2), round(float(m.group(1)), 3)))
            t = None
    return res


# ---------- WAV mono 16 bits ----------

def para_wav(entrada: Path, saida: Path, aparar: bool = True, taxa: int = TAXA):
    filtros = []
    if aparar:
        s = "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.02"
        filtros = [s, "areverse", s, "areverse"]
    cmd = ["ffmpeg", "-y", "-i", entrada]
    if filtros:
        cmd += ["-af", ",".join(filtros)]
    cmd += ["-ac", "1", "-ar", taxa, "-sample_fmt", "s16", saida]
    rodar(cmd)
    return saida


def acelerar(entrada: Path, saida: Path, fator: float):
    """Muda a velocidade sem alterar o tom (atempo)."""
    if abs(fator - 1.0) < 0.005:
        if entrada != saida:
            saida.write_bytes(entrada.read_bytes())
        return saida
    rodar(["ffmpeg", "-y", "-i", entrada, "-af", f"atempo={fator:.4f}", "-ac", "1", "-ar", TAXA,
           "-sample_fmt", "s16", saida])
    return saida


def dur_wav(caminho: Path) -> float:
    with wave.open(str(caminho), "rb") as w:
        return w.getnframes() / float(w.getframerate())


def ler_pcm(caminho: Path) -> array.array:
    with wave.open(str(caminho), "rb") as w:
        if w.getnchannels() != 1 or w.getsampwidth() != 2 or w.getframerate() != TAXA:
            raise ErroMidia(f"WAV fora do padrão: {caminho.name}")
        a = array.array("h")
        a.frombytes(w.readframes(w.getnframes()))
        return a


def montar_linha_do_tempo(trechos: list[tuple[float, Path]], duracao_total: float, saida: Path):
    """Posiciona cada WAV no instante indicado numa faixa de silêncio."""
    n = int(round(duracao_total * TAXA))
    faixa = array.array("h", bytes(2 * n))
    for t, arq in trechos:
        pcm = ler_pcm(arq)
        ini = int(round(t * TAXA))
        if ini >= n:
            continue
        fim = min(n, ini + len(pcm))
        faixa[ini:fim] = pcm[: fim - ini]
    with wave.open(str(saida), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(TAXA)
        w.writeframes(faixa.tobytes())
    return saida


def tom_de_teste(texto: str, saida: Path, car_s: float = 11.0, velocidade: float = 1.0):
    """Gera um áudio sintético (modo de teste) com a duração que a fala teria."""
    d = max(0.4, len(texto) / car_s / velocidade)
    rodar(["ffmpeg", "-y", "-f", "lavfi", "-i", f"sine=frequency=330:duration={d:.3f}",
           "-af", "volume=0.2", "-ac", "1", "-ar", TAXA, "-sample_fmt", "s16", saida])
    return saida


def pico_db(caminho: Path) -> float:
    p = subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-i", str(caminho), "-vn", "-af",
                        "volumedetect", "-f", "null", "-"], capture_output=True, text=True)
    m = re.search(r"max_volume:\s*(-?[\d.]+) dB", p.stderr)
    return float(m.group(1)) if m else 0.0


def trechos_pretos(caminho: Path) -> list[tuple[float, float]]:
    p = subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-i", str(caminho), "-an", "-vf",
                        "blackdetect=d=0.5:pix_th=0.08", "-f", "null", "-"], capture_output=True, text=True)
    res = []
    for m in re.finditer(r"black_start:([\d.]+) black_end:([\d.]+)", p.stderr):
        res.append((float(m.group(1)), float(m.group(2))))
    return res


def silencio_final(caminho: Path, limiar_db: int = -50) -> float | None:
    """Instante em que começa o silêncio final do arquivo (ou None)."""
    p = subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-i", str(caminho), "-af",
                        f"silencedetect=noise={limiar_db}dB:d=0.5", "-f", "null", "-"],
                       capture_output=True, text=True)
    inicios = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", p.stderr)]
    fins = re.findall(r"silence_end: ([\d.]+)", p.stderr)
    if inicios and len(fins) < len(inicios):  # silêncio vai até o fim
        return inicios[-1]
    return None


def trechos_parados(caminho: Path, duracao_min: float = 1.0) -> list[tuple[float, float | None]]:
    """Trechos em que a imagem não muda (freezedetect). fim None = parado até o fim."""
    p = subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-i", str(caminho), "-an", "-vf",
                        f"scale=480:-2,freezedetect=n=0.002:d={duracao_min}", "-f", "null", "-"],
                       capture_output=True, text=True, timeout=3600)
    inicios = [float(x) for x in re.findall(r"freeze_start: ([\d.]+)", p.stderr)]
    fins = [float(x) for x in re.findall(r"freeze_end: ([\d.]+)", p.stderr)]
    return [(ini, fins[i] if i < len(fins) else None) for i, ini in enumerate(inicios)]
