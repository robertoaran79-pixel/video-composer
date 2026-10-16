"use strict";
/* Configurações em seções que abrem e fecham, com a voz dinâmica por motor */

const CHAVE_SECOES = "vc-config-abertas";
const secoesAbertas = () => { try { return JSON.parse(localStorage.getItem(CHAVE_SECOES) || '["aparencia"]'); } catch (_) { return ["aparencia"]; } };

function secao(id, icone, titulo, resumo, corpo) {
  return `<details class="acordeao" data-secao="${id}" ${secoesAbertas().includes(id) ? "open" : ""}>
    <summary><span class="ic-sec">${ic(icone)}</span><span><div class="tit">${titulo}</div><div class="res" id="res-${id}">${resumo}</div></span><span class="seta">${ic("seta")}</span></summary>
    <div class="corpo">${corpo}</div></details>`;
}

function campoChave(nome, rotulo, s, suf = "") {
  return `<div class="campo campo-chave"><label for="k-${nome}${suf}">${rotulo}</label>
    <p class="peq">${s[nome].definida ? `${TAGS.ok("definida")} <span class="chave-mascara">${esc(s[nome].mascara)}</span> · ${esc(s[nome].origem)}` : TAGS.aviso("não informada")}</p>
    <div class="linha"><input type="password" id="k-${nome}${suf}" placeholder="cole a nova chave" autocomplete="off" style="flex:1;min-width:200px">
      <button class="btn" data-salvar-chave="${nome}">Salvar chave</button><button class="btn" data-testar="${nome}">Testar</button></div>
    <div class="ajuda">Guardada no cofre da aplicação (fora da pasta de trabalho). A tela só mostra o final.</div>
    <div class="ajuda resultado-teste"></div></div>`;
}

document.addEventListener("click", async (e) => {
  const sv = e.target.closest("[data-salvar-chave]");
  if (sv) {
    const nome = sv.dataset.salvarChave;
    const inp = $("input[type=password]", sv.closest(".campo-chave"));
    const v = inp.value.trim();
    if (!v) { toast("Cole a chave antes de salvar", "erro"); return; }
    await api("PUT", "/api/segredos", { [nome]: v });
    inp.value = "";
    toast("Chave salva");
    rotear();
    return;
  }
  const ts = e.target.closest("[data-testar]");
  if (ts) {
    const alvo = $(".resultado-teste", ts.closest(".campo-chave"));
    alvo.innerHTML = "⏳ testando…";
    const r = await api("POST", `/api/testar/${ts.dataset.testar}`);
    alvo.innerHTML = r.ok ? TAGS.ok(r.mensagem) : TAGS.erro(r.mensagem);
  }
});

/* ---------------- voz: campos que mudam com o motor ---------------- */

const MOTORES = [
  ["elevenlabs", "ElevenLabs (melhor qualidade, pago por caractere)"],
  ["kokoro", "Kokoro (offline e gratuito, vozes feminina e masculinas)"],
  ["piper", "Piper (offline e gratuito, vozes masculinas)"],
];

