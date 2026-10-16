"use strict";
/* Meus vídeos, novo vídeo (gravar ou importar), gravação e ajustes de corte */

/* ================= MEUS VÍDEOS ================= */

const FILTROS_LIB = [["todos", "Todos"], ["configurar", "A configurar"], ["revisar", "Para revisar"], ["aprovados", "Aprovados"]];
const LIB = { filtro: "todos", busca: "" };

function grupoSituacao(s) {
  if (s === "aprovado") return "aprovados";
  if (s === "narrado") return "revisar";
  return "configurar";
}

async function telaVideos() {
  const { videos } = await api("GET", "/api/biblioteca");
  conteudo().innerHTML = `
    <div class="linha" style="margin-bottom:6px"><div><h1>Meus vídeos</h1>
      <p class="sub">Manuais e treinamentos em vídeo. Abra um para editar, exporte ou crie uma nova versão quando o produto mudar.</p></div>
      <span class="espaco"></span><a class="btn prim grande" href="#/novo">${ic("mais")} Novo vídeo</a></div>
    ${videos.length ? `
    <div class="barra-lib">
      <input type="search" id="lib-busca" placeholder="Buscar pelo nome" value="${esc(LIB.busca)}" aria-label="Buscar vídeo pelo nome">
      ${segmentos("lib-filtro", FILTROS_LIB.map(([v, t]) => [v, `${t} (${v === "todos" ? videos.length : videos.filter((x) => grupoSituacao(x.situacao) === v).length})`]), LIB.filtro)}
    </div>
    <div class="galeria" id="galeria"></div>` : `
    <div class="cartao vazio"><div class="ico-grande">${ic("videos", "g")}</div>
      <h2 style="justify-content:center">Nenhum vídeo ainda</h2>
      <p>Grave a navegação numa aba do Chrome ou importe um vídeo. A IA escreve a narração, gera a voz e monta o vídeo.</p>
      <a class="btn prim grande" href="#/novo">${ic("mais")} Criar o primeiro vídeo</a>
      <div class="passos-vazio">
        <div><b>1. Grave ou importe</b>Navegue no produto como faria numa demonstração.</div>
        <div><b>2. Configure</b>Finalidade, abertura, encerramento, voz e música. Tudo opcional.</div>
        <div><b>3. Revise e exporte</b>Ajuste qualquer fala, imagem ou texto no editor.</div>
      </div></div>`}`;
  if (!videos.length) return;
  const desenhar = () => {
    const q = LIB.busca.trim().toLowerCase();
    const lista = videos.filter((v) => (LIB.filtro === "todos" || grupoSituacao(v.situacao) === LIB.filtro) && (!q || v.nome.toLowerCase().includes(q)));
    $("#galeria").innerHTML = lista.length ? lista.map(cardVideo).join("") : `<p class="peq">Nenhum vídeo neste filtro.</p>`;
  };
  desenhar();
  $("#lib-busca").oninput = (e) => { LIB.busca = e.target.value; desenhar(); };
  ligarSegmentos(conteudo(), "lib-filtro", (v) => { LIB.filtro = v; desenhar(); });
  $("#galeria").onclick = async (e) => {
    const ap = e.target.closest("[data-apagar]");
    if (ap) { e.preventDefault(); const v = videos.find((x) => x.id === ap.dataset.apagar); if (v) apagarVideo(v); }
  };
  if (videos.some((v) => ["convertendo", "gravando", "enviando"].includes(v.situacao))) {
    setTimeout(() => { if (location.hash === "#/videos" || location.hash === "") telaVideos(); }, 4000);
  }
}

