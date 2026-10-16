"use strict";
/* Editor em trilhas (player, linha do tempo e ferramentas) e exportação */

const EDITOR = { pps: 12, painel: "fala", sel: null, raf: 0, id: null };

function mdParaHtml(md) {
  const linhas = md.split("\n");
  let html = "", tabela = [];
  const inline = (s) => esc(s).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>");
  const fechar = () => {
    if (!tabela.length) return;
    const [cab, , ...corpo] = tabela;
    const cel = (l) => l.trim().replace(/^\||\|$/g, "").split("|").map((c) => c.trim());
    html += `<table><thead><tr>${cel(cab).map((c) => `<th>${inline(c)}</th>`).join("")}</tr></thead><tbody>${corpo.map((l) => `<tr>${cel(l).map((c) => `<td>${inline(c)}</td>`).join("")}</tr>`).join("")}</tbody></table>`;
    tabela = [];
  };
  for (const l of linhas) {
    if (l.trim().startsWith("|")) { tabela.push(l); continue; }
    fechar();
    if (l.startsWith("# ")) html += `<h2>${inline(l.slice(2))}</h2>`;
    else if (l.trim()) html += `<p>${inline(l)}</p>`;
  }
  fechar();
  return html;
}

const FERRAMENTAS = [
  ["fala", "fala", "Fala"], ["abertura", "abertura", "Abertura"], ["encerramento", "encerramento", "Encerramento"],
  ["capa", "imagem", "Capa"], ["musica", "musica", "Música"], ["qa", "lupa", "Qualidade"], ["exportar", "baixar", "Exportar"],
];