async function camposVoz(el, { compacto = false } = {}) {
  const d = await carregarConfig();
  const c = d.config;
  const s = d.segredos;
  const motores = ESTADO.sistema && ESTADO.sistema.modo_teste ? [...MOTORES, ["teste", "Voz de teste (simulada)"]] : MOTORES;
  el.innerHTML = `
    <div class="campo" style="max-width:520px"><label for="v-motor">Motor de voz</label>
      <select id="v-motor">${motores.map(([v, t]) => `<option value="${v}" ${v === c.voz.motor ? "selected" : ""}>${esc(t)}</option>`).join("")}</select></div>
    <div id="v-motor-campos"></div>
    <div class="linha" style="margin-top:4px"><button class="btn" id="v-amostra">${ic("play")} Ouvir amostra</button><span id="v-player" style="flex:1;min-width:220px"></span><span class="peq" id="v-status"></span></div>
    ${compacto ? "" : `
    <div class="grade g2" style="margin-top:14px">
      <div class="campo"><label for="v-acel">Aceleração máxima para encaixar a fala: <b id="v-acel-v">${Math.round((c.voz.aceleracao_max - 1) * 100)}%</b></label>
        <input type="range" id="v-acel" min="1" max="1.5" step="0.05" value="${c.voz.aceleracao_max}" style="width:100%">
        <div class="ajuda">Acima de 10% a voz começa a soar apressada; a aplicação prefere encurtar o texto.</div></div>
      <div class="campo"><label>Ritmo da voz atual</label>
        <p>${d.ritmo.calibrado ? `${TAGS.ok("calibrada")} <b>${d.ritmo.car_s.toFixed(1)} car/s</b>` : `${TAGS.info("calibra sozinha no primeiro roteiro")} ${d.ritmo.car_s} car/s padrão`}</p>
        <button class="btn peq" id="v-calibrar">${ic("voz")} Calibrar agora</button></div>
    </div>`}`;
  const area = $("#v-motor-campos", el);
  const desenhar = () => {
    const m = $("#v-motor", el).value;
    if (m === "elevenlabs") {
      area.innerHTML = `${compacto && !s.elevenlabs.definida ? `<div class="alerta aviso">⚠ Informe a chave da ElevenLabs em <a href="#/config">Configurações</a>, seção Voz.</div>` : ""}
        ${compacto ? "" : campoChave("elevenlabs", "Chave de API da ElevenLabs", s)}
        <div class="grade g2">
          <div class="campo"><label for="v-el">Voz</label><div class="linha"><select id="v-el" style="flex:1"><option value="${esc(c.voz.elevenlabs.voice_id)}">${esc(c.voz.elevenlabs.nome || "(carregue a lista)")}</option></select>
            <button class="btn" id="v-el-lista" ${s.elevenlabs.definida ? "" : "disabled"}>Carregar lista</button></div><div class="ajuda">Vozes em português do Brasil aparecem primeiro, marcadas com pt-BR.</div></div>
          <div class="campo"><label for="v-el-mod">Modelo</label><select id="v-el-mod">${d.modelos_eleven.map((x) => `<option value="${x.id}" ${x.id === c.voz.elevenlabs.modelo ? "selected" : ""}>${esc(x.nome)}</option>`).join("")}</select></div>
        </div>`;
      $("#v-el-lista", el).onclick = async () => {
        const { vozes } = await api("GET", "/api/vozes");
        $("#v-el", el).innerHTML = vozes.map((x) => `<option value="${esc(x.id)}" data-nome="${esc(x.nome)}" ${x.id === c.voz.elevenlabs.voice_id ? "selected" : ""}>${x.pt_br ? "pt-BR · " : ""}${esc(x.nome)}${x.descricao ? ` · ${esc(x.descricao)}` : ""}</option>`).join("");
        toast(`${vozes.length} vozes carregadas`);
      };
      $("#v-el", el).onchange = salvar;
      $("#v-el-mod", el).onchange = salvar;
    } else if (m === "kokoro") {
      area.innerHTML = `${d.kokoro_instalado ? "" : `<div class="alerta aviso">⚠ O Kokoro não está instalado nesta imagem. Rode o instalador de novo.</div>`}
        <div class="campo" style="max-width:520px"><label for="v-kokoro">Voz</label><select id="v-kokoro">${d.vozes_kokoro.map((x) => `<option value="${x.id}" ${x.id === (c.voz.kokoro || {}).voz ? "selected" : ""}>${esc(x.nome)}</option>`).join("")}</select>
          <div class="ajuda">O modelo (cerca de 350 MB) é baixado na primeira vez e fica guardado. Uso comercial permitido (Apache 2.0).</div></div>`;
      $("#v-kokoro", el).onchange = salvar;
    } else if (m === "piper") {
      area.innerHTML = `<div class="campo" style="max-width:520px"><label for="v-piper">Voz</label><select id="v-piper">${d.vozes_piper.map((x) => `<option value="${x.id}" ${x.id === c.voz.piper.modelo ? "selected" : ""}>${esc(x.nome)}</option>`).join("")}</select>
        <div class="ajuda">Baixada na primeira vez (precisa de internet). Para voz feminina offline, use o Kokoro.</div></div>`;
      $("#v-piper", el).onchange = salvar;
    } else {
      area.innerHTML = `<p class="peq">Voz simulada com tons, só para testar o fluxo sem custo.</p>`;
    }
  };
  const dados = () => {
    const m = $("#v-motor", el).value;
    const voz = { motor: m };
    if (m === "elevenlabs") {
      const op = $("#v-el", el).selectedOptions[0];
      voz.elevenlabs = { voice_id: $("#v-el", el).value, nome: op ? (op.dataset.nome || op.textContent) : "", modelo: $("#v-el-mod", el).value };
    }
    if (m === "kokoro") voz.kokoro = { voz: $("#v-kokoro", el).value };
    if (m === "piper") voz.piper = { modelo: $("#v-piper", el).value };
    if ($("#v-acel", el)) voz.aceleracao_max = +$("#v-acel", el).value;
    return { voz };
  };
  async function salvar() {
    const r = await api("PUT", "/api/config", dados());
    ESTADO.cfg.config = r.config;
    $("#v-status", el).innerHTML = TAGS.ok("salvo");
    const res = $("#res-voz");
    if (res) res.textContent = descVoz();
  }
  desenhar();
  $("#v-motor", el).onchange = async () => { desenhar(); await salvar(); };
  $("#v-amostra", el).onclick = async () => {
    await salvar();
    $("#v-player", el).innerHTML = `<span class="peq">⏳ gerando amostra…</span>`;
    $("#v-player", el).innerHTML = `<audio controls autoplay src="/api/voz/amostra?v=${Date.now()}"></audio>`;
  };
  if ($("#v-acel", el)) $("#v-acel", el).oninput = adiar(salvar, 400);
  if ($("#v-acel", el)) $("#v-acel", el).addEventListener("input", (e) => { $("#v-acel-v", el).textContent = `${Math.round((e.target.value - 1) * 100)}%`; });
  if ($("#v-calibrar", el)) $("#v-calibrar", el).onclick = async () => {
    await salvar();
    acompanhar(await api("POST", "/api/voz/calibrar", {}), () => { if (location.hash === "#/config") telaConfig(); });
  };
}

