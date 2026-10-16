"use strict";
/* Projeto de um vídeo: cabeçalho, assistente de configuração (antes do editor),
   editor de abertura e encerramento, roteiro e voz (telas avançadas) */

/* ---------------- cabeçalho comum ---------------- */

async function cabProjeto(id, ativo, p = null) {
  p = p || await api("GET", `/api/projetos/${id}`);
  const v = p.video;
  const sit = p.situacao;
  const configurado = sit !== "bruto";
  const passos = [
    ["configurar", "Configurar", configurado],
    ["editor", "Revisar no editor", !!p.aprovacoes?.final],
    ["exportar", "Exportar", false],
  ];
  return `<div class="cab-video">
    <a class="btn-icone" href="#/videos" title="Meus vídeos" aria-label="Voltar para Meus vídeos">${ic("esquerda")}</a>
    <div style="min-width:0"><div class="titulo">${esc(v.nome)}</div>
      <div class="peq">${v.duracao_s ? `${fmtDur(v.duracao_s)} gravados · ` : ""}${esc(dataBr(v.criado_em))}${v.versao ? ` · versão ${v.versao}` : ""} · ${tagSituacao(v.situacao_arquivo === "pronto" ? sit : v.situacao_arquivo)}</div></div>
    <span class="espaco"></span>
    <div class="passos" style="margin:0">${passos.map(([k, t, feito], i) => `${i ? '<span class="sep"></span>' : ""}<a class="passo ${k === ativo ? "ativo" : ""} ${feito && k !== ativo ? "feito" : ""}" href="#/video/${id}/${k}">
      <span class="num">${feito && k !== ativo ? "✓" : i + 1}</span>${t}</a>`).join("")}</div>
    <details class="menu-mais"><summary class="btn-icone" title="Mais opções" aria-label="Mais opções">⋯</summary>
      <div class="menu">
        <a href="#/video/${id}/roteiro" class="${ativo === "roteiro" ? "ativo" : ""}">${ic("roteiro")} Roteiro completo</a>
        <a href="#/video/${id}/voz" class="${ativo === "voz" ? "ativo" : ""}">${ic("voz")} Voz e encaixe das falas</a>
        <a href="#/video/${id}/ajustes" class="${ativo === "ajustes" ? "ativo" : ""}">${ic("tesoura")} Cortes e marcadores</a>
        <a href="#/novo?base=${id}">${ic("copiar")} Nova versão</a>
        <button type="button" data-apagar-projeto="${id}">${ic("lixo")} Apagar vídeo</button>
      </div></details>
  </div>
  ${p.custos.total_usd ? `<p class="peq" style="margin:-8px 0 14px">Custo registrado neste vídeo: <b>${usd(p.custos.total_usd)}</b></p>` : ""}`;
}

document.addEventListener("click", async (e) => {
  const ap = e.target.closest("[data-apagar-projeto]");
  if (ap) {
    const v = (await api("GET", "/api/biblioteca")).videos.find((x) => x.id === ap.dataset.apagarProjeto);
    if (v) apagarVideo(v);
  }
  if (!e.target.closest(".menu-mais")) $$(".menu-mais[open]").forEach((d) => d.removeAttribute("open"));
});

/* #/video/<id>: abre no lugar certo */
async function telaAbrirVideo(id) {
  const p = await api("GET", `/api/projetos/${id}`);
  location.replace(p.tem_video_final || (p.tarefa && p.tarefa.situacao === "rodando") ? `#/video/${id}/editor` : `#/video/${id}/configurar`);
}

/* ================= ASSISTENTE DE CONFIGURAÇÃO ================= */

const PASSOS_ASSIST = [
  ["sobre", "Sobre o vídeo", "fala"],
  ["cartoes", "Abertura e encerramento", "abertura"],
  ["voz", "Voz e música", "mic"],
  ["gerar", "Revisar e gerar", "ia"],
];

async function telaConfigurar(id, params) {
  const [p, d, fins] = await Promise.all([api("GET", `/api/projetos/${id}`), carregarConfig(), carregarFinalidades()]);
  const passo = PASSOS_ASSIST.some(([k]) => k === params.get("passo")) ? params.get("passo") : "sobre";
  const idx = PASSOS_ASSIST.findIndex(([k]) => k === passo);
  conteudo().innerHTML = `${await cabProjeto(id, "configurar", p)}
    ${p.tarefa && p.tarefa.situacao === "rodando" ? `<div class="alerta info">⏳ ${esc(nomeTarefa(p.tarefa.tipo))}: ${esc(p.tarefa.mensagem)}</div>` : ""}
    <div class="assist">
      <nav class="assist-nav" aria-label="Passos da configuração">${PASSOS_ASSIST.map(([k, t], i) => `<button type="button" data-passo="${k}" class="${k === passo ? "ativo" : i < idx ? "feito" : ""}">
        <span class="num">${i < idx ? "✓" : i + 1}</span>${t}</button>`).join("")}
        <p class="peq" style="padding:10px 12px">Tudo é opcional. Pule direto para <b>Revisar e gerar</b> se quiser usar os padrões.</p></nav>
      <div><div id="assist-corpo"></div>
        <div class="rodape-assist">
          ${idx > 0 ? `<button class="btn" id="assist-ant">${ic("esquerda")} Voltar</button>` : "<span></span>"}
          ${idx < PASSOS_ASSIST.length - 1 ? `<button class="btn prim" id="assist-prox">Próximo: ${PASSOS_ASSIST[idx + 1][1]} ${ic("direita")}</button>` : ""}
        </div></div>
    </div>`;
  const corpo = $("#assist-corpo");
  const telas = { sobre: assistSobre, cartoes: assistCartoes, voz: assistVoz, gerar: assistGerar };
  const ctx = await telas[passo](corpo, p, id, d, fins);
  const ir = async (k) => {
    if (ctx && ctx.salvar) { try { await ctx.salvar(); } catch (_) { return; } }
    location.hash = `#/video/${id}/configurar?passo=${k}`;
  };
  $$("[data-passo]").forEach((b) => b.onclick = () => ir(b.dataset.passo));
  if ($("#assist-ant")) $("#assist-ant").onclick = () => ir(PASSOS_ASSIST[idx - 1][0]);
  if ($("#assist-prox")) $("#assist-prox").onclick = () => ir(PASSOS_ASSIST[idx + 1][0]);
}

