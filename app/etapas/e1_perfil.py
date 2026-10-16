"""Etapa 1: ingestão e perfil. Aplica os cortes e gera o vídeo-base do projeto."""
from ..core import jsonio, midia
from ..core.caminhos import pasta_projeto, pasta_video
from . import e0_gravacao


def executar(tarefa, video_id: str) -> dict:
    m = e0_gravacao.meta(video_id)
    if not m or m.get("situacao_arquivo") != "pronto":
        raise RuntimeError("O vídeo ainda não está pronto (gravação ou conversão em andamento)")
    origem = pasta_video(video_id) / "video.mp4"
    proj = pasta_projeto(video_id)
    if m.get("cortes_manuais"):
        ini = float(m["cortes"].get("inicio_s") or 0)
        fim = float(m["cortes"].get("fim_s") or m["duracao_s"])
        origem_corte = "manual"
    else:
        tarefa.etapa("Cortando automaticamente o começo e o fim parados", 0.01)
        auto = cortes_automaticos(video_id, m, origem)
        ini, fim = auto["inicio_s"], auto["fim_s"]
        origem_corte = "automático"
    base = proj / "base.mp4"
    assinatura = f"{ini:.2f}-{fim:.2f}-{origem.stat().st_mtime:.0f}"
    perfil_ant = jsonio.ler(proj / "perfil_video.json", {}) or {}
    if not base.exists() or perfil_ant.get("assinatura") != assinatura:
        tarefa.etapa("Aplicando cortes de início e fim", 0.02)
        if ini <= 0.01 and fim >= m["duracao_s"] - 0.05:
            midia.rodar(["ffmpeg", "-y", "-i", origem, "-c", "copy", "-movflags", "+faststart", base])
        else:
            midia.rodar(["ffmpeg", "-y", "-ss", f"{ini:.3f}", "-to", f"{fim:.3f}", "-i", origem,
                         "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-r", "30",
                         "-fps_mode", "cfr", "-an", "-movflags", "+faststart", base])
    tarefa.etapa("Medindo duração, resolução e quadros por segundo", 0.05)
    info = midia.sondar(base)
    marcadores = [
        {"t_s": round(x["t_s"] - ini, 2), "nota": x.get("nota", "")}
        for x in m.get("marcadores", []) if ini <= x["t_s"] <= fim
    ]
    eventos = [
        dict(e, t_s=round(e["t_s"] - ini, 2))
        for e in m.get("eventos", []) if ini <= e.get("t_s", -1) <= fim
    ]
    perfil = {
        "assinatura": assinatura, "duracao_s": info["duracao_s"], "resolucao": info["resolucao"],
        "fps": info["fps"], "taxa_variavel": info["taxa_variavel"], "tem_audio": info["tem_audio"],
        "corte_inicio_s": ini, "corte_fim_s": fim, "corte_origem": origem_corte,
        "marcadores": marcadores, "eventos": eventos,
    }
    jsonio.gravar(proj / "perfil_video.json", perfil)
    return perfil


def cortes_automaticos(video_id: str, m: dict, origem) -> dict:
    """Remove o trecho parado do começo (antes de a navegação começar) e encurta a tela parada do fim,
    mantendo 1 s antes do primeiro movimento e 3 s da tela final."""
    assinatura = f"{origem.stat().st_mtime:.0f}"
    salvo = m.get("cortes_automaticos") or {}
    if salvo.get("assinatura") == assinatura:
        return salvo
    dur = float(m["duracao_s"])
    ini, fim = 0.0, dur
    parados = midia.trechos_parados(origem, 1.0)
    if parados:
        p_ini, p_fim = parados[0]
        if p_ini <= 0.3 and p_fim and p_fim > 1.5:
            ini = round(p_fim - 1.0, 2)
        u_ini, u_fim = parados[-1]
        if (u_fim is None or u_fim >= dur - 0.2) and u_ini > ini and dur - u_ini > 3.5:
            fim = round(u_ini + 3.0, 2)
    if fim - ini < 3:
        ini, fim = 0.0, dur
    res = {"inicio_s": ini, "fim_s": fim, "assinatura": assinatura,
           "removido_s": round(dur - (fim - ini), 2)}
    m = e0_gravacao.meta(video_id)
    m["cortes_automaticos"] = res
    e0_gravacao.salvar_meta(video_id, m)
    return res
