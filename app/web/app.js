"use strict";
/* Video Composer · navegação e início. As telas ficam em js/*.js */

const NAV = [["videos", "Meus vídeos", "videos"]];
const NAV_RODAPE = [["config", "Configurações", "config"]];

function desenharNav() {
  $("#btn-novo").innerHTML = `${ic("mais")} Novo vídeo`;
  const link = ([k, t, i]) => `<a href="#/${k}" data-rota="${k}" title="${t}">${ic(i)}${t}</a>`;
  $("#nav").innerHTML = NAV.map(link).join("");
  $("#nav-rodape").innerHTML = NAV_RODAPE.map(link).join("");
}

/* rotas: [expressão, função(params, ...grupos)] */
const ROTAS = [
  [/^#\/videos$/, () => telaVideos()],
  [/^#\/novo$/, (q) => telaNovo(q)],
  [/^#\/video\/([\w-]+)$/, (q, id) => telaAbrirVideo(id)],
  [/^#\/video\/([\w-]+)\/configurar$/, (q, id) => telaConfigurar(id, q)],
  [/^#\/video\/([\w-]+)\/editor$/, (q, id) => telaEditor(id, q)],
  [/^#\/video\/([\w-]+)\/exportar$/, (q, id) => telaExportar(id)],
  [/^#\/video\/([\w-]+)\/roteiro$/, (q, id) => telaRoteiro(id)],
  [/^#\/video\/([\w-]+)\/voz$/, (q, id) => telaVoz(id)],
  [/^#\/video\/([\w-]+)\/ajustes$/, (q, id) => telaAjustes(id)],
  [/^#\/config$/, () => telaConfig()],
];

/* endereços da versão anterior continuam funcionando */
function rotaAntiga(h) {
  let m;
  if (h === "#/biblioteca" || h === "") return "#/videos";
  if (h === "#/gravar") return "#/novo";
  if ((m = h.match(/^#\/biblioteca\/([\w-]+)$/))) return `#/video/${m[1]}/ajustes`;
  if ((m = h.match(/^#\/projeto\/([\w-]+)\/(\w+)$/))) {
    const mapa = { briefing: "configurar", roteiro: "roteiro", voz: "voz", final: "editor", exportar: "exportar" };
    return `#/video/${m[1]}/${mapa[m[2]] || "configurar"}`;
  }
  return null;
}

async function rotear() {
  cancelAnimationFrame(EDITOR.raf);
  let h = location.hash || "#/videos";
  const antiga = rotaAntiga(h);
  if (antiga) { location.replace(antiga); return; }
  if (ESTADO.gravando && !h.startsWith("#/novo")) {
    location.hash = "#/novo";
    toast("Pare a gravação antes de sair desta tela", "erro");
    return;
  }
  const [caminho, busca] = h.split("?");
  const params = new URLSearchParams(busca || "");
  $$(".lateral .nav a").forEach((a) => a.classList.toggle("ativo",
    caminho === `#/${a.dataset.rota}` || (a.dataset.rota === "videos" && caminho.startsWith("#/video/"))));
  $("#btn-novo").classList.toggle("ativo", caminho === "#/novo");
  for (const [re, fn] of ROTAS) {
    const m = caminho.match(re);
    if (m) {
      try { await fn(params, ...m.slice(1)); } catch (e) { conteudo().innerHTML = `<div class="alerta erro">✕ ${esc(e.message)}</div><a class="btn" href="#/videos">${ic("esquerda")} Meus vídeos</a>`; }
      window.scrollTo(0, 0);
      return;
    }
  }
  location.replace("#/videos");
}
window.addEventListener("hashchange", rotear);

(async function iniciar() {
  desenharNav();
  try {
    const s = await api("GET", "/api/sistema", undefined, { silencioso: true });
    ESTADO.sistema = s;
    $("#rodape").innerHTML = `${esc(s.versao)}${s.modo_teste ? " · modo de teste" : ""} · ${s.livre_gb} GB livres`;
    const d = await carregarConfig();
    aplicarTema((d.config.aparencia || {}).tema);
    const { tarefas: ts } = await api("GET", "/api/tarefas", undefined, { silencioso: true });
    ts.filter((t) => t.situacao === "rodando").forEach((t) => acompanhar(t));
  } catch (_) { /* servidor iniciando */ }
  rotear();
})();