/* ---- passo 1: sobre o vídeo ---- */

function assistSobre(el, p, id, d, fins) {
  const b = p.briefing || {};
  let fin = b.finalidade || "";
  const fObj = () => fins.find((f) => f.id === fin);
  el.innerHTML = `
    <div class="cartao"><h2>${ic("fala")} Sobre o vídeo</h2>
      <div class="campo"><label for="b-nome">Nome</label><input type="text" id="b-nome" value="${esc(p.video.nome)}"></div>
      <div class="campo"><label>Para quem é este vídeo?</label>
        <div class="chips" id="fins">${fins.map((f) => `<button type="button" class="chip ${f.id === fin ? "sel" : ""}" data-fin="${f.id}">${ic(ICONE_FINALIDADE[f.icone] || "info")} ${esc(f.nome)}</button>`).join("")}</div>
        <div class="ajuda" id="fin-ajuda"></div></div>
      <div class="campo"><label for="b-texto">O que o vídeo deve mostrar ou destacar? <span class="peq">(opcional)</span></label>
        <textarea id="b-texto" rows="3" placeholder="ex.: Como cadastrar um fornecedor e por que o sistema bloqueia CNPJ duplicado.">${esc(b.texto_livre)}</textarea>
        <div class="ajuda">Sem nada aqui, a IA descreve o que aparece na tela e explica as suposições que fez.</div></div>
      <div class="grade g2">
        <div class="campo"><label for="b-pontos">Precisa falar (um por linha)</label><textarea id="b-pontos" rows="3" placeholder="ex.: aprovação em duas etapas">${esc((b.pontos_obrigatorios || []).join("\n"))}</textarea></div>
        <div class="campo"><label for="b-nao">Não pode falar (um por linha)</label><textarea id="b-nao" rows="3" placeholder="ex.: nomes de clientes, valores reais">${esc((b.nao_mencionar || []).join("\n"))}</textarea></div>
      </div>
      <details><summary class="peq" style="cursor:pointer">Mais opções: público, objetivo, tom, idioma e duração</summary>
        <div class="grade g2" style="margin-top:12px">
          <div class="campo"><label for="b-publico">Público</label><input type="text" id="b-publico" value="${esc(b.publico)}"></div>
          <div class="campo"><label for="b-objetivo">Objetivo</label><input type="text" id="b-objetivo" value="${esc(b.objetivo)}"></div>
          <div class="campo"><label for="b-tom">Tom</label><input type="text" id="b-tom" value="${esc(b.tom)}" placeholder="padrão: ${esc(d.config.narracao.tom)}"></div>
          <div class="campo"><label for="b-idioma">Idioma</label><input type="text" id="b-idioma" value="${esc(b.idioma)}" placeholder="padrão: ${esc(d.config.narracao.idioma)}"></div>
          <div class="campo"><label for="b-dur">Duração desejada (s)</label><input type="number" id="b-dur" value="${b.duracao_alvo_s ?? ""}" min="0"></div>
        </div>
        <p class="peq">Ao escolher a finalidade, público, objetivo e tom vazios são preenchidos sozinhos. <a href="#/video/${id}/ajustes">Cortes e marcadores</a> também são opcionais.</p></details>
    </div>`;
  const ajuda = () => {
    const f = fObj();
    $("#fin-ajuda").innerHTML = f ? `Narração para <b>${esc(f.publico)}</b>, com objetivo de ${esc(f.objetivo)}, em tom ${esc(f.tom)}.` : "Escolha uma opção para ajustar público, objetivo e tom com um clique.";
  };
  ajuda();
  $$("[data-fin]").forEach((bt) => bt.onclick = () => {
    const anterior = fObj();
    fin = fin === bt.dataset.fin ? "" : bt.dataset.fin;
    $$("[data-fin]").forEach((x) => x.classList.toggle("sel", x.dataset.fin === fin));
    // troca os campos que vieram da finalidade anterior
    const f = fObj();
    for (const [campo, elId] of [["publico", "b-publico"], ["objetivo", "b-objetivo"], ["tom", "b-tom"]]) {
      const inp = $(`#${elId}`);
      if (!inp.value || (anterior && inp.value === anterior[campo])) inp.value = f ? f[campo] : "";
    }
    ajuda();
  });
  return {
    salvar: async () => {
      const nome = $("#b-nome").value.trim();
      if (nome && nome !== p.video.nome) await api("PATCH", `/api/biblioteca/${id}`, { nome });
      await api("PUT", `/api/projetos/${id}/briefing`, {
        finalidade: fin, texto_livre: $("#b-texto").value, publico: $("#b-publico").value, objetivo: $("#b-objetivo").value,
        tom: $("#b-tom").value, idioma: $("#b-idioma").value, pontos_obrigatorios: $("#b-pontos").value.split("\n"),
        nao_mencionar: $("#b-nao").value.split("\n"), duracao_alvo_s: $("#b-dur").value,
      });
    },
  };
}

/* ---- passo 2: abertura e encerramento ---- */

async function assistCartoes(el, p, id) {
  el.innerHTML = `<div class="cartao">
    <div class="linha" style="margin-bottom:14px"><h2 style="margin:0">${ic("abertura")} Abertura e encerramento</h2><span class="espaco"></span>
      ${segmentos("qual-cartao", [["abertura", "Abertura", "abertura"], ["encerramento", "Encerramento", "encerramento"]], ASSIST_CARTAO.qual)}</div>
    <p class="peq">Cartões antes e depois da gravação. Defina aqui texto, imagem e fala; no editor dá para mudar tudo de novo.</p>
    <div id="cx-area"></div></div>`;
  const abrir = () => editorCartao($("#cx-area"), id, ASSIST_CARTAO.qual, { roteiro: p.roteiro });
  ligarSegmentos(el, "qual-cartao", (v) => { ASSIST_CARTAO.qual = v; abrir(); });
  await abrir();
}
const ASSIST_CARTAO = { qual: "abertura" };