function cardVideo(v) {
  const mini = v.tem_miniatura ? `<img src="/api/biblioteca/${v.id}/miniatura?${encodeURIComponent(v.criado_em)}" alt="">` : ic("videos", "g");
  const pronto = v.situacao === "narrado" || v.situacao === "aprovado";
  return `<div class="video-card">
    <a class="mini" href="#/video/${v.id}" aria-label="Abrir ${esc(v.nome)}">${mini}${v.duracao_s ? `<span class="dur">${fmtDur(v.duracao_s)}</span>` : ""}</a>
    <div class="dados"><a class="nome" href="#/video/${v.id}" title="${esc(v.nome)}">${esc(v.nome)}</a>
      <div class="peq">${esc(dataBr(v.criado_em))}${v.versao ? ` · versão ${v.versao}` : ""}</div>
      <div>${tagSituacao(v.situacao)}</div></div>
    <div class="acoes">
      <a class="btn peq" href="#/video/${v.id}">${ic("editar")} ${pronto ? "Editar" : "Continuar"}</a>
      ${pronto ? `<a class="btn peq" href="#/video/${v.id}/exportar" title="Exportar">${ic("baixar")} Exportar</a>` : ""}
      <span class="espaco"></span>
      <a class="btn-icone" href="#/novo?base=${v.id}" title="Nova versão (regravar mantendo as configurações)" aria-label="Nova versão">${ic("copiar")}</a>
      <button class="btn-icone" data-apagar="${v.id}" title="Apagar" aria-label="Apagar ${esc(v.nome)}">${ic("lixo")}</button>
    </div></div>`;
}

async function apagarVideo(v) {
  if (!(await confirmar("Apagar vídeo", `Apagar <b>${esc(v.nome)}</b> e todo o projeto de narração dele? Não dá para desfazer. Os arquivos já exportados continuam na pasta de exportados.`, "Apagar", "perigo"))) return;
  await api("DELETE", `/api/biblioteca/${v.id}`);
  toast("Vídeo apagado");
  if (location.hash === "#/videos") telaVideos(); else location.hash = "#/videos";
}

/* ================= NOVO VÍDEO ================= */

const NOVO = { modo: "gravar", base: null };

async function telaNovo(params) {
  if (ESTADO.gravando) { desenharPainelGravacao(); return; }
  const cfg = (await carregarConfig()).config;
  NOVO.base = params.get("base") || null;
  let base = null;
  if (NOVO.base) base = (await api("GET", "/api/biblioteca")).videos.find((x) => x.id === NOVO.base) || null;
  conteudo().innerHTML = `
    <a class="btn peq" href="#/videos">${ic("esquerda")} Meus vídeos</a>
    <h1 style="margin-top:14px">${base ? `Nova versão de ${esc(base.nome)}` : "Novo vídeo"}</h1>
    <p class="sub">${base ? "Grave de novo ou importe o vídeo atualizado. Finalidade, briefing, abertura, encerramento e capa vêm da versão anterior." : "Comece pela gravação da tela. Depois você configura abertura, encerramento, voz e música antes de gerar."}</p>
    <div class="cartao">
      <div class="campo" style="max-width:520px"><label for="novo-nome">Nome do vídeo</label>
        <input type="text" id="novo-nome" placeholder="${base ? "deixe vazio para usar o nome com a versão" : "ex.: Cadastro de fornecedor"}"></div>
      <label>Como você quer começar?</label>
      <div class="grade g2">
        <button type="button" class="opcao-grande ${NOVO.modo === "gravar" ? "sel" : ""}" data-modo="gravar">${ic("gravar", "g")}<b>Gravar uma aba do Chrome</b><span class="peq">Navegue no produto. A gravação fica só no seu computador.</span></button>
        <button type="button" class="opcao-grande ${NOVO.modo === "importar" ? "sel" : ""}" data-modo="importar">${ic("enviar", "g")}<b>Importar um vídeo</b><span class="peq">.mov, .mp4, .webm ou .mkv gravado em outra ferramenta.</span></button>
      </div>
    </div>
    <div id="novo-corpo"></div>`;
  const corpo = $("#novo-corpo");
  const desenharModo = () => {
    $$("[data-modo]").forEach((b) => b.classList.toggle("sel", b.dataset.modo === NOVO.modo));
    if (NOVO.modo === "gravar") {
      corpo.innerHTML = `<div class="grade g2">
        <div class="cartao"><h2>${ic("ok")} Antes de gravar</h2>
          ${["Deixe a janela do Chrome em 16:9 (ex.: 1920×1080) para não sair com faixas pretas",
            "Esconda a barra de favoritos e ative o Não perturbe",
            "Use dados de demonstração e feche abas com dados sensíveis",
            "Áudio e microfone ficam desligados: a narração é gerada depois",
          ].map((t, i) => `<label class="check"><input type="checkbox" id="ck${i}"> ${esc(t)}</label>`).join("")}
          <p class="peq" style="margin-top:10px">Comece parado e termine parado: a aplicação corta sozinha o começo e o fim sem ação. Limite: ${cfg.gravacao.limite_min} min.</p></div>
        <div class="cartao"><h2>${ic("gravar")} Gravar</h2>
          <div class="campo"><label for="url-grav">Endereço que você vai abrir (opcional, só para registro)</label><input type="url" id="url-grav" placeholder="https://app.exemplo.com/..."></div>
          <button class="btn rec grande" id="iniciar">${ic("gravar")} Escolher aba e iniciar</button>
          <p class="peq" style="margin-top:10px">O Chrome pede para escolher a aba a cada gravação. Conteúdo protegido por DRM aparece preto.</p></div></div>`;
      $("#iniciar").onclick = iniciarGravacao;
    } else {
      corpo.innerHTML = `<div class="cartao"><h2>${ic("enviar")} Importar vídeo</h2>
        <label class="opcao-grande" for="arquivo-import" style="align-items:center;text-align:center;border-style:dashed" id="zona-import">
          ${ic("enviar", "g")}<b>Clique para escolher ou arraste o arquivo aqui</b><span class="peq">O vídeo é comprimido para 1080p a 30 quadros/s. Pode levar alguns minutos.</span></label>
        <input type="file" id="arquivo-import" accept=".mov,.mp4,.webm,.m4v,.mkv,video/*" hidden>
        <div id="progresso-import" style="margin-top:12px"></div></div>`;
      $("#arquivo-import").onchange = (e) => e.target.files[0] && importarArquivo(e.target.files[0]);
      const z = $("#zona-import");
      z.ondragover = (e) => { e.preventDefault(); z.classList.add("sel"); };
      z.ondragleave = () => z.classList.remove("sel");
      z.ondrop = (e) => { e.preventDefault(); z.classList.remove("sel"); const f = e.dataTransfer.files[0]; if (f) importarArquivo(f); };
    }
  };
  $$("[data-modo]").forEach((b) => b.onclick = () => { NOVO.modo = b.dataset.modo; desenharModo(); });
  desenharModo();
}

