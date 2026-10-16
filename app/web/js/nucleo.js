"use strict";
/* Video Composer · núcleo da interface: utilitários, ícones, tarefas em segundo plano, paletas */

const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const conteudo = () => $("#conteudo");

const ESTADO = { cfg: null, sistema: null, gravando: null, finalidades: null };

/* ---------------- ícones (traço, estilo Lucide) ---------------- */

const ICONES = {
  videos: '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
  mais: '<path d="M12 5v14M5 12h14"/>',
  config: '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/>',
  gravar: '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="4" fill="currentColor"/>',
  enviar: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="M17 8l-5-5-5 5"/><path d="M12 3v12"/>',
  baixar: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="M7 10l5 5 5-5"/><path d="M12 15V3"/>',
  play: '<path d="M7 4l13 8-13 8z" fill="currentColor"/>',
  pausa: '<rect x="6" y="4" width="4" height="16" rx="1" fill="currentColor"/><rect x="14" y="4" width="4" height="16" rx="1" fill="currentColor"/>',
  ant: '<path d="M19 20L9 12l10-8z"/><path d="M5 19V5"/>',
  prox: '<path d="M5 4l10 8-10 8z"/><path d="M19 5v14"/>',
  tesoura: '<circle cx="6" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><path d="M20 4L8.1 15.9M14.5 14.5L20 20M8.1 8.1L12 12"/>',
  musica: '<path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/>',
  imagem: '<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><path d="M21 15l-5-5L5 21"/>',
  texto: '<path d="M4 7V4h16v3M9 20h6M12 4v16"/>',
  fala: '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
  mic: '<rect x="9" y="2" width="6" height="12" rx="3"/><path d="M19 10v1a7 7 0 0 1-14 0v-1M12 18v4M8 22h8"/>',
  ok: '<path d="M20 6L9 17l-5-5"/>',
  x: '<path d="M18 6L6 18M6 6l12 12"/>',
  alerta: '<path d="M10.3 3.9L1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/><path d="M12 9v4M12 17h.01"/>',
  editar: '<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"/>',
  copiar: '<rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>',
  lixo: '<path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>',
  busca: '<circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/>',
  pasta: '<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>',
  paleta: '<circle cx="13.5" cy="6.5" r="1.2" fill="currentColor"/><circle cx="17.5" cy="10.5" r="1.2" fill="currentColor"/><circle cx="8.5" cy="7.5" r="1.2" fill="currentColor"/><circle cx="6.5" cy="12.5" r="1.2" fill="currentColor"/><path d="M12 2a10 10 0 0 0 0 20c1 0 1.7-.8 1.7-1.7 0-.4-.2-.8-.4-1.1-.3-.3-.4-.7-.4-1.1 0-.9.8-1.7 1.7-1.7h2A5.6 5.6 0 0 0 22 11c0-5-4.5-9-10-9z"/>',
  ia: '<path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9z"/><path d="M19 15l.9 2.1L22 18l-2.1.9L19 21l-.9-2.1L16 18l2.1-.9z"/>',
  voz: '<path d="M2 10v4M6 6v12M10 3v18M14 8v8M18 5v14M22 10v4"/>',
  escudo: '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
  caixa: '<path d="M21 16V8a2 2 0 0 0-1-1.7l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.7l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><path d="M3.3 7L12 12l8.7-5M12 22V12"/>',
  seta: '<path d="M6 9l6 6 6-6"/>',
  esquerda: '<path d="M19 12H5M12 19l-7-7 7-7"/>',
  direita: '<path d="M5 12h14M12 5l7 7-7 7"/>',
  abertura: '<rect x="2" y="4" width="20" height="16" rx="2"/><path d="M10 9l5 3-5 3z" fill="currentColor"/>',
  encerramento: '<rect x="2" y="4" width="20" height="16" rx="2"/><path d="M8 12h8M8 9h8M8 15h5"/>',
  refazer: '<path d="M21 12a9 9 0 1 1-3-6.7L21 8"/><path d="M21 3v5h-5"/>',
  olho: '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8S1 12 1 12z"/><circle cx="12" cy="12" r="3"/>',
  lupa: '<circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3M11 8v6M8 11h6"/>',
  roteiro: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6M8 13h8M8 17h5"/>',
  marca: '<path d="M20.6 13.4l-7.2 7.2a2 2 0 0 1-2.8 0L2 12V2h10l8.6 8.6a2 2 0 0 1 0 2.8z"/><circle cx="7" cy="7" r="1.5" fill="currentColor"/>',
  usuarios: '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.9M16 3.1a4 4 0 0 1 0 7.8"/>',
  aperto: '<path d="M11 17l2 2a1 1 0 1 0 3-3"/><path d="M14 14l2.5 2.5a1 1 0 1 0 3-3l-3.9-3.9a2 2 0 0 0-2.8 0l-.9.9a1 1 0 1 1-3-3l2.8-2.8a5 5 0 0 1 5.7-1l.4.2a2 2 0 0 0 1.4.1L21 3"/><path d="M21 14l1-1M3 3l1 1M3 14l7 7"/>',
  fone: '<path d="M3 18v-6a9 9 0 0 1 18 0v6"/><path d="M21 19a2 2 0 0 1-2 2h-1v-6h3zM3 19a2 2 0 0 0 2 2h1v-6H3z"/>',
  grafico: '<path d="M3 3v18h18"/><path d="M7 15l4-4 3 3 6-6"/>',
  megafone: '<path d="M3 11v2a1 1 0 0 0 1 1h3l5 4V6L7 10H4a1 1 0 0 0-1 1zM16 8a5 5 0 0 1 0 8"/>',
  boia: '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="4"/><path d="M4.9 4.9l4.3 4.3M14.8 14.8l4.3 4.3M14.8 9.2l4.3-4.3M4.9 19.1l4.3-4.3"/>',
  relogio: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  dinheiro: '<path d="M12 1v22M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>',
  camadas: '<path d="M12 2l10 5-10 5L2 7z"/><path d="M2 17l10 5 10-5M2 12l10 5 10-5"/>',
  info: '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/>',
  link: '<path d="M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7-7l-1.7 1.7"/><path d="M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7 7l1.7-1.7"/>',
};
const ic = (nome, extra = "") => `<svg class="ic ${extra}" viewBox="0 0 24 24" aria-hidden="true">${ICONES[nome] || ICONES.info}</svg>`;
const ICONE_FINALIDADE = { users: "usuarios", handshake: "aperto", headset: "fone", chart: "grafico", megaphone: "megafone", lifebuoy: "boia" };