/* Editor de um cartão (abertura ou encerramento). Usado no assistente e no editor.
   Salva sozinho a cada alteração e atualiza a prévia. */
async function editorCartao(el, id, qual, opts = {}) {
  const cart = await api("GET", `/api/projetos/${id}/cartoes`);
  const c = cart[qual];
  const nomeQ = qual === "abertura" ? "abertura" : "encerramento";
  const textoIA = qual === "abertura" && opts.roteiro && opts.roteiro.abertura ? (opts.roteiro.abertura.texto_legenda || "") : "";
  let modo = c.fala ? "eu" : qual === "abertura" && c.fala_auto ? "ia" : "sem";
  const origemImg = c.imagem_url ? TAGS.ok("imagem deste vídeo") : c.imagem_marca ? TAGS.info("imagem da marca") : TAGS.neutro("fundo com a cor da marca");
  el.innerHTML = `<div class="cartao-edit">
    <div>
      <img class="previa ${c.ativo ? "" : "desligado"}" id="cx-prev" src="/api/projetos/${id}/cartoes/${qual}.png?v=${Date.now()}" alt="Prévia do cartão de ${nomeQ}">
      <div class="linha" style="margin-top:10px"><span class="peq">Imagem:</span> ${origemImg}<span class="espaco"></span>
        <label class="btn peq" for="cx-img" style="margin:0">${ic("imagem")} ${c.imagem_url ? "Trocar imagem" : "Enviar imagem"}</label>
        <input type="file" id="cx-img" accept="image/png,image/jpeg,image/webp" hidden>
        ${c.imagem_url ? `<button class="btn peq perigo" id="cx-rm-img">${ic("x")} Remover</button>` : ""}</div>
      <p class="peq" style="margin-top:6px">PNG, JPG ou WEBP em 16:9 (1920×1080 de preferência). A imagem preenche a tela inteira.</p>
      <div class="peq" id="cx-status" aria-live="polite"></div>
    </div>
    <div>
      ${chave("cx-ativo", `Usar ${nomeQ}`, c.ativo)}
      <div id="cx-campos" style="${c.ativo ? "" : "opacity:.5"}">
        <div class="campo"><label for="cx-tit">Título</label><input type="text" id="cx-tit" value="${esc(c.titulo)}" maxlength="120"></div>
        <div class="campo"><label for="cx-sub">Subtítulo</label><input type="text" id="cx-sub" value="${esc(c.subtitulo)}" maxlength="160" placeholder="opcional"></div>
        ${chave("cx-sobre", "Escrever título e subtítulo sobre a imagem", c.texto_sobre_imagem !== false)}
        <div class="campo"><label>Fala ${qual === "abertura" ? "na abertura" : "no encerramento"}</label>
          ${segmentos("cx-modo", [["eu", "Eu escrevo", "editar"], ...(qual === "abertura" ? [["ia", "IA escreve", "ia"]] : []), ["sem", "Sem fala", "x"]], modo)}
          <div id="cx-fala" style="margin-top:10px"></div></div>
        <div class="campo"><label for="cx-dur">Duração mínima: <b id="cx-dur-v">${(+c.duracao_s).toFixed(1)} s</b></label>
          <input type="range" id="cx-dur" min="1" max="15" step="0.5" value="${c.duracao_s}" style="width:100%">
          <div class="ajuda">Se a fala for mais longa, o cartão estica sozinho para caber.</div></div>
        ${qual === "encerramento" ? chave("cx-cred", "Mostrar o crédito da música quando a licença exigir", c.credito_musica !== false) : ""}
      </div>
      ${opts.aoAplicar ? `<div class="linha fim" style="margin-top:6px"><button class="btn prim" id="cx-aplicar">${ic("refazer")} Aplicar no vídeo</button></div>` : ""}
    </div></div>`;

  const desenharFala = () => {
    const alvo = $("#cx-fala", el);
    if (modo === "eu") {
      alvo.innerHTML = `<textarea id="cx-texto" rows="3" maxlength="400" placeholder="${qual === "abertura" ? "ex.: Neste vídeo, você vai ver como cadastrar um fornecedor em menos de um minuto." : "ex.: Pronto! Dúvidas? Fale com o time de suporte."}">${esc(c.fala || "")}</textarea>
        <div class="ajuda">Lida exatamente como está escrito e mostrada como legenda.</div>`;
      $("#cx-texto", el).oninput = () => salvarAdiado();
    } else if (modo === "ia") {
      alvo.innerHTML = textoIA
        ? `<div class="alerta info" style="margin:0 0 8px">${ic("ia")} <span>“${esc(textoIA)}”</span></div><button class="btn peq" id="cx-editar-ia">${ic("editar")} Editar este texto</button>`
        : `<p class="peq">A IA escreve uma frase de abertura junto com o roteiro, apresentando o que o vídeo mostra.</p>`;
      const bt = $("#cx-editar-ia", el);
      if (bt) bt.onclick = () => { c.fala = textoIA; modo = "eu"; $$(`[data-seg="cx-modo"] button`, el).forEach((x) => x.classList.toggle("sel", x.dataset.v === "eu")); desenharFala(); salvar(); };
    } else {
      alvo.innerHTML = `<p class="peq">Só a imagem${qual === "abertura" ? ", e a narração começa junto com a gravação" : ""}.</p>`;
    }
  };
  desenharFala();

  const status = (t) => { const s = $("#cx-status", el); if (s) s.innerHTML = t; };
  const coletar = () => {
    const d = {
      ativo: $("#cx-ativo", el).checked, titulo: $("#cx-tit", el).value, subtitulo: $("#cx-sub", el).value,
      texto_sobre_imagem: $("#cx-sobre", el).checked, duracao_s: +$("#cx-dur", el).value,
      fala: modo === "eu" ? ($("#cx-texto", el)?.value || "") : "", fala_auto: modo === "ia",
    };
    if (qual === "encerramento") d.credito_musica = $("#cx-cred", el).checked;
    return d;
  };
  const salvar = async () => {
    status("⏳ salvando…");
    const d = coletar();
    c.fala = d.fala;
    await api("PUT", `/api/projetos/${id}/cartoes`, { [qual]: d });
    $("#cx-prev", el).src = `/api/projetos/${id}/cartoes/${qual}.png?v=${Date.now()}`;
    $("#cx-prev", el).classList.toggle("desligado", !d.ativo);
    $("#cx-campos", el).style.opacity = d.ativo ? "" : ".5";
    status(`${TAGS.ok("salvo")}${opts.aoAplicar ? " Clique em Aplicar no vídeo para ver no corte final." : ""}`);
  };
  const salvarAdiado = adiar(salvar, 700);
  ["cx-tit", "cx-sub"].forEach((k) => $(`#${k}`, el).oninput = salvarAdiado);
  ["cx-ativo", "cx-sobre", "cx-cred"].forEach((k) => { const x = $(`#${k}`, el); if (x) x.onchange = salvar; });
  $("#cx-dur", el).oninput = (e) => { $("#cx-dur-v", el).textContent = `${(+e.target.value).toFixed(1)} s`; salvarAdiado(); };
  ligarSegmentos(el, "cx-modo", (v) => { modo = v; desenharFala(); salvar(); });
  $("#cx-img", el).onchange = async (e) => {
    const f = e.target.files[0];
    if (!f) return;
    status("⏳ enviando imagem…");
    await api("POST", `/api/projetos/${id}/cartoes/${qual}/imagem?nome=${encodeURIComponent(f.name)}`, f);
    editorCartao(el, id, qual, opts);
  };
  if ($("#cx-rm-img", el)) $("#cx-rm-img", el).onclick = async () => { await api("PUT", `/api/projetos/${id}/cartoes`, { [qual]: { imagem: "" } }); editorCartao(el, id, qual, opts); };
  if ($("#cx-aplicar", el)) $("#cx-aplicar", el).onclick = async () => { await salvar(); opts.aoAplicar(); };
}