/* depois de criar o vídeo (gravado ou importado): herda configurações e abre o assistente */
async function aposCriar(id) {
  const nome = ($("#novo-nome")?.value || NOVO.nomeDigitado || "").trim();
  try {
    if (NOVO.base) await api("POST", `/api/biblioteca/${id}/herdar`, { de: NOVO.base, renomear: !nome });
    if (nome) await api("PATCH", `/api/biblioteca/${id}`, { nome });
  } catch (_) { /* segue para o assistente */ }
  NOVO.base = null;
  NOVO.nomeDigitado = "";
  location.hash = `#/video/${id}/configurar`;
}

function importarArquivo(arq) {
  const box = $("#progresso-import");
  NOVO.nomeDigitado = $("#novo-nome").value;
  box.innerHTML = `<div class="peq"><b>Enviando ${esc(arq.name)}</b></div><div class="barra"><div id="barra-imp" style="width:0%"></div></div><div class="peq" id="txt-imp"></div>`;
  const xhr = new XMLHttpRequest();
  xhr.open("POST", `/api/biblioteca/importar?nome=${encodeURIComponent(arq.name)}`);
  xhr.upload.onprogress = (e) => {
    if (!e.lengthComputable) return;
    $("#barra-imp").style.width = `${(e.loaded / e.total) * 100}%`;
    $("#txt-imp").textContent = `${(e.loaded / 1048576).toFixed(0)} de ${(e.total / 1048576).toFixed(0)} MB`;
  };
  xhr.onload = () => {
    let d = {};
    try { d = JSON.parse(xhr.responseText); } catch (_) { /* */ }
    if (xhr.status >= 400) { box.innerHTML = `<div class="alerta erro">✕ ${esc(d.detail || "Falha no envio")}</div>`; return; }
    acompanhar(d.tarefa);
    aposCriar(d.video.id);
  };
  xhr.onerror = () => { box.innerHTML = `<div class="alerta erro">✕ Falha no envio</div>`; };
  xhr.send(arq);
}

/* ---------------- gravação da aba ---------------- */