async function telaEditor(id, params) {
  cancelAnimationFrame(EDITOR.raf);
  if (EDITOR.id !== id) { EDITOR.id = id; EDITOR.sel = null; EDITOR.painel = "fala"; EDITOR.ajustado = false; }
  if (params && params.get("painel")) EDITOR.painel = params.get("painel");
  const [p, lt] = await Promise.all([api("GET", `/api/projetos/${id}`), api("GET", `/api/projetos/${id}/linha-do-tempo`)]);
  await carregarConfig();
  const cab = await cabProjeto(id, "editor", p);
  const rodando = p.tarefa && p.tarefa.situacao === "rodando";
  if (rodando) acompanhar(p.tarefa, () => { if (location.hash.startsWith(`#/video/${id}/editor`)) rotear(); });
  if (!lt.pronto || (!p.tem_video_final && !p.encaixe)) {
    conteudo().innerHTML = `${cab}<div class="cartao vazio">
      <div class="ico-grande">${ic(rodando ? "relogio" : "ia", "g")}</div>
      ${rodando ? `<h2 style="justify-content:center">Gerando o vídeo</h2><p>${esc(nomeTarefa(p.tarefa.tipo))}: ${esc(p.tarefa.mensagem)}</p>
        <div class="barra ${p.tarefa.progresso < 0.02 ? "indet" : ""}" style="max-width:420px;margin:12px auto"><div style="width:${Math.round(p.tarefa.progresso * 100)}%"></div></div>
        <p class="peq">Pode sair desta tela. O editor abre sozinho quando terminar.</p>`
        : `<p>O vídeo ainda não foi gerado.</p><a class="btn prim" href="#/video/${id}/configurar?passo=gerar">${ic("ia")} Configurar e gerar</a>`}</div>`;
    if (rodando) setTimeout(() => { if (location.hash.startsWith(`#/video/${id}/editor`) && !$("#ed-video")) rotear(); }, 5000);
    return;
  }
  const v = Date.now();
  const total = lt.lt.total_s;
  conteudo().innerHTML = `${cab}
    ${rodando ? `<div class="alerta info">⏳ ${esc(nomeTarefa(p.tarefa.tipo))}: ${esc(p.tarefa.mensagem)}. O vídeo abaixo é a versão anterior.</div>` : ""}
    <div class="palco">${p.tem_video_final
      ? `<video id="ed-video" src="/api/projetos/${id}/arquivo/video_final.mp4?v=${v}" preload="metadata" playsinline></video>`
      : `<div class="vazio-palco">O vídeo final ainda não foi montado.<br><br><button class="btn prim" id="montar0">${ic("play")} Montar vídeo</button></div>`}</div>
    <div class="transporte">
      <span class="tempo" id="ed-tempo">0:00 / ${fmtDur(total)}</span>
      <span class="espaco"></span>
      <button class="ctrl" id="ed-ant" title="Fala anterior" aria-label="Fala anterior">${ic("ant")}</button>
      <button class="ctrl play" id="ed-play" title="Reproduzir ou pausar" aria-label="Reproduzir ou pausar">${ic("play")}</button>
      <button class="ctrl" id="ed-prox" title="Próxima fala" aria-label="Próxima fala">${ic("prox")}</button>
      <span class="espaco"></span>
      <label class="peq" style="margin:0;display:flex;align-items:center;gap:6px">${ic("lupa")} zoom <input type="range" id="ed-zoom" min="4" max="60" value="${EDITOR.pps}"></label>
      <button class="btn peq" id="ed-montar" title="Monta o vídeo de novo com as configurações atuais">${ic("refazer")} Montar de novo</button>
    </div>
    <div class="trilhas">
      <div class="rotulos">
        <div class="rotulo">${ic("abertura")}Vídeo</div>
        <div class="rotulo">${ic("mic")}Narração</div>
        <div class="rotulo">${ic("texto")}Legenda</div>
        <div class="rotulo">${ic("musica")}Música</div>
        <div class="rotulo regua"></div>
      </div>
      <div class="rolagem" id="ed-rolagem"><div class="faixas" id="ed-faixas"></div></div>
    </div>
    <div class="barra-ferr" role="toolbar" aria-label="Ferramentas do editor">
      ${FERRAMENTAS.map(([k, i, t]) => `<button class="ferr ${EDITOR.painel === k ? "ativo" : ""}" data-ferr="${k}" aria-pressed="${EDITOR.painel === k}">${ic(i, "g")}${t}</button>`).join("")}
    </div>
    <div id="ed-painel"></div>
    ${p.tem_video_final ? `<div class="linha fim">${p.aprovacoes.final ? TAGS.ok("corte final aprovado") : ""}
      <button class="btn prim grande" id="aprovar-f">${p.aprovacoes.final ? `${ic("baixar")} Ir para exportar` : `${ic("ok")} Aprovar e exportar`}</button></div>` : ""}`;

  const video = $("#ed-video");
  const L = lt.lt;
  const desenharTrilhas = () => {
    const pps = EDITOR.pps;
    const larg = Math.max(total * pps + 40, $("#ed-rolagem").clientWidth);
    const px = (t) => `${(t * pps).toFixed(1)}px`;
    let video_b = "";
    if (L.abertura_s > 0) video_b += `<div class="bloco cartao-b ${EDITOR.painel === "abertura" ? "sel" : ""}" data-cartao="abertura" data-seek="0" style="left:0;width:${px(L.abertura_s)}" title="Abertura: clique para editar">${ic("abertura")} Abertura</div>`;
    for (const c of lt.cenas) {
      video_b += `<div class="bloco cena" data-seek="${c.ini}" title="${esc(c.tela)} · ${esc(c.tipo)}" style="left:${px(c.ini)};width:${px(c.fim - c.ini)};background-image:url('/api/biblioteca/${id}/quadro?t=${c.t_base}&largura=240')"><span>${esc(c.tela)}</span></div>`;
    }
    if (!lt.cenas.length) video_b += `<div class="bloco cena" style="left:${px(L.deslocamento_video_s)};width:${px(L.video_s)}"><span>Vídeo gravado</span></div>`;
    if (L.encerramento_s > 0) video_b += `<div class="bloco cartao-b ${EDITOR.painel === "encerramento" ? "sel" : ""}" data-cartao="encerramento" data-seek="${L.fim_video_s}" style="left:${px(L.total_s - L.encerramento_s)};width:${px(L.encerramento_s)}" title="Encerramento: clique para editar">${ic("encerramento")} Encerramento</div>`;
    const icoFala = (f) => f.situacao === "ESTOURA" ? "⚠" : f.ajustada ? "✂" : (f.velocidade || 1) > 1.001 ? "⚡" : "✓";
    const descFala = (f) => f.situacao === "ESTOURA" ? "não coube" : f.ajustada ? "encurtada pela IA" : (f.velocidade || 1) > 1.001 ? `acelerada ${Math.round((f.velocidade - 1) * 100)}%` : f.situacao === "sem voz" ? "sem voz" : "ok";
    const rotFala = (f) => f.id === "abertura" ? "Abertura" : f.id === "encerramento" ? "Encerramento" : `Fala ${f.id}`;
    const falas = lt.falas.map((f) => {
      const ehCartao = f.id === "abertura" || f.id === "encerramento";
      return `<div class="bloco fala ${ehCartao ? "cartao-fala" : ""} ${f.situacao === "ESTOURA" ? "estoura" : (f.velocidade || 1) > 1.001 ? "alerta" : ""} ${EDITOR.sel === String(f.id) && EDITOR.painel === "fala" ? "sel" : ""}"
        ${ehCartao ? `data-cartao="${f.id}"` : `data-fala="${f.id}"`} data-seek="${f.ini}" title="${rotFala(f)}: ${esc(descFala(f))}" style="left:${px(f.ini)};width:${px(Math.max(f.dur, 0.4))}">${icoFala(f)} ${rotFala(f)} <small>${f.dur.toFixed(1)}s</small></div>`;
    }).join("");
    const legendas = lt.deixas.map((d) => `<div class="bloco legenda" data-seek="${d.ini}" title="${esc(d.linhas.join(" "))}" style="left:${px(d.ini)};width:${px(d.fim - d.ini)}">${esc(d.linhas.join(" "))}</div>`).join("");
    const mus = lt.musica ? `<div class="bloco musica" data-ferr-bloco="musica" data-seek="0" style="left:0;width:${px(lt.musica.fim)}">♪ ${esc(lt.musica.nome)} <small>${esc(lt.musica.autor)}</small></div>`
      : `<div class="bloco" data-ferr-bloco="musica" style="left:8px;color:var(--texto-2);font-weight:500">Sem música · clique para escolher</div>`;
    let regua = "";
    const passo = pps >= 30 ? 1 : pps >= 14 ? 5 : pps >= 7 ? 10 : 30;
    for (let t = 0; t <= total; t += passo) regua += `<div class="marca-t" style="left:${px(t)}">${t}s</div>`;
    $("#ed-faixas").style.width = `${larg}px`;
    $("#ed-faixas").innerHTML = `<div class="faixa">${video_b}</div><div class="faixa">${falas}</div><div class="faixa">${legendas}</div><div class="faixa">${mus}</div>
      <div class="regua">${regua}</div><div class="cabeca" id="ed-cabeca" style="left:0"></div>`;
  };
  if (!EDITOR.ajustado) { EDITOR.pps = Math.max(4, Math.min(40, Math.floor(($("#ed-rolagem").clientWidth - 30) / Math.max(total, 1)))); EDITOR.ajustado = true; $("#ed-zoom").value = EDITOR.pps; }
  desenharTrilhas();

  const tAtual = () => (video ? video.currentTime : EDITOR.t || 0);
  const irPara = (t) => { t = Math.max(0, Math.min(total, t)); if (video) video.currentTime = t; EDITOR.t = t; };
  let tocandoAntes = null;
  const ciclo = () => {
    const t = tAtual();
    const cabeca = $("#ed-cabeca");
    if (!cabeca) return;
    cabeca.style.left = `${t * EDITOR.pps}px`;
    $("#ed-tempo").textContent = `${fmtT(t)} / ${fmtDur(total)}`;
    const tocando = video && !video.paused;
    if (tocando) {
      const rol = $("#ed-rolagem"), x = t * EDITOR.pps;
      if (x > rol.scrollLeft + rol.clientWidth - 60 || x < rol.scrollLeft) rol.scrollLeft = x - 80;
    }
    if (tocando !== tocandoAntes) { $("#ed-play").innerHTML = ic(tocando ? "pausa" : "play"); tocandoAntes = tocando; }
    EDITOR.raf = requestAnimationFrame(ciclo);
  };
  ciclo();

  const selecionar = (painel) => {
    EDITOR.painel = painel;
    $$("[data-ferr]").forEach((x) => { x.classList.toggle("ativo", x.dataset.ferr === painel); x.setAttribute("aria-pressed", x.dataset.ferr === painel); });
    desenharTrilhas();
    abrirPainel();
    $("#ed-painel").scrollIntoView({ behavior: "smooth", block: "nearest" });
  };
  $("#ed-faixas").addEventListener("click", (e) => {
    const b = e.target.closest("[data-seek]");
    const fala = e.target.closest("[data-fala]");
    const cart = e.target.closest("[data-cartao]");
    const fb = e.target.closest("[data-ferr-bloco]");
    if (fala) { EDITOR.sel = fala.dataset.fala; selecionar("fala"); }
    else if (cart) selecionar(cart.dataset.cartao);
    else if (fb) selecionar(fb.dataset.ferrBloco);
    if (b) { irPara(+b.dataset.seek); return; }
    if (fb) return;
    const r = $("#ed-faixas").getBoundingClientRect();
    irPara((e.clientX - r.left) / EDITOR.pps);
  });
  $("#ed-zoom").oninput = (e) => { EDITOR.pps = +e.target.value; desenharTrilhas(); };
  $("#ed-play").onclick = () => { if (video) video.paused ? video.play() : video.pause(); };
  const inicios = lt.falas.map((f) => f.ini).sort((a, b) => a - b);
  $("#ed-ant").onclick = () => { const t = tAtual() - 0.3; irPara([...inicios].reverse().find((x) => x < t) ?? 0); };
  $("#ed-prox").onclick = () => { const t = tAtual() + 0.05; const x = inicios.find((y) => y > t); if (x !== undefined) irPara(x); };
  const recarregar = () => { if (location.hash.startsWith(`#/video/${id}/editor`)) rotear(); };
  const montar = async () => acompanhar(await api("POST", `/api/projetos/${id}/montar`), recarregar);
  $("#ed-montar").onclick = montar;
  if ($("#montar0")) $("#montar0").onclick = montar;
  $$("[data-ferr]").forEach((b) => b.onclick = () => {
    if (b.dataset.ferr === "exportar") { location.hash = `#/video/${id}/exportar`; return; }
    selecionar(b.dataset.ferr);
  });
  const ap = $("#aprovar-f");
  if (ap) ap.onclick = async () => {
    if (!p.aprovacoes.final) {
      if (p.qa && p.qa.falhas && !(await confirmar("Qualidade com falhas", "O controle de qualidade encontrou falhas. Veja em Qualidade. Aprovar assim mesmo?", "Aprovar"))) return;
      await api("POST", `/api/projetos/${id}/aprovar`, { etapa: "final" });
      toast("Corte final aprovado");
    }
    location.hash = `#/video/${id}/exportar`;
  };
  const refazer = async () => acompanhar(await api("POST", `/api/projetos/${id}/refazer`), recarregar);

  function abrirPainel() {
    const alvo = $("#ed-painel");
    const k = EDITOR.painel;
    if (k === "abertura" || k === "encerramento") {
      alvo.innerHTML = `<div class="cartao"><div class="linha" style="margin-bottom:12px"><h2 style="margin:0">${ic(k)} ${k === "abertura" ? "Abertura" : "Encerramento"}</h2>
        <span class="espaco"></span><span class="peq">Texto, imagem e fala. Salva sozinho; aplique para ver no vídeo.</span></div><div id="cx-area"></div></div>`;
      editorCartao($("#cx-area"), id, k, { roteiro: p.roteiro, aoAplicar: refazer });
      return;
    }
    const fn = { fala: painelFala, capa: painelCapa, musica: painelMusica, qa: painelQa }[k] || painelFala;
    fn(alvo, p, id, lt, { video, irPara, tAtual, refazer, montar });
  }
  abrirPainel();
}