/* ---- passo 3: voz e música ---- */

async function assistVoz(el, p, id, d) {
  const musicaAtual = d.config.musica.arquivo;
  el.innerHTML = `
    <div class="cartao"><h2>${ic("mic")} Voz da narração</h2>
      <p class="peq">Vale para todos os vídeos. Troque quando quiser em Configurações.</p>
      <div id="voz-campos"></div></div>
    <div class="cartao"><h2>${ic("musica")} Música de fundo</h2>
      ${segmentos("mus-modo", [["gerar", "Gerar com IA", "ia"], ["faixas", "Minhas faixas", "musica"], ["sem", "Sem música", "x"]], musicaAtual ? "faixas" : "gerar")}
      <div id="mus-corpo" style="margin-top:14px"></div></div>`;
  await camposVoz($("#voz-campos"), { compacto: true });
  const corpo = $("#mus-corpo");
  const desenhar = async (modo) => {
    if (modo === "sem") {
      await api("PUT", "/api/config", { musica: { arquivo: "" } });
      corpo.innerHTML = `<p>${TAGS.ok("sem música")} O vídeo fica só com a narração.</p>`;
      return;
    }
    if (modo === "gerar") {
      const info = await api("GET", `/api/musicas/gerar/info?video_id=${id}`);
      const plano = info.plano || {};
      corpo.innerHTML = `<p class="peq">O Eleven Music compõe uma faixa instrumental no tamanho do vídeo, feita para ficar sob a narração. É a opção mais segura para uso comercial.</p>
        ${plano.erro ? `<div class="alerta aviso">⚠ ${esc(plano.erro)} · <a href="#/config">abrir Configurações</a></div>`
          : `<div class="alerta ${plano.individual ? "aviso" : "info"}">${plano.individual ? "⚠" : "●"} <span><b>Plano ${esc(plano.nome || "?")}:</b> ${esc(plano.aviso || "")}</span></div>`}
        <div class="campo"><label>Estilo</label><div class="chips">${info.estilos.map((e, i) => `<button type="button" class="chip ${i === 0 ? "sel" : ""}" data-estilo="${e.id}">${esc(e.nome)}</button>`).join("")}</div></div>
        <div class="campo"><label for="mus-desc">Detalhe (opcional)</label><input type="text" id="mus-desc" placeholder="ex.: mais animada no final, sem bateria"></div>
        <div class="linha"><button class="btn prim" id="mus-gerar" ${plano.erro ? "disabled" : ""}>${ic("ia")} Gerar e usar</button><span class="peq">≈ ${fmtDur(info.duracao_s)} · custo estimado ${usd(info.custo_usd)}</span></div>`;
      let estilo = info.estilos[0] ? info.estilos[0].id : "corporativo";
      $$("[data-estilo]", corpo).forEach((b) => b.onclick = () => { estilo = b.dataset.estilo; $$("[data-estilo]", corpo).forEach((x) => x.classList.toggle("sel", x === b)); });
      $("#mus-gerar").onclick = async () => acompanhar(await api("POST", `/api/projetos/${id}/musica/gerar`, { estilo, descricao: $("#mus-desc").value }),
        (t) => { if (t.situacao === "ok") { const b = $(`[data-seg="mus-modo"] [data-v="faixas"]`); if (b) b.click(); } });
      return;
    }
    const cfg = (await carregarConfig()).config;
    const { musicas } = await api("GET", "/api/musicas");
    corpo.innerHTML = musicas.length ? `<div class="lista-musicas">${musicas.map((m) => itemMusica(m, cfg.musica.arquivo)).join("")}</div>
      <p class="peq" style="margin-top:8px">Mais opções (enviar faixa licenciada, volume, catálogo aberto) ficam no editor, na ferramenta Música.</p>`
      : `<p class="peq">Nenhuma faixa ainda. Gere uma com IA ou envie no editor, na ferramenta Música.</p>`;
    corpo.onclick = async (e) => {
      if (tocarAmostra(e, corpo)) return;
      const u = e.target.closest("[data-usar]");
      if (u) { await api("PUT", "/api/config", { musica: { arquivo: u.dataset.usar } }); toast("Música escolhida"); desenhar("faixas"); }
    };
  };
  ligarSegmentos(el, "mus-modo", desenhar);
  desenhar(musicaAtual ? "faixas" : "gerar");
}

