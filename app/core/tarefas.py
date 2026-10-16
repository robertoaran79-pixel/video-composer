"""Tarefas em segundo plano com progresso, consultadas pela interface."""
import threading
import time
import traceback
import uuid

_tarefas: dict = {}
_lock = threading.Lock()
_ocupados: dict = {}  # video_id -> tarefa_id


class Cancelada(Exception):
    pass


class Tarefa:
    def __init__(self, tipo: str, video_id: str | None):
        self.id = uuid.uuid4().hex[:12]
        self.tipo = tipo
        self.video_id = video_id
        self.situacao = "rodando"  # rodando | ok | erro
        self.progresso = 0.0
        self.mensagem = "Iniciando"
        self.log: list[str] = []
        self.resultado = None
        self.erro = ""
        self.inicio = time.time()
        self.fim = None

    def etapa(self, mensagem: str, progresso: float | None = None):
        self.mensagem = mensagem
        if progresso is not None:
            self.progresso = max(0.0, min(1.0, progresso))
        self.log.append(f"{time.strftime('%H:%M:%S')} {mensagem}")
        print(f"[{self.tipo}:{self.video_id}] {mensagem}", flush=True)

    def dict(self):
        return {
            "id": self.id, "tipo": self.tipo, "video_id": self.video_id,
            "situacao": self.situacao, "progresso": round(self.progresso, 3),
            "mensagem": self.mensagem, "log": self.log[-30:], "erro": self.erro,
            "resultado": self.resultado,
            "duracao_s": round((self.fim or time.time()) - self.inicio, 1),
        }


def iniciar(tipo: str, video_id: str | None, funcao, *args, **kwargs) -> Tarefa:
    with _lock:
        if video_id and video_id in _ocupados:
            atual = _tarefas.get(_ocupados[video_id])
            if atual and atual.situacao == "rodando":
                raise RuntimeError(f"Já existe uma tarefa em andamento para este vídeo: {atual.tipo}")
        t = Tarefa(tipo, video_id)
        _tarefas[t.id] = t
        if video_id:
            _ocupados[video_id] = t.id

    def rodar():
        try:
            t.resultado = funcao(t, *args, **kwargs)
            t.situacao = "ok"
            t.progresso = 1.0
            t.etapa("Concluído")
        except Exception as e:  # noqa: BLE001
            t.situacao = "erro"
            t.erro = str(e) or e.__class__.__name__
            t.etapa(f"Erro: {t.erro}")
            traceback.print_exc()
        finally:
            t.fim = time.time()
            with _lock:
                if video_id and _ocupados.get(video_id) == t.id:
                    _ocupados.pop(video_id, None)

    threading.Thread(target=rodar, daemon=True).start()
    return t


def obter(tid: str):
    return _tarefas.get(tid)


def do_video(video_id: str):
    tid = _ocupados.get(video_id)
    return _tarefas.get(tid) if tid else None


def recentes(n=20):
    return [t.dict() for t in sorted(_tarefas.values(), key=lambda x: -x.inicio)[:n]]
