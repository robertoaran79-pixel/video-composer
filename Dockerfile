# Video Composer · imagem da aplicação
FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    VC_TRABALHO=/trabalho \
    VC_DADOS=/dados \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PYTHONIOENCODING=utf-8

# FFmpeg (com libass para legendas) e fontes para cartões e legendas
RUN apt-get update \
 && apt-get install -y --no-install-recommends ffmpeg fonts-dejavu-core fonts-liberation fontconfig \
 && rm -rf /var/lib/apt/lists/* \
 && fc-cache -f

WORKDIR /opt/video-composer
COPY requirements.txt .
RUN pip install -r requirements.txt \
 && (pip install "kokoro-onnx==0.6.1" || echo "AVISO: Kokoro não instalado; a voz offline Kokoro ficará indisponível") \
 && (pip install "piper-tts>=1.3,<2" || echo "AVISO: Piper não instalado; a voz offline Piper ficará indisponível")

COPY app ./app

EXPOSE 8898
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8898/api/sistema', timeout=4)" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8898", "--timeout-keep-alive", "30"]