const AUDIO_PREVIA = new Audio();
AUDIO_PREVIA.preload = "none";

function tocarAmostra(e, raiz) {
  const ouvir = e.target.closest("[data-ouvir]");
  if (!ouvir) return false;
  const tocando = AUDIO_PREVIA.dataset.src === ouvir.dataset.ouvir && !AUDIO_PREVIA.paused;
  $$("[data-ouvir]", raiz).forEach((b) => { b.innerHTML = ic("play"); b.setAttribute("aria-label", "Ouvir"); });
  if (tocando) { AUDIO_PREVIA.pause(); return true; }
  AUDIO_PREVIA.src = ouvir.dataset.ouvir;
  AUDIO_PREVIA.dataset.src = ouvir.dataset.ouvir;
  AUDIO_PREVIA.play().then(() => { ouvir.innerHTML = ic("pausa"); ouvir.setAttribute("aria-label", "Pausar"); }).catch(() => toast("Não foi possível tocar a amostra", "erro"));
  return true;
}

function tagOrigemMusica(m) {
  if (m.origem === "eleven_music") return TAGS.ok("gerada · Eleven Music");
  if (m.verificada) return TAGS.ok("licença confirmada");
  if (m.origem === "catalogo_aberto") return TAGS.aviso("catálogo aberto · licença não confirmada");
  return TAGS.aviso("licença não confirmada");
}

function itemMusica(m, emUso, extras = "") {
  return `<div class="musica-item">
    <button class="play" data-ouvir="/api/musicas/${encodeURIComponent(m.arquivo)}" aria-label="Ouvir">${ic("play")}</button>
    <div style="min-width:0"><div class="t">${esc(m.titulo || m.arquivo)}</div>
      <div class="peq">${esc(m.autor || "")} · ${fmtDur(m.duracao_s)} ${tagOrigemMusica(m)}</div></div>
    <div class="linha">${extras}${m.arquivo === emUso ? TAGS.ok("em uso") : `<button class="btn peq" data-usar="${esc(m.arquivo)}">Usar</button>`}</div></div>`;
}

/* ---- passo 4: revisar e gerar ---- */

async function assistGerar(el, p, id, d) {
  const b = p.briefing || {};
  const fins = await carregarFinalidades();
  const fin = fins.find((f) => f.id === b.finalidade);
  const c = p.cartoes;
  const descCart = (k) => {
    const x = c[k];
    if (!x.ativo) return TAGS.neutro("desligado");
    const fala = x.fala ? "fala escrita por você" : k === "abertura" && x.fala_auto ? "fala escrita pela IA" : "sem fala";
    return `${TAGS.ok("ligado")} ${esc(x.titulo || "(sem título)")} · ${fala}${x.imagem_url ? " · imagem própria" : ""}`;
  };
  const pronto = p.video.situacao_arquivo === "pronto";
  const mus = d.config.musica.arquivo;
  el.innerHTML = `
    <div class="cartao"><h2>${ic("ok")} Resumo</h2>
      <dl class="resumo-lista">
        <dt>Finalidade</dt><dd>${fin ? esc(fin.nome) : TAGS.neutro("padrão das configurações")} <a class="peq" href="#/video/${id}/configurar?passo=sobre">alterar</a></dd>
        <dt>O que mostrar</dt><dd>${b.texto_livre ? esc(b.texto_livre) : `<span class="peq">a IA decide pelo que aparece na tela</span>`}</dd>
        <dt>Abertura</dt><dd>${descCart("abertura")} <a class="peq" href="#/video/${id}/configurar?passo=cartoes">alterar</a></dd>
        <dt>Encerramento</dt><dd>${descCart("encerramento")}</dd>
        <dt>Voz</dt><dd>${esc(descVoz(d))} ${d.ritmo.calibrado ? TAGS.ok("ritmo calibrado") : TAGS.info("calibra sozinha antes do roteiro")}</dd>
        <dt>Música</dt><dd>${mus ? esc(mus) : TAGS.neutro("sem música")} <a class="peq" href="#/video/${id}/configurar?passo=voz">alterar</a></dd>
      </dl></div>
    <div class="cartao"><h2>${ic("dinheiro")} Estimativa de custo</h2>${tabelaEstimativa(p.estimativa)}</div>
    <div class="cartao destaque"><h2>${ic("ia")} Gerar</h2>
      ${pronto ? "" : `<div class="alerta aviso">⏳ O vídeo ainda está sendo comprimido. O botão libera sozinho quando terminar.</div>`}
      <p class="peq">A aplicação corta o começo e o fim parados, entende a tela, escreve o roteiro, gera a voz resolvendo o encaixe de cada fala, monta e confere. Depois você revisa tudo no editor.</p>
      ${p.roteiro ? `<div class="alerta aviso">⚠ Já existe um roteiro. Gerar de novo substitui o atual e as edições feitas nele.</div>` : ""}
      <div class="linha"><button class="btn prim grande" id="completo" ${pronto ? "" : "disabled"}>${ic("ia")} Gerar vídeo completo</button>
        <button class="btn" id="so-roteiro" ${pronto ? "" : "disabled"}>Só o roteiro, para revisar antes</button>
        ${p.tem_video_final ? `<a class="btn" href="#/video/${id}/editor">Ir para o editor sem gerar ${ic("direita")}</a>` : ""}</div>
    </div>`;
  if (!pronto) setTimeout(() => { if (location.hash.startsWith(`#/video/${id}/configurar`)) rotear(); }, 4000);
  $("#completo").onclick = () => gerarRoteiro(id, {}, "completo");
  $("#so-roteiro").onclick = () => gerarRoteiro(id, {}, "roteiro");
}