/* ---------------- paletas de cor ---------------- */

/* cores mostradas na amostra: [fundo, painel, acento 1, acento 2, texto] */
const PALETAS = [
  { id: "marinho", nome: "Marinho", tipo: "escura", cores: ["#121829", "#222a42", "#19c3b1", "#8b5cf6", "#e8ecf6"] },
  { id: "indigo", nome: "Índigo (logo)", tipo: "escura", cores: ["#0f1024", "#1d2048", "#4f6bff", "#a855f7", "#eceeff"] },
  { id: "grafite", nome: "Grafite", tipo: "escura", cores: ["#16171b", "#26282f", "#38bdf8", "#f59e0b", "#ececef"] },
  { id: "floresta", nome: "Floresta", tipo: "escura", cores: ["#0f1916", "#1b2b26", "#22c55e", "#eab308", "#e6f2ed"] },
  { id: "ameixa", nome: "Ameixa", tipo: "escura", cores: ["#1a1220", "#2b1f35", "#f472b6", "#a78bfa", "#f3eaf7"] },
  { id: "nuvem", nome: "Nuvem", tipo: "clara", cores: ["#f3f5fa", "#ffffff", "#0d9488", "#7c3aed", "#18203a"] },
  { id: "areia", nome: "Areia", tipo: "clara", cores: ["#f6f1e8", "#fffdf8", "#c2410c", "#0f766e", "#2b2318"] },
  { id: "menta", nome: "Menta", tipo: "clara", cores: ["#edf6f2", "#ffffff", "#059669", "#2563eb", "#12302a"] },
  { id: "lavanda", nome: "Lavanda", tipo: "clara", cores: ["#f4f1fb", "#ffffff", "#7c3aed", "#db2777", "#241d3c"] },
  { id: "contraste", nome: "Alto contraste", tipo: "clara", cores: ["#ffffff", "#f4f4f4", "#0040c0", "#a1006b", "#000000"] },
];

function aplicarTema(id) {
  const t = PALETAS.some((p) => p.id === id) ? id : "marinho";
  if (t === "marinho") delete document.documentElement.dataset.tema;
  else document.documentElement.dataset.tema = t;
  try { localStorage.setItem("vc-tema", t); } catch (_) { /* navegador sem armazenamento */ }
}

function amostraPaleta(p, sel) {
  const [bg, pn, a1, a2, tx] = p.cores;
  return `<button type="button" class="paleta ${sel ? "sel" : ""}" data-tema="${p.id}" aria-pressed="${sel}" title="Usar a paleta ${esc(p.nome)}">
    <div class="amostra" style="background:${bg}">
      <div class="pn" style="background:${pn}"><div class="l" style="background:${tx};opacity:.85;width:70%"></div><div class="l" style="background:${tx};opacity:.4"></div><div class="bt" style="background:${a1}"></div></div>
      <div class="ac" style="background:${a2}"></div></div>
    <div class="nome-p">${esc(p.nome)}<small>${p.tipo === "clara" ? "☀ clara" : "☾ escura"}</small></div></button>`;
}