async function iniciarGravacao() {
  if (!navigator.mediaDevices || !navigator.mediaDevices.getDisplayMedia) {
    toast("Este navegador não permite capturar abas. Use o Chrome em http://localhost:8898", "erro");
    return;
  }
  const cfg = ESTADO.cfg.config;
  NOVO.nomeDigitado = $("#novo-nome")?.value || "";
  let stream;
  try {
    stream = await navigator.mediaDevices.getDisplayMedia({
      video: { displaySurface: "browser", width: { ideal: 1920 }, height: { ideal: 1080 }, frameRate: { ideal: 30, max: 30 } },
      audio: false, preferCurrentTab: false, selfBrowserSurface: "exclude", surfaceSwitching: "include", monitorTypeSurfaces: "exclude",
    });
  } catch (e) {
    toast("Captura cancelada", "erro");
    return;
  }
  const trilha = stream.getVideoTracks()[0];
  const ajustes = trilha.getSettings();
  const tipos = ["video/webm;codecs=vp9", "video/webm;codecs=vp8", "video/webm"];
  const mime = tipos.find((t) => MediaRecorder.isTypeSupported(t)) || "";

  const cont = document.createElement("div");
  cont.className = "contagem";
  document.body.appendChild(cont);
  for (let i = 3; i > 0; i--) { cont.textContent = i; await new Promise((r) => setTimeout(r, 1000)); }
  cont.remove();

  const v = await api("POST", "/api/gravacoes", { nome: NOVO.nomeDigitado, url_inicial: $("#url-grav")?.value || "" });
  const g = {
    id: v.id, nome: v.nome, stream, trilha, ajustes, inicio: Date.now(), acumulado: 0, pausado: false,
    fila: [], seq: 0, enviados: 0, bytes: 0, enviando: false, parado: false, erroEnvio: "",
    limiteMs: cfg.gravacao.limite_min * 60000,
  };
  ESTADO.gravando = g;
  const rec = new MediaRecorder(stream, { mimeType: mime || undefined, videoBitsPerSecond: 8_000_000 });
  g.rec = rec;
  rec.ondataavailable = (ev) => { if (ev.data && ev.data.size) { g.fila.push({ seq: g.seq++, blob: ev.data }); bombearFila(g); } };
  rec.onstop = () => finalizarGravacao(g);
  trilha.addEventListener("ended", () => { if (!g.parado) pararGravacao(); });
  rec.start(3000);
  g.relogio = setInterval(() => atualizarCronometro(g), 250);
  if (!location.hash.startsWith("#/novo")) location.hash = "#/novo";
  desenharPainelGravacao();
}

async function bombearFila(g) {
  if (g.enviando) return;
  g.enviando = true;
  while (g.fila.length) {
    const item = g.fila[0];
    let tentativas = 0;
    for (;;) {
      try {
        await api("POST", `/api/gravacoes/${g.id}/bloco?seq=${item.seq}`, item.blob, { silencioso: true });
        break;
      } catch (e) {
        tentativas++;
        g.erroEnvio = `Falha ao salvar bloco ${item.seq} (tentativa ${tentativas}): ${e.message}`;
        await new Promise((r) => setTimeout(r, Math.min(1000 * tentativas, 5000)));
        if (tentativas > 20) { toast("Não foi possível salvar a gravação. Verifique se o contêiner está rodando.", "erro"); g.enviando = false; return; }
      }
    }
    g.erroEnvio = "";
    g.bytes += item.blob.size;
    g.enviados++;
    g.fila.shift();
  }
  g.enviando = false;
  if (g.parado && g.aguardandoFila) g.aguardandoFila();
}

const tempoGravado = (g) => g.acumulado + (g.pausado ? 0 : Date.now() - g.inicio);

function atualizarCronometro(g) {
  const ms = tempoGravado(g);
  const el = $("#cron");
  if (el) el.textContent = fmtDur(ms / 1000);
  const st = $("#status-envio");
  if (st) st.innerHTML = g.erroEnvio ? TAGS.aviso(g.erroEnvio) : `${TAGS.ok("blocos salvos")} <span class="peq">${g.enviados} blocos · ${(g.bytes / 1048576).toFixed(1)} MB${g.fila.length ? ` · ${g.fila.length} na fila` : ""}</span>`;
  if (ms >= g.limiteMs && !g.parado) { toast("Limite de duração atingido: gravação encerrada", "erro"); pararGravacao(); }
}