function tabelaEstimativa(e) {
  return `<table><thead><tr><th>Item</th><th>Modelo</th><th class="num">Estimativa</th></tr></thead><tbody>
    ${e.itens.map((i) => `<tr><td>${esc(i.item)}</td><td class="mono">${esc(i.modelo)}${i.caracteres ? ` · ≈ ${i.caracteres} car.` : ""}</td><td class="num">${usd(i.usd)}</td></tr>`).join("")}
    <tr><td><b>Total</b></td><td class="peq">${fmtDur(e.duracao_s)} de vídeo · ${usd(e.por_minuto_usd)} por minuto</td><td class="num"><b>${usd(e.total_usd)}</b></td></tr></tbody></table>
    ${e.acima_do_limite ? `<div class="alerta aviso" style="margin-top:10px">⚠ Passa do limite por vídeo (${usd(e.limite_usd)}). Será pedida confirmação.</div>` : `<p class="peq" style="margin-top:8px">${TAGS.ok("dentro do limite")} limite por vídeo: ${usd(e.limite_usd)}</p>`}`;
}

async function gerarRoteiro(id, extras, modo = "roteiro") {
  const corpo = { ...extras };
  const url = modo === "completo" ? `/api/projetos/${id}/completo` : `/api/projetos/${id}/roteiro/gerar`;
  const destino = modo === "completo" ? "editor" : "roteiro";
  for (let i = 0; i < 3; i++) {
    try {
      const t = await api("POST", url, corpo, { silencioso: true });
      acompanhar(t, () => { if (location.hash.startsWith(`#/video/${id}`)) rotear(); });
      location.hash = `#/video/${id}/${destino}`;
      return;
    } catch (e) {
      if (e.status === 428) {
        if (!(await avisoPrivacidade())) return;
      } else if (e.status === 402) {
        if (!(await confirmar("Custo acima do limite", esc(e.message), "Gerar mesmo assim"))) return;
        corpo.confirmado = true;
      } else { toast(e.message, "erro"); return; }
    }
  }
}

async function avisoPrivacidade() {
  const r = await modal({
    titulo: "Aviso de privacidade",
    html: `<p>Para entender o vídeo e escrever o roteiro, <b>quadros da gravação são enviados para a API da Anthropic</b> (Claude). O texto do roteiro é enviado para a ElevenLabs quando ela é a voz escolhida.</p>
      <p>Use dados de demonstração sempre que possível. Gravações de sistemas reais podem mostrar nomes, documentos e valores de clientes (LGPD).</p>
      <p class="peq">Você pode rever este aviso em Configurações, Privacidade e custos.</p>`,
    botoes: [{ texto: "Cancelar", valor: false }, { texto: "Entendi, continuar", valor: true, classe: "prim" }],
  });
  if (r.valor !== true) return false;
  await api("PUT", "/api/config", { privacidade: { aviso_aceito: true } });
  return true;
}

/* ================= ROTEIRO (avançado) ================= */

function contadorHtml(n, orc) {
  if (n > orc) return `<span class="contador" style="color:var(--erro)">⚠ ${n}/${orc} car. · passa ${n - orc}</span>`;
  if (n > orc * 0.95) return `<span class="contador" style="color:var(--aviso)">◐ ${n}/${orc} car. · no limite</span>`;
  return `<span class="contador" style="color:var(--ok)">✓ ${n}/${orc} car. · cabe</span>`;
}