function painelFala(el, p, id, lt, ctx) {
  const f = lt.falas.find((x) => String(x.id) === EDITOR.sel);
  if (!f) {
    el.innerHTML = `<div class="cartao"><h2>${ic("fala")} Falas</h2><p class="peq">Clique numa fala da trilha Narração para mudar o texto. A aplicação refaz só essa fala, resolve o encaixe e monta de novo.</p>
      <p class="peq">Ícones: ✓ ritmo natural · ⚡ acelerada · ✂ encurtada pela IA · ⚠ não coube. Para ver todas as falas de uma vez, use <a href="#/video/${id}/roteiro">Roteiro completo</a>.</p></div>`;
    return;
  }
  el.innerHTML = `<div class="cartao"><div class="linha"><h2 style="margin:0">${ic("fala")} Fala ${f.id}</h2>
      <span class="peq">${fmtT(f.ini)} · ${f.dur.toFixed(1)} s</span><span class="espaco"></span>
      ${f.situacao === "ESTOURA" ? TAGS.erro("não coube") : f.ajustada ? TAGS.info("encurtada pela IA") : (f.velocidade || 1) > 1.001 ? TAGS.aviso(`acelerada ${Math.round((f.velocidade - 1) * 100)}%`) : TAGS.ok("ritmo natural")}
      ${f.emprestou_s > 0.05 ? TAGS.info(`usou +${f.emprestou_s.toFixed(1)} s de silêncio`) : ""}</div>
    <div class="grade g2" style="margin-top:12px">
      <div class="campo"><label for="pf-leg">Legenda</label><textarea id="pf-leg" rows="3">${esc(f.texto_legenda)}</textarea></div>
      <div class="campo"><label for="pf-fal">Texto falado <span id="pf-cont"></span></label><textarea id="pf-fal" rows="3">${esc(f.texto_falado)}</textarea></div>
    </div>
    <div class="linha"><button class="btn peq" id="pf-copiar">Usar a legenda como texto falado</button><span class="espaco"></span>
      <button class="btn prim" id="pf-aplicar">${ic("refazer")} Aplicar no vídeo</button></div>
    <p class="peq" style="margin-top:8px">Se o texto novo não couber, a aplicação usa o silêncio seguinte, ajusta a velocidade ou encurta sozinha.</p></div>`;
  const cont = () => { $("#pf-cont").innerHTML = contadorHtml($("#pf-fal").value.trim().length, f.orcamento); };
  $("#pf-fal").oninput = cont;
  cont();
  $("#pf-copiar").onclick = () => { $("#pf-fal").value = $("#pf-leg").value; cont(); };
  $("#pf-aplicar").onclick = async () => {
    const rot = p.roteiro;
    const dados = { abertura: { texto_legenda: rot.abertura?.texto_legenda || "", texto_falado: rot.abertura?.texto_falado || "" },
      falas: rot.falas.map((x) => ({ janela: x.janela, texto_legenda: x.texto_legenda, texto_falado: x.texto_falado, numeros_citados: x.numeros_citados })) };
    const alvo = dados.falas.find((x) => x.janela === f.janela);
    alvo.texto_legenda = $("#pf-leg").value;
    alvo.texto_falado = $("#pf-fal").value;
    await api("PUT", `/api/projetos/${id}/roteiro`, dados);
    ctx.refazer();
  };
}