/* ---------------- utilitários ---------------- */

async function api(metodo, url, corpo, opcoes = {}) {
  const init = { method: metodo, headers: {} };
  if (corpo instanceof Blob || corpo instanceof ArrayBuffer) {
    init.body = corpo;
  } else if (corpo !== undefined) {
    init.headers["Content-Type"] = "application/json";
    init.body = JSON.stringify(corpo);
  }
  const r = await fetch(url, init);
  let dados = null;
  try { dados = await r.json(); } catch (_) { /* sem corpo */ }
  if (!r.ok) {
    const e = new Error((dados && dados.detail) || `Erro ${r.status}`);
    e.status = r.status;
    if (!opcoes.silencioso) toast(e.message, "erro");
    throw e;
  }
  return dados;
}

function toast(msg, tipo = "ok") {
  const el = document.createElement("div");
  el.className = `toast ${tipo}`;
  el.textContent = (tipo === "ok" ? "✓ " : "✕ ") + msg;
  $("#toast").appendChild(el);
  setTimeout(() => el.remove(), tipo === "ok" ? 3000 : 7000);
}

function modal({ titulo, html, botoes = [] }) {
  return new Promise((resolve) => {
    const fundo = document.createElement("div");
    fundo.className = "fundo-modal";
    fundo.innerHTML = `<div class="modal" role="dialog" aria-modal="true"><h2>${esc(titulo)}</h2><div>${html}</div>
      <div class="linha fim" style="margin-top:18px">${botoes.map((b, i) => `<button class="btn ${b.classe || ""}" data-i="${i}">${esc(b.texto)}</button>`).join("")}</div></div>`;
    document.body.appendChild(fundo);
    $$("button[data-i]", fundo).forEach((b) => b.addEventListener("click", () => {
      const bt = botoes[+b.dataset.i];
      const valor = bt.valor !== undefined ? bt.valor : bt.texto;
      const dados = Object.fromEntries($$("input,textarea,select", fundo).filter((x) => x.id).map((x) => [x.id, x.value]));
      fundo.remove();
      resolve({ valor, el: fundo, dados });
    }));
  });
}

async function confirmar(titulo, texto, ok = "Confirmar", classe = "prim") {
  const r = await modal({ titulo, html: `<p>${texto}</p>`, botoes: [{ texto: "Cancelar", valor: false }, { texto: ok, valor: true, classe }] });
  return r.valor === true;
}