async function telaRoteiro(id) {
  const [p] = await Promise.all([api("GET", `/api/projetos/${id}`), carregarConfig()]);
  const cab = await cabProjeto(id, "roteiro", p);
  const r = p.roteiro;
  if (!r) {
    conteudo().innerHTML = `${cab}<div class="cartao vazio"><div class="ico-grande">${ic("roteiro", "g")}</div><p>O roteiro ainda não foi gerado.</p><a class="btn prim" href="#/video/${id}/configurar?passo=gerar">Configurar e gerar</a></div>`;
    if (p.tarefa && p.tarefa.situacao === "rodando") acompanhar(p.tarefa, () => rotear());
    return;
  }
  const cenas = Object.fromEntries((p.mapa?.cenas || []).map((c) => [c.id, c]));
  const porJanela = Object.fromEntries(r.falas.map((f) => [f.janela, f]));
  const probs = r.problemas || [];
  conteudo().innerHTML = `${cab}
    <div class="grade g2">
      <div class="cartao"><h2>Resumo</h2>
        <p>${r.falas.length} falas em ${r.janelas.length} trechos · voz ${esc(r.voz.nome || r.voz.motor)} a <b>${r.voz.ritmo_car_s} car/s</b> ${r.voz.calibrado ? TAGS.ok("calibrada") : TAGS.aviso("ritmo padrão")}</p>
        ${p.mapa?.resumo ? `<p class="peq">Vídeo: ${esc(p.mapa.resumo)}</p>` : ""}
        <div class="campo"><label for="premissas">Suposições feitas pela IA (uma por linha)</label><textarea id="premissas" rows="2">${esc((r.premissas || []).join("\n"))}</textarea></div>
        <p class="peq">A fala da abertura e do encerramento fica em <a href="#/video/${id}/configurar?passo=cartoes">Abertura e encerramento</a>.</p>
      </div>
      <div class="cartao"><h2>Avisos</h2>
        ${probs.length ? `<ul style="margin:0;padding-left:0;list-style:none">${probs.map((x) => `<li style="margin-bottom:6px">${x.tipo === "estouro" || x.tipo === "nao_mencionar" ? TAGS.erro(x.tipo.replace("_", " ")) : TAGS.aviso(x.tipo.replace("_", " "))} ${x.fala ? `<b>${esc(x.fala)}</b>: ` : ""}${esc(x.detalhe)}</li>`).join("")}</ul>`
          : `<p>${TAGS.ok("nenhum aviso")} Todas as falas cabem e respeitam o briefing.</p>`}
      </div>
    </div>
    <div class="cartao"><h2>${ic("fala")} Falas por trecho</h2>
      <p class="peq">O tamanho é contado no <b>texto falado</b> (o que a voz lê). A legenda usa a grafia normal. Se passar um pouco, a aplicação resolve sozinha.</p>
      <div id="falas">${r.janelas.map((j) => linhaFala(j, porJanela[j.id], cenas, id)).join("")}</div>
    </div>
    <div class="cartao"><h2>${ic("refazer")} Regerar com instruções</h2>
      <div class="campo"><textarea id="instr" rows="2" placeholder="ex.: tom mais informal; destacar a aprovação em duas etapas; encurtar as falas do começo"></textarea></div>
      ${chave("reanalisar", "Reanalisar o vídeo também (refaz o mapa de cenas e custa mais)", false)}
      <button class="btn" id="regerar">${ic("refazer")} Regerar roteiro</button></div>
    <div class="linha fim" style="position:sticky;bottom:0;background:var(--bg);padding:12px 0;border-top:1px solid var(--borda)">
      <span class="peq" id="resumo-cont"></span><span class="espaco"></span>
      <button class="btn" id="salvar-r">Salvar</button>
      <button class="btn prim" id="aplicar-r">${ic("refazer")} Salvar e gerar o vídeo</button></div>`;
  const el = conteudo();
  const atualizar = () => {
    let estouros = 0;
    $$(".fala[data-j]").forEach((row) => {
      const ta = $("textarea[data-c=texto_falado]", row);
      if (!ta) return;
      const orc = +row.dataset.orc;
      const n = ta.value.trim().length;
      if (n > orc) estouros++;
      $(".cont", row).innerHTML = contadorHtml(n, orc);
    });
    $("#resumo-cont").innerHTML = estouros ? TAGS.aviso(`${estouros} fala(s) longas: serão ajustadas sozinhas`) : TAGS.ok("todas as falas cabem");
  };
  el.oninput = (e) => { if (e.target.matches("textarea")) atualizar(); };
  el.onclick = (e) => {
    const add = e.target.closest("[data-add]");
    if (add) {
      const row = add.closest(".fala");
      $(".textos", row).innerHTML = camposFala({ texto_legenda: "", texto_falado: "" });
      row.classList.remove("vazia");
      atualizar();
    }
    const rm = e.target.closest("[data-rmfala]");
    if (rm) {
      const row = rm.closest(".fala");
      $(".textos", row).innerHTML = `<button class="btn peq" data-add>${ic("mais")} Adicionar fala neste trecho</button><span class="cont"></span>`;
      row.classList.add("vazia");
      atualizar();
    }
  };
  atualizar();
  const coletar = () => ({
    premissas: $("#premissas").value.split("\n"),
    abertura: { texto_legenda: r.abertura?.texto_legenda || "", texto_falado: r.abertura?.texto_falado || "" },
    falas: $$(".fala[data-j]").filter((row) => $("textarea[data-c=texto_falado]", row)).map((row) => ({
      janela: row.dataset.j,
      texto_legenda: $("textarea[data-c=texto_legenda]", row).value,
      texto_falado: $("textarea[data-c=texto_falado]", row).value,
      numeros_citados: JSON.parse(row.dataset.nums || "{}"),
    })),
  });
  $("#salvar-r").onclick = async () => { await api("PUT", `/api/projetos/${id}/roteiro`, coletar()); toast("Roteiro salvo"); };
  $("#aplicar-r").onclick = async () => {
    await api("PUT", `/api/projetos/${id}/roteiro`, coletar());
    acompanhar(await api("POST", `/api/projetos/${id}/refazer`), () => { if (location.hash.startsWith(`#/video/${id}`)) rotear(); });
    location.hash = `#/video/${id}/editor`;
  };
  $("#regerar").onclick = async () => {
    if (!(await confirmar("Regerar roteiro", "O roteiro atual, inclusive as suas edições, será substituído.", "Regerar"))) return;
    await gerarRoteiro(id, { instrucoes: $("#instr").value, reanalisar_video: $("#reanalisar").checked });
  };
}

function camposFala(f) {
  return `<div class="grade g2">
      <div class="campo"><label>Legenda</label><textarea data-c="texto_legenda" rows="2">${esc(f.texto_legenda)}</textarea></div>
      <div class="campo"><label>Texto falado</label><textarea data-c="texto_falado" rows="2">${esc(f.texto_falado)}</textarea></div></div>
    <div class="linha"><span class="cont"></span><span class="espaco"></span><button class="btn peq perigo" data-rmfala>${ic("x")} Remover fala</button></div>`;
}

function linhaFala(j, f, cenas, id) {
  const meio = (j.inicio_s + j.fim_s) / 2;
  const cs = j.cenas.map((c) => cenas[c]).filter(Boolean);
  const desc = cs.map((c) => `${esc(c.tela)}${c.tipo ? ` · ${esc(c.tipo)}` : ""}${c.importancia === "alta" ? " · ★ importante" : ""}`).join("<br>");
  const acao = cs.map((c) => esc(c.acao)).join(" ");
  const nums = cs.flatMap((c) => Object.entries(c.numeros_visiveis || {}).map(([k, v]) => `${esc(k)}: ${esc(v)}`));
  return `<div class="fala ${f ? "" : "vazia"}" data-j="${j.id}" data-orc="${j.orcamento_caracteres}" data-nums='${esc(JSON.stringify(f?.numeros_citados || {}))}'>
    <div class="quadro"><img loading="lazy" src="/api/biblioteca/${id}/quadro?t=${meio.toFixed(2)}&largura=360" alt="Quadro em ${fmtT(meio)}">
      <div class="tempo">${fmtT(j.inicio_s)} → ${fmtT(j.fim_s)}</div>
      <div class="cena">${(j.fim_s - j.inicio_s).toFixed(1)} s · até ${j.orcamento_caracteres} car.</div>
      <div class="cena" style="margin-top:4px">${desc}</div></div>
    <div><div class="peq" style="margin-bottom:6px">${acao}${nums.length ? `<br><b>Números na tela:</b> ${nums.join(" · ")}` : ""}</div>
      <div class="textos">${f ? camposFala(f) : `<button class="btn peq" data-add>${ic("mais")} Adicionar fala neste trecho</button><span class="cont"></span>`}</div></div></div>`;
}