async function painelCapa(el, p, id, lt, ctx) {
  const { capa: c, instante_automatico } = await api("GET", `/api/projetos/${id}/capa`);
  const D = lt.lt.deslocamento_video_s;
  el.innerHTML = `<div class="cartao"><h2>${ic("imagem")} Capa do vídeo</h2>
    <p class="peq">A imagem que aparece antes do play (YouTube, LinkedIn, plataforma de treinamento). Vai embutida no MP4 e também como JPG.</p>
    <div class="cartao-edit">
      <div><img class="previa" id="capa-img" src="/api/projetos/${id}/capa.jpg?v=${Date.now()}" alt="Prévia da capa"></div>
      <div>
        <div class="campo"><label>Imagem</label>
          ${segmentos("capa-modo", [["automatica", "Automática", "ia"], ["quadro", "Quadro do vídeo", "abertura"], ["imagem", "Enviada", "enviar"]], c.modo)}
          <div class="ajuda" id="capa-ajuda"></div></div>
        <div class="linha" style="margin-bottom:12px"><button class="btn peq" id="capa-usar-quadro">⌖ Usar o quadro atual do player</button>
          <label class="btn peq" for="capa-up" style="margin:0">${ic("enviar")} Enviar imagem</label><input type="file" id="capa-up" accept="image/png,image/jpeg,image/webp" hidden></div>
        ${chave("capa-texto", "Escrever título na capa (não vale para imagem enviada)", c.mostrar_texto)}
        <div class="campo"><label for="capa-tit">Título</label><input type="text" id="capa-tit" value="${esc(c.titulo)}"></div>
        <div class="campo"><label for="capa-sub">Subtítulo</label><input type="text" id="capa-sub" value="${esc(c.subtitulo)}" placeholder="opcional"></div>
        <div class="linha"><span class="peq" id="capa-status"></span><span class="espaco"></span><a class="btn peq" href="/api/projetos/${id}/capa.jpg" download="capa.jpg">${ic("baixar")} Baixar JPG</a></div>
      </div></div>
    <p class="peq" style="margin-top:8px">A capa nova entra no próximo Montar de novo e sempre nas exportações.</p></div>`;
  let t = c.t_s, modo = c.modo;
  const ajuda = () => {
    $("#capa-ajuda").innerHTML = modo === "automatica" ? `A IA escolhe o quadro mais representativo (${fmtT(instante_automatico)} do vídeo gravado).`
      : modo === "quadro" ? `Quadro em ${t != null ? fmtT(t) : "?"}: posicione o player e clique em Usar o quadro atual.` : c.imagem ? "Imagem enviada por você." : "Envie uma imagem 16:9.";
  };
  ajuda();
  const salvar = async () => {
    $("#capa-status").textContent = "⏳ salvando…";
    await api("PUT", `/api/projetos/${id}/capa`, { modo, t_s: t, titulo: $("#capa-tit").value, subtitulo: $("#capa-sub").value, mostrar_texto: $("#capa-texto").checked });
    $("#capa-img").src = `/api/projetos/${id}/capa.jpg?v=${Date.now()}`;
    $("#capa-status").innerHTML = TAGS.ok("salvo");
  };
  const salvarAdiado = adiar(salvar, 700);
  ligarSegmentos(el, "capa-modo", (v) => { modo = v; ajuda(); salvar(); });
  $("#capa-tit").oninput = salvarAdiado;
  $("#capa-sub").oninput = salvarAdiado;
  $("#capa-texto").onchange = salvar;
  $("#capa-usar-quadro").onclick = async () => {
    const tf = ctx.tAtual() - D;
    if (tf < 0 || tf > lt.lt.video_s) { toast("Posicione o player dentro do vídeo gravado (fora da abertura e do encerramento)", "erro"); return; }
    t = +tf.toFixed(2);
    modo = "quadro";
    $$(`[data-seg="capa-modo"] button`).forEach((x) => x.classList.toggle("sel", x.dataset.v === "quadro"));
    ajuda();
    await salvar();
  };
  $("#capa-up").onchange = async (e) => {
    const f = e.target.files[0];
    if (!f) return;
    await api("POST", `/api/projetos/${id}/capa/imagem?nome=${encodeURIComponent(f.name)}`, f);
    painelCapa(el, p, id, lt, ctx);
  };
}