const fmtT = (s) => {
  s = Math.max(0, +s || 0);
  const m = Math.floor(s / 60), r = s - m * 60;
  return `${m}:${r.toFixed(1).padStart(4, "0")}`;
};
const fmtDur = (s) => { s = Math.round(+s || 0); return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`; };
const usd = (v) => `US$ ${(+v || 0).toFixed(2).replace(".", ",")}`;
const dataBr = (s) => String(s || "").slice(0, 16).replace(/(\d+)-(\d+)-(\d+)/, "$3/$2/$1");
const adiar = (fn, ms = 600) => { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; };

const TAGS = {
  ok: (t) => `<span class="tag ok">✓ ${esc(t)}</span>`,
  aviso: (t) => `<span class="tag aviso">⚠ ${esc(t)}</span>`,
  erro: (t) => `<span class="tag erro">✕ ${esc(t)}</span>`,
  neutro: (t) => `<span class="tag neutro">○ ${esc(t)}</span>`,
  info: (t) => `<span class="tag info">● ${esc(t)}</span>`,
};

function tagSituacao(s) {
  return ({
    "bruto": TAGS.neutro("a configurar"), "roteiro pronto": TAGS.info("roteiro pronto"), "narrado": TAGS.info("pronto para revisar"),
    "aprovado": TAGS.ok("aprovado"), "gravando": TAGS.aviso("gravando"), "convertendo": TAGS.aviso("comprimindo"),
    "enviando": TAGS.aviso("enviando"), "erro": TAGS.erro("erro na conversão"),
  })[s] || TAGS.neutro(s || "?");
}

/* chave liga/desliga com rótulo de estado (nunca só cor) */
const chave = (id, rotulo, ligado, extra = "") =>
  `<label class="chave-linha" for="${id}"><input type="checkbox" class="chave" id="${id}" ${ligado ? "checked" : ""} ${extra}><span class="chave-estado" aria-hidden="true">${ligado ? "LIGA" : "DESL"}</span><span>${rotulo}</span></label>`;
document.addEventListener("change", (e) => {
  if (e.target.matches("input.chave")) {
    const st = e.target.nextElementSibling;
    if (st && st.classList.contains("chave-estado")) st.textContent = e.target.checked ? "LIGA" : "DESL";
  }
});

/* controle segmentado */
const segmentos = (nome, opcoes, atual) => `<div class="segmentos" role="radiogroup" data-seg="${nome}">${opcoes.map(([v, t, i]) =>
  `<button type="button" role="radio" aria-checked="${v === atual}" class="${v === atual ? "sel" : ""}" data-v="${esc(v)}">${i ? ic(i) : ""}${esc(t)}</button>`).join("")}</div>`;
function ligarSegmentos(el, nome, aoMudar) {
  const g = $(`[data-seg="${nome}"]`, el);
  if (!g) return;
  $$("button", g).forEach((b) => b.addEventListener("click", () => {
    $$("button", g).forEach((x) => { x.classList.toggle("sel", x === b); x.setAttribute("aria-checked", x === b); });
    aoMudar(b.dataset.v);
  }));
}
const valorSegmento = (el, nome) => { const b = $(`[data-seg="${nome}"] button.sel`, el); return b ? b.dataset.v : ""; };

/* ---------------- tarefas em segundo plano ---------------- */

const acompanhando = new Map();

function acompanhar(t, aoTerminar) {
  if (!t || !t.id || acompanhando.has(t.id)) return;
  const el = document.createElement("div");
  el.className = "tarefa";
  $("#tarefas").appendChild(el);
  acompanhando.set(t.id, el);
  const desenhar = (d) => {
    const indet = d.situacao === "rodando" && d.progresso < 0.02;
    const ico = d.situacao === "ok" ? "✓" : d.situacao === "erro" ? "✕" : "⏳";
    const rot = d.situacao === "ok" ? "concluída" : d.situacao === "erro" ? "com erro" : "em andamento";
    el.innerHTML = `<div class="tit">${ico} <span>${esc(nomeTarefa(d.tipo))}</span><span class="espaco"></span><span class="peq">${rot} · ${Math.round(d.duracao_s)} s</span></div>
      <div class="barra ${indet ? "indet" : ""}"><div style="width:${Math.round(d.progresso * 100)}%"></div></div>
      <div class="peq">${esc(d.situacao === "erro" ? d.erro : d.mensagem)}</div>
      ${d.situacao === "erro" ? `<div class="linha fim" style="margin-top:6px"><button class="btn peq">Fechar</button></div>` : ""}`;
    const b = $("button", el);
    if (b) b.onclick = () => el.remove();
  };
  desenhar(t);
  const ciclo = async () => {
    let d;
    try { d = await api("GET", `/api/tarefas/${t.id}`, undefined, { silencioso: true }); } catch (_) { setTimeout(ciclo, 2000); return; }
    desenhar(d);
    if (d.situacao === "rodando") { setTimeout(ciclo, 800); return; }
    acompanhando.delete(t.id);
    if (d.situacao === "ok") { setTimeout(() => el.remove(), 2500); toast(`${nomeTarefa(d.tipo)}: concluída`); }
    else toast(`${nomeTarefa(d.tipo)}: ${d.erro}`, "erro");
    if (aoTerminar) aoTerminar(d);
  };
  setTimeout(ciclo, 600);
}

function nomeTarefa(tipo) {
  return ({ converter: "Compressão do vídeo", roteiro: "Entendimento e roteiro", voz: "Geração da voz", "prévia de voz": "Prévia da voz",
    calibrar: "Calibração da voz", "vídeo completo": "Geração do vídeo completo", ajuste: "Ajuste e nova montagem", "download de música": "Download da música",
    "música gerada": "Composição da música", montagem: "Montagem do vídeo", "exportação": "Exportação" })[tipo] || tipo;
}

async function carregarConfig() {
  const d = await api("GET", "/api/config");
  ESTADO.cfg = d;
  return d;
}

async function carregarFinalidades() {
  if (!ESTADO.finalidades) ESTADO.finalidades = (await api("GET", "/api/finalidades")).finalidades;
  return ESTADO.finalidades;
}

function descVoz(cfgResp = ESTADO.cfg) {
  const v = cfgResp.config.voz;
  if (v.motor === "elevenlabs") return `ElevenLabs · ${v.elevenlabs.nome || "nenhuma voz escolhida"}`;
  if (v.motor === "kokoro") { const k = (cfgResp.vozes_kokoro || []).find((x) => x.id === (v.kokoro || {}).voz); return `Kokoro (offline) · ${k ? k.nome : (v.kokoro || {}).voz}`; }
  if (v.motor === "teste") return "Voz de teste (simulada)";
  const p = (cfgResp.vozes_piper || []).find((x) => x.id === v.piper.modelo);
  return `Piper (offline) · ${p ? p.nome : v.piper.modelo}`;
}