function desenharPainelGravacao() {
  const g = ESTADO.gravando;
  if (!g) return;
  const r = g.ajustes || {};
  const prop = r.width && r.height ? r.width / r.height : 16 / 9;
  const avisoProp = Math.abs(prop - 16 / 9) > 0.05
    ? `<div class="alerta aviso">⚠ A aba está em ${r.width}×${r.height} (proporção diferente de 16:9). O vídeo terá faixas pretas nas laterais ou em cima e embaixo.</div>` : "";
  conteudo().innerHTML = `
    <h1>Gravando: ${esc(g.nome)}</h1>
    <p class="sub">Volte para a aba escolhida e navegue. Esta página pode ficar em segundo plano.</p>
    ${avisoProp}
    <div class="cartao painel-rec">
      <div class="ind-rec ${g.pausado ? "pausado" : ""}"><span class="bola"></span>${g.pausado ? "⏸ PAUSADO" : "GRAVANDO"}</div>
      <div class="cronometro" id="cron">0:00</div>
      <div class="linha" style="justify-content:center">
        <button class="btn grande" id="pausar">${g.pausado ? `${ic("play")} Retomar` : `${ic("pausa")} Pausar`}</button>
        <button class="btn rec grande" id="parar">⏹ Parar e salvar</button>
      </div>
      <p class="peq" style="margin-top:14px">Captura: ${r.width || "?"}×${r.height || "?"} a ${Math.round(r.frameRate || 0) || "?"} quadros/s</p>
      <div id="status-envio" style="margin-top:6px"></div>
    </div>`;
  $("#pausar").onclick = () => {
    if (g.pausado) { g.rec.resume(); g.inicio = Date.now(); g.pausado = false; }
    else { g.rec.pause(); g.acumulado += Date.now() - g.inicio; g.pausado = true; }
    desenharPainelGravacao();
  };
  $("#parar").onclick = pararGravacao;
  atualizarCronometro(g);
}

function pararGravacao() {
  const g = ESTADO.gravando;
  if (!g || g.parado) return;
  g.parado = true;
  g.duracao = tempoGravado(g) / 1000;
  clearInterval(g.relogio);
  try { if (g.rec.state !== "inactive") g.rec.stop(); } catch (_) { finalizarGravacao(g); }
  g.stream.getTracks().forEach((t) => t.stop());
  conteudo().innerHTML = `<h1>Salvando gravação</h1><div class="cartao painel-rec"><p>⏳ Enviando os últimos blocos…</p></div>`;
}

async function finalizarGravacao(g) {
  if (g.finalizando) return;
  g.finalizando = true;
  await new Promise((r) => setTimeout(r, 300));
  if (g.fila.length || g.enviando) await new Promise((r) => { g.aguardandoFila = r; bombearFila(g); });
  ESTADO.gravando = null;
  try {
    const t = await api("POST", `/api/gravacoes/${g.id}/finalizar`, { duracao_s: g.duracao });
    acompanhar(t);
    await aposCriar(g.id);
  } catch (_) {
    location.hash = "#/videos";
  }
}

window.addEventListener("beforeunload", (e) => { if (ESTADO.gravando) { e.preventDefault(); e.returnValue = ""; } });

/* ================= CORTES E MARCADORES (avançado) ================= */

