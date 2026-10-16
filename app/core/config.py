"""Configurações da aplicação (sem segredos). Ficam em trabalho/configuracoes.json."""
import copy
import threading

from . import jsonio
from .caminhos import CONFIG

PADRAO = {
    "versao": 1,
    "aparencia": {"tema": "marinho"},  # ver PALETAS em app/web/app.js e styles.css
    "claude": {
        "modelos": {
            "entendimento": "claude-opus-5-5",
            "roteiro": "claude-opus-5-5",
            "qa": "claude-haiku-5-5",
        }
    },
    "voz": {
        "motor": "elevenlabs",  # elevenlabs | kokoro | piper
        "elevenlabs": {"voice_id": "", "nome": "", "modelo": "eleven_multilingual_v2"},
        "piper": {"modelo": "pt_BR-faber-medium"},
        "kokoro": {"voz": "pf_dora"},
        "calibracoes": {},  # "motor|voz|modelo": {"car_s": 10.5, "data": "..."}
        "ritmo_padrao_car_s": 12.0,
        "aceleracao_max": 1.30,
    },
    "marca_ativa": "padrao",
    "marcas": {
        "padrao": {
            "nome": "Padrão",
            "abertura_imagem": "",
            "encerramento_imagem": "",
            "logotipo": "",
            "cor_fundo_cartao": "#0F172A",
            "cor_texto_cartao": "#FFFFFF",
            "cor_legenda": "#FFFFFF",
            "cor_fundo_legenda": "#000000",
            "opacidade_fundo_legenda": 0.55,
            "fonte": "DejaVu Sans",
            "tamanho_fonte": 42,
            "duracao_abertura_s": 3.5,
            "duracao_transicao_s": 0.8,
            "duracao_encerramento_s": 3.0,
        }
    },
    "musica": {
        "arquivo": "",
        "nivel_fundo_db": -20,
        "nivel_sob_voz_db": -32,
        "cortar_fim_s": 3.0,
        "emenda_s": 3.0,
    },
    "narracao": {
        "idioma": "pt-BR",
        "tom": "claro, direto e profissional",
        "persona": "apresentador de produto",
        "publico": "",
        "glossario": [],  # [{"termo": "GenIntegrations", "falado": "Gen Integreichons"}]
    },
    "exportacao": {
        "horizontal": True,
        "vertical": False,
        "sem_narracao": False,
        "legenda": "gravada",  # gravada | selecionavel | nenhuma
        "srt_separado": True,
    },
    "privacidade": {"aviso_aceito": False, "limite_custo_usd": 2.00},
    "gravacao": {"limite_min": 15, "apagar_bruto": True, "crf": 23},
}

_lock = threading.Lock()


def _mesclar(base, novo):
    for k, v in (novo or {}).items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _mesclar(base[k], v)
        else:
            base[k] = v
    return base


def carregar() -> dict:
    with _lock:
        cfg = copy.deepcopy(PADRAO)
        _mesclar(cfg, jsonio.ler(CONFIG, {}))
        return cfg


def salvar(parcial: dict) -> dict:
    with _lock:
        cfg = copy.deepcopy(PADRAO)
        _mesclar(cfg, jsonio.ler(CONFIG, {}))
        # dicionários que o usuário substitui por inteiro
        for chave_lista in (("narracao", "glossario"),):
            a, b = chave_lista
            if a in parcial and b in (parcial.get(a) or {}):
                cfg[a][b] = []
        _mesclar(cfg, parcial)
        jsonio.gravar(CONFIG, cfg)
        return cfg


def marca(cfg: dict) -> dict:
    m = copy.deepcopy(PADRAO["marcas"]["padrao"])
    m.update(cfg["marcas"].get(cfg.get("marca_ativa"), {}) or {})
    return m


def chave_voz(cfg: dict) -> str:
    v = cfg["voz"]
    if v["motor"] == "elevenlabs":
        return f"elevenlabs|{v['elevenlabs'].get('voice_id','')}|{v['elevenlabs'].get('modelo','')}"
    if v["motor"] == "teste":
        return "teste|tom|1"
    if v["motor"] == "kokoro":
        return f"kokoro|{v.get('kokoro', {}).get('voz', 'pf_dora')}|v1.0"
    return f"piper|{v['piper'].get('modelo','')}|-"


def ritmo_voz(cfg: dict):
    """Retorna (car_s, calibrado: bool)."""
    cal = cfg["voz"]["calibracoes"].get(chave_voz(cfg))
    if cal and cal.get("car_s"):
        return float(cal["car_s"]), True
    return float(cfg["voz"]["ritmo_padrao_car_s"]), False