/* ================= VOZ E ENCAIXE (avançado) ================= */

async function telaVoz(id) {
  const [p] = await Promise.all([api("GET", `/api/projetos/${id}`), carregarConfig()]);
  const cab = await cabProjeto(id, "voz", p);
  const ritmo = ESTADO.cfg.ritmo;
  const enc = p.encaixe;
  const v = Date.now();
  conteudo().innerHTML = `${cab}
    <div class="alerta info">${ic("info")} <span>O encaixe de cada fala é resolvido pela aplicação: primeiro no ritmo natural, usando o silêncio até a próxima fala; depois com ajuste leve de velocidade; se ainda não couber, a IA encurta o texto e gera de novo.</span></div>
    <div class="grade g2">
      <div class="cartao"><h2>${ic("mic")} Voz</h2>
        <p>${esc(descVoz())} · <a href="#/config">trocar em Configurações</a></p>
        <p>${ritmo.calibrado ? `${TAGS.ok("calibrada")} ${ritmo.car_s.toFixed(1)} car/s` : `${TAGS.aviso("não calibrada")} usando ${ritmo.car_s.toFixed(1)} car/s padrão`}</p>
        <button class="btn peq" id="calibrar">${ic("voz")} Calibrar de novo</button></div>
      <div class="cartao"><h2>${ic("olho")} Prévia de 3 falas</h2>
        ${p.previa ? p.previa.map((r) => `<div style="margin-bottom:8px"><div class="peq">Fala ${r.id} · ${r.duracao_s.toFixed(1)} s de ${r.janela_s.toFixed(1)} s · ${r.velocidade.toFixed(2)}× ${r.situacao === "ok" ? TAGS.ok("cabe") : TAGS.erro("não cabe")}</div>
          <audio controls preload="none" src="/api/projetos/${id}/arquivo/audio/${r.arquivo}?v=${v}"></audio></div>`).join("") : `<p class="peq">Ouça antes de gastar crédito com todas as falas.</p>`}
        <button class="btn" id="previa" ${p.roteiro ? "" : "disabled"}>${ic("play")} ${p.previa ? "Gerar prévia de novo" : "Gerar prévia"}</button></div>
    </div>
    <div class="cartao"><h2>${ic("voz")} Todas as falas</h2>
      ${enc ? `<div class="linha" style="margin-bottom:10px">
          ${enc.resumo.estouros ? TAGS.erro(`${enc.resumo.estouros} não couberam`) : TAGS.ok("todas couberam")}
          ${TAGS.info(`${enc.resumo.no_ritmo_natural} de ${enc.resumo.falas} no ritmo natural`)}
          ${enc.resumo.encurtadas_pela_ia ? TAGS.info(`${enc.resumo.encurtadas_pela_ia} encurtadas pela IA`) : ""}
          <span class="peq">${enc.resumo.geradas_agora} geradas agora · ${enc.resumo.do_cache} reaproveitadas</span></div>
        <table><thead><tr><th>Fala</th><th class="num">Início</th><th class="num">Espaço</th><th class="num">Duração</th><th class="num">Veloc.</th><th>Situação</th><th>Texto e áudio</th></tr></thead><tbody>
        ${enc.falas.map((r) => `<tr><td>${esc(r.id)}</td><td class="num">${r.id === "abertura" || r.id === "encerramento" ? esc(r.id) : fmtT(r.inicio_s)}</td><td class="num">${r.janela_s.toFixed(1)} s</td>
          <td class="num">${r.duracao_s.toFixed(1)} s</td><td class="num">${r.velocidade.toFixed(2)}×</td>
          <td>${r.situacao !== "ok" ? TAGS.erro("não cabe") : r.velocidade > 1.001 ? TAGS.aviso(`acelerada ${Math.round((r.velocidade - 1) * 100)}%`) : (r.emprestou_s || 0) > 0.05 ? TAGS.ok(`ok · +${r.emprestou_s.toFixed(1)} s de silêncio`) : TAGS.ok("ok")}</td>
          <td style="min-width:280px"><div class="peq">${esc(r.texto)}</div><audio controls preload="none" src="/api/projetos/${id}/arquivo/audio/${r.arquivo}?v=${v}"></audio></td></tr>`).join("")}</tbody></table>`
        : `<p class="peq">As falas aparecem aqui depois da geração.</p>`}
      <div class="linha" style="margin-top:12px"><button class="btn prim" id="gerar-voz" ${p.roteiro ? "" : "disabled"}>${ic("refazer")} ${enc ? "Gerar de novo e montar (só o que mudou)" : "Gerar falas e montar"}</button></div>
    </div>`;
  const recarregar = () => { if (location.hash === `#/video/${id}/voz`) rotear(); };
  $("#calibrar").onclick = async () => acompanhar(await api("POST", "/api/voz/calibrar", { video_id: id }), recarregar);
  $("#previa").onclick = async () => acompanhar(await api("POST", `/api/projetos/${id}/voz/previa`), recarregar);
  $("#gerar-voz").onclick = async () => acompanhar(await api("POST", `/api/projetos/${id}/refazer`), recarregar);
}