async function painelMusica(el, p, id, lt, ctx) {
  const cfg = (await carregarConfig()).config;
  const [{ musicas }, info] = await Promise.all([api("GET", "/api/musicas"), api("GET", `/api/musicas/gerar/info?video_id=${id}`)]);
  const plano = info.plano || {};
  el.innerHTML = `
    <div class="grade g2">
      <div class="cartao"><h2>${ic("ia")} Gerar música para este vídeo <span class="tag ok">✓ recomendado</span></h2>
        <p class="peq">O Eleven Music compõe uma faixa instrumental no tamanho exato do vídeo (${fmtDur(info.duracao_s)}), feita para ficar sob a narração. É a opção mais segura para uso comercial.</p>
        ${plano.erro ? `<div class="alerta aviso">⚠ ${esc(plano.erro)}</div>`
          : `<div class="alerta ${plano.individual ? "aviso" : "info"}">${plano.individual ? "⚠" : "●"} <span><b>Plano ${esc(plano.nome || "?")}:</b> ${esc(plano.aviso || "")}</span></div>`}
        <div class="campo"><label>Estilo</label><div class="chips">${info.estilos.map((e, i) => `<button type="button" class="chip ${i === 0 ? "sel" : ""}" data-estilo="${e.id}">${esc(e.nome)}</button>`).join("")}</div></div>
        <div class="campo"><label for="mus-desc">Detalhe (opcional)</label><input type="text" id="mus-desc" placeholder="ex.: mais animada no final, sem bateria"></div>
        <div class="linha"><button class="btn prim" id="mus-gerar" ${plano.erro ? "disabled" : ""}>${ic("ia")} Gerar e usar</button><span class="peq">custo estimado: ${usd(info.custo_usd)}</span></div>
      </div>
      <div class="cartao"><h2>${ic("musica")} Minhas faixas</h2>
        <div class="lista-musicas">${musicas.map((m) => itemMusica(m, cfg.musica.arquivo,
          `${!m.verificada && m.origem !== "eleven_music" ? `<button class="btn peq" data-confirmar="${esc(m.arquivo)}" data-pagina="${esc(m.pagina || "")}">Confirmar licença</button>` : ""}<button class="btn-icone" data-apagar-mus="${esc(m.arquivo)}" aria-label="Apagar faixa" title="Apagar faixa">${ic("lixo")}</button>`)).join("")}
          <div class="musica-item"><span></span><div class="t">Sem música</div><div>${cfg.musica.arquivo ? `<button class="btn peq" data-usar="">Usar</button>` : TAGS.ok("em uso")}</div></div>
        </div>
        <p class="peq" style="margin-top:10px"><b>Faixa licenciada pela empresa</b> (Epidemic Sound, Artlist, banco próprio): envie o áudio e o comprovante (.txt com o mesmo nome) e confirme a licença.</p>
        <div class="linha"><label class="btn peq" for="up-mus" style="margin:0">${ic("enviar")} Enviar faixa ou comprovante</label><input type="file" id="up-mus" accept="audio/*,.txt" hidden multiple></div>
        <div class="grade g2" style="margin-top:12px">
          <div class="campo"><label for="nf">Volume de fundo: <b id="nf-v">${cfg.musica.nivel_fundo_db} dB</b></label><input type="range" id="nf" min="-40" max="-6" step="1" value="${cfg.musica.nivel_fundo_db}" style="width:100%"></div>
          <div class="campo"><label for="nv">Volume sob a voz: <b id="nv-v">${cfg.musica.nivel_sob_voz_db} dB</b></label><input type="range" id="nv" min="-50" max="-12" step="1" value="${cfg.musica.nivel_sob_voz_db}" style="width:100%"></div>
        </div>
        <div class="linha"><span class="peq">Trocou a música ou o volume?</span><button class="btn peq" id="mus-montar">${ic("refazer")} Montar de novo</button></div>
      </div>
    </div>
    <details class="cartao"><summary><b>Catálogo aberto (avançado, por sua conta e risco)</b></summary>
      <div class="alerta aviso" style="margin-top:12px">⚠ <span>Este catálogo (Openverse) <b>não verifica as licenças</b>; os termos dele dizem que a responsabilidade de conferir é de quem usa. Faixas podem ter licença errada ou ser reivindicadas pelo Content ID. Faixas daqui ficam como "licença não confirmada" até você confirmar.</span></div>
      <div class="linha"><input type="text" id="cat-q" placeholder="ex.: corporate, piano, ambient" style="flex:1" value="${esc(EDITOR.busca || "corporate")}">
        <select id="cat-lic" style="width:auto"><option value="livre">Só CC0 e domínio público</option><option value="atribuicao">Só CC BY (exige crédito)</option></select>
        <button class="btn" id="cat-buscar">${ic("busca")} Buscar</button></div>
      <div class="lista-musicas" id="cat-res"><p class="peq">Faça uma busca.</p></div>
    </details>`;
  let estilo = info.estilos[0] ? info.estilos[0].id : "corporativo";
  const recarregar = () => painelMusica(el, p, id, lt, ctx);
  $$("[data-estilo]", el).forEach((b) => b.onclick = () => { estilo = b.dataset.estilo; $$("[data-estilo]", el).forEach((x) => x.classList.toggle("sel", x === b)); });
  $("#mus-gerar").onclick = async () => acompanhar(await api("POST", `/api/projetos/${id}/musica/gerar`, { estilo, descricao: $("#mus-desc").value }), (d) => { if (d.situacao === "ok") recarregar(); });
  $("#mus-montar").onclick = () => ctx.montar();
  let itens = [];
  const buscar = async (q) => {
    EDITOR.busca = q;
    $("#cat-res").innerHTML = `<p class="peq">⏳ Buscando "${esc(q)}"…</p>`;
    try {
      const r = await api("GET", `/api/musicas/catalogo?q=${encodeURIComponent(q)}&licenca=${$("#cat-lic").value}`, undefined, { silencioso: true });
      itens = r.itens;
      $("#cat-res").innerHTML = itens.length ? itens.map((m, i) => `<div class="musica-item">
          <button class="play" data-ouvir="${esc(m.arquivo_url)}" aria-label="Ouvir amostra">${ic("play")}</button>
          <div style="min-width:0"><div class="t" title="${esc(m.titulo)}">${esc(m.titulo)}</div>
            <div class="peq">${esc(m.autor)} · ${fmtDur(m.duracao_s)} · ${m.licenca === "by" ? "CC BY (exige crédito)" : m.licenca === "pdm" ? "domínio público" : "CC0"}
              ${m.pagina ? ` · <a href="${esc(m.pagina)}" target="_blank" rel="noopener">conferir na fonte ↗</a>` : ""}</div></div>
          <button class="btn peq" data-baixar="${i}">${ic("baixar")} Baixar</button></div>`).join("") : `<p class="peq">Nada encontrado. Tente outro termo em inglês.</p>`;
    } catch (e) {
      $("#cat-res").innerHTML = `<div class="alerta erro">✕ ${esc(e.message)}</div>`;
    }
  };
  $("#cat-buscar").onclick = () => buscar($("#cat-q").value.trim());
  $("#cat-q").onkeydown = (e) => { if (e.key === "Enter") buscar($("#cat-q").value.trim()); };
  el.onclick = async (e) => {
    if (tocarAmostra(e, el)) return;
    const bx = e.target.closest("[data-baixar]");
    if (bx) {
      bx.disabled = true;
      acompanhar(await api("POST", "/api/musicas/catalogo/baixar", { item: itens[+bx.dataset.baixar], usar: false }), (d) => { if (d.situacao === "ok") recarregar(); });
      return;
    }
    const conf = e.target.closest("[data-confirmar]");
    if (conf) {
      const pagina = conf.dataset.pagina;
      const r = await modal({ titulo: "Confirmar licença", html: `<p>Confirme só se você conferiu a licença na fonte original ou se a empresa licenciou esta faixa para uso comercial em vídeo.</p>
        ${pagina ? `<p><a href="${esc(pagina)}" target="_blank" rel="noopener">Abrir a página da obra ↗</a></p>` : ""}
        <div class="campo"><label for="conf-origem">De onde vem a licença?</label><input type="text" id="conf-origem" placeholder="ex.: Epidemic Sound, assinatura da empresa; ou CC0 conferida na página"></div>`,
        botoes: [{ texto: "Cancelar", valor: false }, { texto: "Confirmo a licença", valor: true, classe: "prim" }] });
      if (r.valor !== true) return;
      await api("POST", `/api/musicas/${encodeURIComponent(conf.dataset.confirmar)}/confirmar`, { origem_licenca: r.dados["conf-origem"] || "" });
      toast("Licença confirmada");
      recarregar();
      return;
    }
    const usar = e.target.closest("[data-usar]");
    if (usar) { await api("PUT", "/api/config", { musica: { arquivo: usar.dataset.usar } }); toast("Música escolhida. Clique em Montar de novo."); recarregar(); return; }
    const ap = e.target.closest("[data-apagar-mus]");
    if (ap && await confirmar("Apagar faixa", `Apagar <b>${esc(ap.dataset.apagarMus)}</b> e o comprovante?`, "Apagar", "perigo")) {
      await api("DELETE", `/api/musicas/${encodeURIComponent(ap.dataset.apagarMus)}`);
      recarregar();
    }
  };
  const niveis = adiar(() => api("PUT", "/api/config", { musica: { nivel_fundo_db: +$("#nf").value, nivel_sob_voz_db: +$("#nv").value } }), 400);
  $("#nf").oninput = (e) => { $("#nf-v").textContent = `${e.target.value} dB`; niveis(); };
  $("#nv").oninput = (e) => { $("#nv-v").textContent = `${e.target.value} dB`; niveis(); };
  $("#up-mus").onchange = async (e) => {
    for (const f of e.target.files) await api("POST", `/api/musicas?nome=${encodeURIComponent(f.name)}`, f);
    toast("Arquivo(s) enviado(s)");
    recarregar();
  };
}