/* ================= CONFIGURAÇÕES ================= */

async function telaConfig() {
  const [d, sis, { arquivos }, pasta] = await Promise.all([carregarConfig(), api("GET", "/api/sistema"), api("GET", "/api/marcas/arquivos"), api("GET", "/api/sistema/pasta")]);
  ESTADO.sistema = sis;
  const c = d.config, s = d.segredos;
  const m = c.marcas[c.marca_ativa] || c.marcas.padrao;
  const temaAtual = (c.aparencia || {}).tema || "marinho";
  const nomeTema = (PALETAS.find((x) => x.id === temaAtual) || PALETAS[0]).nome;
  const opMarca = (sel) => `<option value="">(nenhuma: fundo com a cor da marca)</option>${arquivos.map((a) => `<option ${a === sel ? "selected" : ""}>${esc(a)}</option>`).join("")}`;
  const selModelo = (etapa) => `<select data-modelo="${etapa}">${d.modelos_claude.map((x) => `<option value="${x.id}" ${x.id === c.claude.modelos[etapa] ? "selected" : ""}>${esc(x.nome)}</option>`).join("")}</select>`;
  const nomeModelo = (id) => (d.modelos_claude.find((x) => x.id === id) || { nome: id }).nome.split(" ")[0];
  const formatos = [c.exportacao.horizontal && "16:9", c.exportacao.vertical && "9:16", c.exportacao.sem_narracao && "sem narração", c.exportacao.srt_separado && ".srt"].filter(Boolean).join(", ");

  conteudo().innerHTML = `
    <h1>Configurações</h1><p class="sub">Valem para todos os vídeos. Clique numa seção para abrir.</p>
    ${sis.modo_teste ? `<div class="alerta aviso">⚠ Modo de teste ligado (VC_MODO_TESTE=1): IA e voz são simuladas.</div>` : ""}

    ${secao("aparencia", "paleta", "Aparência", `Paleta ${esc(nomeTema)}`, `
      <p class="peq">Escolha a paleta de cores da aplicação. Muda na hora e fica salva.</p>
      <div class="paletas">${PALETAS.map((p) => amostraPaleta(p, p.id === temaAtual)).join("")}</div>`)}

    ${secao("claude", "ia", "Claude (IA do roteiro)", `${s.claude.definida ? "✓ chave definida" : "⚠ chave não informada"} · ${nomeModelo(c.claude.modelos.entendimento)} no entendimento, ${nomeModelo(c.claude.modelos.roteiro)} no roteiro`, `
      ${campoChave("claude", "Chave de API da Anthropic", s)}
      <div class="grade g3">
        <div class="campo"><label>Entendimento do vídeo</label>${selModelo("entendimento")}</div>
        <div class="campo"><label>Roteiro</label>${selModelo("roteiro")}</div>
        <div class="campo"><label>Controle de qualidade</label>${selModelo("qa")}</div>
      </div>
      <p class="peq">Padrão: Opus no entendimento e no roteiro (qualidade) e Haiku no controle de qualidade. Sonnet custa cerca de metade do Opus.</p>`)}

    ${secao("voz", "mic", "Voz", esc(descVoz(d)), `<div id="cfg-voz"></div>`)}

    ${secao("pasta", "pasta", "Pasta de trabalho", esc(pasta.configurada || sis.pasta_trabalho_host), `
      <p>Atual: <span class="mono" style="word-break:break-all">${esc(sis.pasta_trabalho_host)}</span></p>
      <p class="peq">Espaço livre: ${sis.livre_gb} GB. Vídeos, projetos, músicas e exportados ficam aqui.</p>
      ${sis.alerta_nuvem ? `<div class="alerta aviso">⚠ ${esc(sis.alerta_nuvem)}</div>` : ""}
      ${pasta.precisa_reiniciar ? `<div class="alerta info">● <span>Nova pasta definida: <b class="mono">${esc(pasta.configurada)}</b>. Feche a aplicação (Parar) e abra de novo (Iniciar) para começar a usar.</span></div>` : ""}
      ${pasta.pode_alterar ? `
        <div class="campo"><label for="pasta-nova">Mudar para</label>
          <div class="linha"><input type="text" id="pasta-nova" placeholder="ex.: /Users/voce/Videos/VideoComposer ou C:\\Videos\\VideoComposer" style="flex:1;min-width:260px" value="${pasta.precisa_reiniciar ? esc(pasta.configurada) : ""}">
            <button class="btn prim" id="pasta-salvar">Salvar</button></div>
          <div class="ajuda">Caminho completo de uma pasta no seu computador. Evite pastas sincronizadas com a nuvem. Os vídeos da pasta atual não são movidos: copie a pasta se quiser levar tudo junto.</div></div>`
        : `<p class="peq">Esta instalação não permite trocar a pasta pela tela. Rode o instalador de novo e escolha a pasta.</p>`}`)}

    ${secao("marca", "marca", "Marca", esc(m.nome), `
      <div class="grade g3">
        <div class="campo"><label for="m-nome">Nome da marca ou cliente</label><input type="text" id="m-nome" value="${esc(m.nome)}"></div>
        <div class="campo"><label for="m-ab">Imagem padrão da abertura</label><select id="m-ab">${opMarca(m.abertura_imagem)}</select></div>
        <div class="campo"><label for="m-en">Imagem padrão do encerramento</label><select id="m-en">${opMarca(m.encerramento_imagem)}</select></div>
        <div class="campo"><label for="m-logo">Logotipo (no fundo com cor)</label><select id="m-logo">${opMarca(m.logotipo)}</select></div>
        <div class="campo"><label>Enviar imagem</label><label class="btn" for="up-marca" style="margin:0">${ic("enviar")} PNG, JPG ou WEBP</label><input type="file" id="up-marca" accept="image/png,image/jpeg,image/webp" hidden></div>
        <div class="campo"><label for="m-fonte">Fonte das legendas</label><input type="text" id="m-fonte" value="${esc(m.fonte)}"><div class="ajuda">Instaladas: DejaVu Sans e Liberation Sans.</div></div>
        ${[["cor_fundo_cartao", "Cor de fundo do cartão"], ["cor_texto_cartao", "Cor do texto do cartão"], ["cor_legenda", "Cor da legenda"], ["cor_fundo_legenda", "Cor da caixa da legenda"]].map(([k, r]) => `
          <div class="campo"><label for="m-${k}">${r}</label><div class="linha"><input type="color" id="m-${k}" value="${esc(m[k])}"><input type="text" data-hex="${k}" value="${esc(m[k])}" style="width:110px" aria-label="${r} em hexadecimal"></div></div>`).join("")}
        <div class="campo"><label for="m-op">Opacidade da caixa da legenda</label><input type="number" id="m-op" value="${m.opacidade_fundo_legenda}" step="0.05" min="0" max="1"></div>
        <div class="campo"><label for="m-tam">Tamanho da legenda (px em 1080p)</label><input type="number" id="m-tam" value="${m.tamanho_fonte}" min="20" max="80"></div>
        <div class="campo"><label for="m-da">Abertura padrão (s, 0 = sem)</label><input type="number" id="m-da" value="${m.duracao_abertura_s}" step="0.5" min="0"></div>
        <div class="campo"><label for="m-dt">Transição (s)</label><input type="number" id="m-dt" value="${m.duracao_transicao_s}" step="0.1" min="0.2"></div>
        <div class="campo"><label for="m-de">Encerramento padrão (s, 0 = sem)</label><input type="number" id="m-de" value="${m.duracao_encerramento_s}" step="0.5" min="0"></div>
      </div>
      <p class="peq">Isto é o padrão para vídeos novos. Cada vídeo pode ter imagem e texto próprios em Abertura e encerramento.</p>
      <button class="btn prim" id="salvar-marca">Salvar marca</button>`)}

    ${secao("musica", "musica", "Música", `fundo ${c.musica.nivel_fundo_db} dB · sob a voz ${c.musica.nivel_sob_voz_db} dB`, `
      ${!s.elevenlabs.definida ? `<div class="alerta info">● Para gerar música com IA (Eleven Music), informe a chave da ElevenLabs na seção Voz, com o motor ElevenLabs selecionado, ou aqui:</div>${campoChave("elevenlabs", "Chave de API da ElevenLabs", s, "-mus")}` : `<p>${TAGS.ok("chave da ElevenLabs definida")} <span class="peq">usada também para gerar música</span></p>`}
      <div class="grade g3">
        <div class="campo"><label for="mu-f">Nível de fundo (dB)</label><input type="number" id="mu-f" value="${c.musica.nivel_fundo_db}"></div>
        <div class="campo"><label for="mu-v">Nível sob a voz (dB)</label><input type="number" id="mu-v" value="${c.musica.nivel_sob_voz_db}"></div>
        <div class="campo"><label for="mu-c">Cortar do fim da faixa antes de repetir (s)</label><input type="number" id="mu-c" value="${c.musica.cortar_fim_s}" step="0.5"></div>
        <div class="campo"><label for="mu-e">Emenda entre repetições (s)</label><input type="number" id="mu-e" value="${c.musica.emenda_s}" step="0.5"></div>
      </div>
      <p class="peq">A faixa de cada vídeo é escolhida na configuração do vídeo ou no editor.</p>
      <button class="btn prim" id="salvar-musica">Salvar música</button>`)}

    ${secao("narracao", "fala", "Padrões de narração", `tom ${esc(c.narracao.tom)} · ${(c.narracao.glossario || []).length} termo(s) no glossário`, `
      <div class="grade g2">
        <div class="campo"><label for="n-idioma">Idioma</label><input type="text" id="n-idioma" value="${esc(c.narracao.idioma)}"></div>
        <div class="campo"><label for="n-tom">Tom</label><input type="text" id="n-tom" value="${esc(c.narracao.tom)}"></div>
        <div class="campo"><label for="n-persona">Persona</label><input type="text" id="n-persona" value="${esc(c.narracao.persona)}"></div>
        <div class="campo"><label for="n-publico">Público</label><input type="text" id="n-publico" value="${esc(c.narracao.publico)}"></div>
      </div>
      <label>Glossário de pronúncia</label><p class="peq">Troca o termo no texto falado (a legenda mantém a grafia certa).</p>
      <table id="glossario"><thead><tr><th>Termo (como se escreve)</th><th>Como falar</th><th></th></tr></thead><tbody></tbody></table>
      <div class="linha" style="margin-top:8px"><button class="btn peq" id="add-g">${ic("mais")} Adicionar termo</button><span class="espaco"></span><button class="btn prim" id="salvar-narr">Salvar padrões</button></div>`)}

    ${secao("exportacao", "caixa", "Exportação", esc(formatos || "nenhum formato marcado"), `
      <div class="campo" style="max-width:420px"><label for="e-leg">Legenda</label><select id="e-leg">
        <option value="gravada" ${c.exportacao.legenda === "gravada" ? "selected" : ""}>Gravada na imagem</option>
        <option value="selecionavel" ${c.exportacao.legenda === "selecionavel" ? "selected" : ""}>Selecionável (faixa de legenda no MP4)</option>
        <option value="nenhuma" ${c.exportacao.legenda === "nenhuma" ? "selected" : ""}>Sem legenda</option></select></div>
      ${chave("e-h", "16:9 marcado por padrão", c.exportacao.horizontal)}
      ${chave("e-v", "9:16 marcado por padrão", c.exportacao.vertical)}
      ${chave("e-s", "Versão sem narração marcada por padrão", c.exportacao.sem_narracao)}
      ${chave("e-srt", ".srt separado marcado por padrão", c.exportacao.srt_separado)}
      <button class="btn prim" id="salvar-exp">Salvar exportação</button>`)}

    ${secao("privacidade", "escudo", "Privacidade, custos e gravação", `limite ${usd(c.privacidade.limite_custo_usd)} por vídeo · gravação até ${c.gravacao.limite_min} min`, `
      ${chave("p-aviso", "Estou ciente de que quadros do vídeo vão para a API da Anthropic e o roteiro vai para a ElevenLabs (quando ela é a voz)", c.privacidade.aviso_aceito)}
      <div class="grade g3">
        <div class="campo"><label for="p-lim">Limite de custo por vídeo (US$)</label><input type="number" id="p-lim" value="${c.privacidade.limite_custo_usd}" step="0.25" min="0"><div class="ajuda">Acima disso, a geração pede confirmação.</div></div>
        <div class="campo"><label for="g-lim">Duração máxima da gravação (min)</label><input type="number" id="g-lim" value="${c.gravacao.limite_min}" min="1" max="120"></div>
        <div class="campo"><label for="g-crf">Qualidade da compressão (CRF, menor = melhor e maior)</label><input type="number" id="g-crf" value="${c.gravacao.crf}" min="16" max="32"></div>
      </div>
      ${chave("g-apagar", "Apagar o arquivo bruto depois da conversão", c.gravacao.apagar_bruto)}
      <button class="btn prim" id="salvar-priv">Salvar</button>`)}

    <p class="peq" style="margin-top:18px">${esc(sis.ffmpeg)} · ${esc(sis.versao)}</p>`;

  // seções abertas ficam lembradas
  $$(".acordeao").forEach((dt) => dt.addEventListener("toggle", () => {
    try { localStorage.setItem(CHAVE_SECOES, JSON.stringify($$(".acordeao[open]").map((x) => x.dataset.secao))); } catch (_) { /* */ }
  }));
  const salvar = async (parcial, msg = "Configurações salvas") => { await api("PUT", "/api/config", parcial); toast(msg); };

  // aparência
  $$("[data-tema]", $(".paletas")).forEach((b) => b.onclick = async () => {
    aplicarTema(b.dataset.tema);
    $$(".paleta").forEach((x) => { x.classList.toggle("sel", x === b); x.setAttribute("aria-pressed", x === b); });
    $("#res-aparencia").textContent = `Paleta ${(PALETAS.find((x) => x.id === b.dataset.tema) || {}).nome}`;
    await api("PUT", "/api/config", { aparencia: { tema: b.dataset.tema } });
  });

  // claude
  $$("[data-modelo]").forEach((sel) => sel.onchange = () => salvar({ claude: { modelos: Object.fromEntries($$("[data-modelo]").map((x) => [x.dataset.modelo, x.value])) } }, "Modelo salvo"));

  // voz
  camposVoz($("#cfg-voz"));

  // pasta
  if ($("#pasta-salvar")) $("#pasta-salvar").onclick = async () => {
    const r = await api("PUT", "/api/sistema/pasta", { caminho: $("#pasta-nova").value });
    toast(r.precisa_reiniciar ? "Pasta salva. Feche e abra a aplicação para usar." : "Pasta salva");
    telaConfig();
  };

  // marca
  $$("[data-hex]").forEach((t) => {
    const cor = $(`#m-${t.dataset.hex}`);
    t.oninput = () => { if (/^#[0-9a-f]{6}$/i.test(t.value)) cor.value = t.value; };
    cor.oninput = () => { t.value = cor.value; };
  });
  $("#up-marca").onchange = async (e) => {
    const f = e.target.files[0];
    if (!f) return;
    await api("POST", `/api/marcas/arquivos?nome=${encodeURIComponent(f.name)}`, f);
    toast("Imagem enviada");
    telaConfig();
  };
  $("#salvar-marca").onclick = () => salvar({ marcas: { [c.marca_ativa]: {
    nome: $("#m-nome").value, abertura_imagem: $("#m-ab").value, encerramento_imagem: $("#m-en").value, logotipo: $("#m-logo").value,
    fonte: $("#m-fonte").value, cor_fundo_cartao: $("#m-cor_fundo_cartao").value, cor_texto_cartao: $("#m-cor_texto_cartao").value,
    cor_legenda: $("#m-cor_legenda").value, cor_fundo_legenda: $("#m-cor_fundo_legenda").value,
    opacidade_fundo_legenda: +$("#m-op").value, tamanho_fonte: +$("#m-tam").value,
    duracao_abertura_s: +$("#m-da").value, duracao_transicao_s: +$("#m-dt").value, duracao_encerramento_s: +$("#m-de").value,
  } } }, "Marca salva");

  $("#salvar-musica").onclick = () => salvar({ musica: { nivel_fundo_db: +$("#mu-f").value, nivel_sob_voz_db: +$("#mu-v").value, cortar_fim_s: +$("#mu-c").value, emenda_s: +$("#mu-e").value } });

  // glossário
  const gl = [...(c.narracao.glossario || [])];
  const desenharG = () => {
    $("#glossario tbody").innerHTML = gl.length ? gl.map((g, i) => `<tr><td><input type="text" data-g="${i}" data-k="termo" value="${esc(g.termo)}" aria-label="Termo"></td><td><input type="text" data-g="${i}" data-k="falado" value="${esc(g.falado)}" aria-label="Como falar"></td><td><button class="btn-icone" data-rmg="${i}" aria-label="Remover termo">${ic("x")}</button></td></tr>`).join("")
      : `<tr><td colspan="3" class="peq">Nenhum termo. Exemplo: "GenIntegrations" falado como "Gen Integreichons".</td></tr>`;
    $$("[data-g]").forEach((inp) => inp.oninput = () => { gl[+inp.dataset.g][inp.dataset.k] = inp.value; });
    $$("[data-rmg]").forEach((b) => b.onclick = () => { gl.splice(+b.dataset.rmg, 1); desenharG(); });
  };
  desenharG();
  $("#add-g").onclick = () => { gl.push({ termo: "", falado: "" }); desenharG(); };
  $("#salvar-narr").onclick = () => salvar({ narracao: { idioma: $("#n-idioma").value, tom: $("#n-tom").value, persona: $("#n-persona").value, publico: $("#n-publico").value, glossario: gl.filter((g) => g.termo && g.falado) } });

  $("#salvar-exp").onclick = () => salvar({ exportacao: { legenda: $("#e-leg").value, horizontal: $("#e-h").checked, vertical: $("#e-v").checked, sem_narracao: $("#e-s").checked, srt_separado: $("#e-srt").checked } });
  $("#salvar-priv").onclick = () => salvar({
    privacidade: { aviso_aceito: $("#p-aviso").checked, limite_custo_usd: +$("#p-lim").value },
    gravacao: { limite_min: +$("#g-lim").value, crf: +$("#g-crf").value, apagar_bruto: $("#g-apagar").checked },
  });
}