async function telaAjustes(id) {
  const lista = (await api("GET", "/api/biblioteca")).videos;
  const v = lista.find((x) => x.id === id);
  if (!v) throw new Error("Vídeo não encontrado");
  const cab = await cabProjeto(id, "ajustes");
  if (v.situacao_arquivo !== "pronto") {
    conteudo().innerHTML = `${cab}<div class="cartao">${tagSituacao(v.situacao)} <p style="margin-top:10px">O vídeo ainda está sendo preparado. Esta tela abre quando terminar.</p></div>`;
    setTimeout(() => { if (location.hash === `#/video/${id}/ajustes`) telaAjustes(id); }, 3000);
    return;
  }
  const auto = v.cortes_automaticos;
  let cortes = v.cortes_manuais ? { ...v.cortes } : auto ? { inicio_s: auto.inicio_s, fim_s: auto.fim_s } : { ...v.cortes };
  let cortesAlterados = false, voltarAuto = false;
  const marcadores = [...(v.marcadores || [])];
  conteudo().innerHTML = `${cab}
    <div class="alerta info">${ic("info")} <span>Tudo aqui é opcional. A aplicação já corta sozinha o começo e o fim parados, e a IA encontra os momentos importantes. Use só se quiser forçar algo específico.</span></div>
    <div class="grade g2">
      <div class="cartao"><video id="player" src="/api/biblioteca/${id}/video" controls preload="metadata"></video>
        <div class="linha" style="margin-top:10px"><span class="peq">Posição: <b id="pos">0:00.0</b> · ${fmtDur(v.duracao_s)} · ${esc(v.resolucao)}</span></div></div>
      <div>
        <div class="cartao"><h2>${ic("tesoura")} Início e fim</h2>
          <p class="peq" id="info-corte"></p>
          <div class="linha"><button class="btn peq" id="def-ini">Início aqui</button><span>Início: <b id="v-ini"></b></span>
            <span class="espaco"></span><button class="btn peq" id="def-fim">Fim aqui</button><span>Fim: <b id="v-fim"></b></span></div>
          <div class="linha" style="margin-top:8px"><button class="btn peq" id="ver-ini">${ic("play")} Ver início</button><button class="btn peq" id="ver-fim">${ic("play")} Ver fim</button><button class="btn peq" id="zerar">${ic("refazer")} Voltar ao automático</button></div>
        </div>
        <div class="cartao"><h2>★ Marcadores</h2>
          <p class="peq">Garanta que algo específico seja narrado naquele instante.</p>
          <div class="linha"><input type="text" id="nota-mk" placeholder="ex.: mostrar a validação do CNPJ" style="flex:1"><button class="btn" id="add-mk">★ Marcar aqui</button></div>
          <ul class="lista-mk" id="lista-mk"></ul>
        </div>
        <div class="linha"><button class="btn prim" id="salvar">Salvar</button><span class="peq">Vale na próxima geração do roteiro.</span></div>
      </div>
    </div>`;
  const player = $("#player");
  player.ontimeupdate = () => { $("#pos").textContent = fmtT(player.currentTime); };
  const desenhar = () => {
    const manual = (v.cortes_manuais || cortesAlterados) && !voltarAuto;
    $("#info-corte").innerHTML = manual
      ? `${TAGS.info("corte manual")} Você definiu o trecho usado. O arquivo original não é alterado.`
      : `${TAGS.ok("corte automático")} ${auto ? `Neste vídeo: ${auto.removido_s.toFixed(1)} s parados removidos.` : "Calculado ao gerar o roteiro."}`;
    $("#v-ini").textContent = fmtT(cortes.inicio_s);
    $("#v-fim").textContent = fmtT(cortes.fim_s ?? v.duracao_s);
    $("#lista-mk").innerHTML = marcadores.length ? marcadores.map((m, i) => `<li><button class="btn peq" data-ir="${i}">${ic("play")} ${fmtT(m.t_s)}</button><span style="flex:1">${esc(m.nota || "(sem nota)")}</span><button class="btn-icone" data-rm="${i}" aria-label="Remover marcador">${ic("x")}</button></li>`).join("")
      : `<li class="peq">Nenhum marcador.</li>`;
    $$("[data-ir]").forEach((b) => b.onclick = () => { player.currentTime = marcadores[+b.dataset.ir].t_s; });
    $$("[data-rm]").forEach((b) => b.onclick = () => { marcadores.splice(+b.dataset.rm, 1); desenhar(); });
  };
  desenhar();
  $("#def-ini").onclick = () => { cortes.inicio_s = +player.currentTime.toFixed(2); cortesAlterados = true; voltarAuto = false; desenhar(); };
  $("#def-fim").onclick = () => { cortes.fim_s = +player.currentTime.toFixed(2); cortesAlterados = true; voltarAuto = false; desenhar(); };
  $("#ver-ini").onclick = () => { player.currentTime = cortes.inicio_s; player.play(); };
  $("#ver-fim").onclick = () => { player.currentTime = Math.max(0, (cortes.fim_s ?? v.duracao_s) - 3); player.play(); };
  $("#zerar").onclick = () => { cortes = auto ? { inicio_s: auto.inicio_s, fim_s: auto.fim_s } : { inicio_s: 0, fim_s: v.duracao_s }; voltarAuto = true; cortesAlterados = false; desenhar(); };
  $("#add-mk").onclick = () => {
    marcadores.push({ t_s: +player.currentTime.toFixed(2), nota: $("#nota-mk").value.trim() });
    marcadores.sort((a, b) => a.t_s - b.t_s);
    $("#nota-mk").value = "";
    desenhar();
  };
  $("#salvar").onclick = async () => {
    const dados = { marcadores };
    if (voltarAuto) dados.cortes = null;
    else if (cortesAlterados) dados.cortes = cortes;
    await api("PATCH", `/api/biblioteca/${id}`, dados);
    toast("Cortes e marcadores salvos");
  };
}