function painelQa(el, p, id) {
  const v = Date.now();
  if (!p.qa) { el.innerHTML = `<div class="cartao"><h2>${ic("lupa")} Qualidade</h2><p class="peq">O relatório aparece depois da montagem.</p></div>`; return; }
  el.innerHTML = `<div class="cartao md"><div class="linha"><h2 style="margin:0">${ic("lupa")} Controle de qualidade</h2><span class="espaco"></span>
      ${p.qa.falhas ? TAGS.erro(`${p.qa.falhas} falha(s)`) : TAGS.ok("sem falhas")} ${p.qa.avisos ? TAGS.aviso(`${p.qa.avisos} atenção`) : ""}</div>
    ${mdParaHtml(p.qa_md.split("\n").slice(1).join("\n"))}
    <div class="miniaturas">${p.qa.quadros.map((q) => `<figure style="margin:0"><img src="/api/projetos/${id}/arquivo/${q.arquivo}?v=${v}" alt="${esc(q.nome)}"><figcaption class="peq">${esc(q.nome)} · ${q.t_s} s</figcaption></figure>`).join("")}</div></div>`;
}

/* ================= EXPORTAR ================= */

async function telaExportar(id) {
  const [p] = await Promise.all([api("GET", `/api/projetos/${id}`), carregarConfig()]);
  const cab = await cabProjeto(id, "exportar", p);
  const ex = ESTADO.cfg.config.exportacao;
  const sis = ESTADO.sistema || (ESTADO.sistema = await api("GET", "/api/sistema"));
  conteudo().innerHTML = `${cab}
    ${!p.tem_video_final ? `<div class="alerta aviso">⚠ O vídeo ainda não foi gerado. <a href="#/video/${id}/configurar?passo=gerar">Configurar e gerar</a></div>`
      : !p.aprovacoes.final ? `<div class="alerta aviso">⚠ O corte final ainda não foi aprovado no editor. Dá para exportar assim mesmo.</div>` : ""}
    <div class="grade g2">
      <div class="cartao"><h2>${ic("caixa")} Formatos</h2>
        ${chave("x-h", "MP4 16:9 (1920×1080)", ex.horizontal)}
        ${chave("x-v", "MP4 vertical 9:16 (1080×1920, com fundo desfocado)", ex.vertical)}
        ${chave("x-s", "Versão sem narração e sem legenda", ex.sem_narracao)}
        ${chave("x-srt", "Legenda .srt separada", ex.srt_separado)}
        <p class="peq">Sempre vão junto: capa em JPG e os créditos e a licença da música.</p>
        <button class="btn prim grande" id="exportar" ${p.tem_video_final ? "" : "disabled"}>${ic("baixar")} Exportar</button>
      </div>
      <div class="cartao"><h2>${ic("pasta")} Onde ficam</h2>
        <p>Na pasta de trabalho, em <code>exportados</code>:</p>
        <p class="mono" style="word-break:break-all">${esc(sis.pasta_trabalho_host)}/exportados/</p>
        <div id="res-export"></div>
      </div>
    </div>`;
  $("#exportar").onclick = async () => {
    const opc = { horizontal: $("#x-h").checked, vertical: $("#x-v").checked, sem_narracao: $("#x-s").checked, srt_separado: $("#x-srt").checked };
    const t = await api("POST", `/api/projetos/${id}/exportar`, opc);
    acompanhar(t, (d) => {
      if (d.situacao !== "ok" || !$("#res-export")) return;
      $("#res-export").innerHTML = `<h3 style="margin-top:12px">Arquivos gerados</h3><ul>${d.resultado.arquivos.map((a) => `<li><a href="/api/exportados/${a.caminho.split("/").map(encodeURIComponent).join("/")}">${esc(a.nome)}</a> <span class="peq">${a.tamanho_mb} MB</span></li>`).join("")}</ul>`;
    });
  };
}
