// 全境封锁2 掉落站 —— 纯静态，无框架
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

// ---------- 主题 ----------
const savedTheme = localStorage.getItem("td2.theme");
if (savedTheme) document.documentElement.dataset.theme = savedTheme;
else if (matchMedia("(prefers-color-scheme: dark)").matches) document.documentElement.dataset.theme = "dark";

function initTheme() {
  const btn = $("#btn-theme");
  if (!btn) return;
  const sync = () => { btn.textContent = document.documentElement.dataset.theme === "dark" ? "☀" : "☾"; };
  sync();
  btn.onclick = () => {
    const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    localStorage.setItem("td2.theme", next);
    sync();
  };
}

// ---------- 时间 ----------
const BEIJING_OFFSET = 8 * 3600 * 1000;
function beijingNow() { const n = new Date(); return new Date(n.getTime() + (n.getTimezoneOffset() * 60000) + BEIJING_OFFSET); }
function nextReset() {
  const bj = beijingNow();
  const r = new Date(bj); r.setHours(16, 0, 0, 0);
  if (bj >= r) r.setDate(r.getDate() + 1);
  return r;
}
function tickClock() {
  const bj = beijingNow();
  const pad = (n) => String(n).padStart(2, "0");
  const el1 = $("#clock-bj"); if (el1) el1.textContent = pad(bj.getMonth() + 1) + "-" + pad(bj.getDate()) + " " + pad(bj.getHours()) + ":" + pad(bj.getMinutes());
  const el2 = $("#countdown");
  if (el2) {
    const ms = nextReset() - bj;
    const h = Math.floor(ms / 3600000), m = Math.floor((ms % 3600000) / 60000), s = Math.floor((ms % 60000) / 1000);
    el2.textContent = pad(h) + ":" + pad(m) + ":" + pad(s);
  }
}

// ---------- 数据 ----------
async function getJSON(url) {
  const r = await fetch(url, { cache: "no-cache" });
  if (!r.ok) throw new Error(url + " " + r.status);
  return r.json();
}
function agoText(iso) {
  if (!iso) return "未知";
  const d = new Date(iso + "T00:00:00+08:00");
  const days = Math.round((beijingNow() - d) / 86400000);
  if (days <= 0) return "今天";
  if (days === 1) return "昨天";
  return days + " 天前";
}
function lootCell(r) {
  if (!r.loot_cn) return '<span style="color:var(--bad)">' + esc(r.loot_en) + "（待补全）</span>";
  const name = esc(r.loot_cn).replace(/※$/, "");
  return name + (r.uncertain ? '<span class="cat" title="译名待确认">※</span>' : "");
}
function iconTag(r, size) {
  if (!r.icon) return "";
  return '<img class="ico" loading="lazy" alt="" src="' + esc(r.icon) + '">';
}
function missionCard(m) {
  const cat = { brand: "品牌", set: "套装", slot: "部位", unknown: "未分类" }[m.category] || "";
  return '<div class="card item">' + iconTag(m) +
    '<div class="body">' +
      '<div class="row1">' +
        (m.priority ? '<span class="pri" title="重点">★</span>' : "") +
        '<span class="mission">' + esc(m.mission_cn || m.mission) + "</span>" +
        (m.faction_cn ? '<span class="faction">' + esc(m.faction_cn) + "</span>" : "") +
      "</div>" +
      '<div class="loot">' + lootCell(m) + '<span class="cat">' + esc(cat) + "</span></div>" +
      '<div class="meta">出现 ' + (m.appearances ?? "-") + " 次 · 上次 " + agoText(m.last_seen) +
        (m.last_seen ? "（" + esc(m.last_seen) + "）" : "") + "</div>" +
    "</div>" +
  "</div>";
}
function cacheCard(c) {
  const cat = { brand: "品牌", set: "套装", slot: "部位", unknown: "未分类" }[c.category] || "";
  return '<div class="card item">' + iconTag(c) +
    '<div class="body">' +
      '<div class="row1"><span class="mission">' + esc(c.name_cn || c.name) + "</span></div>" +
      '<div class="loot">' + lootCell(c) + '<span class="cat">' + esc(cat) + "</span></div>" +
      '<div class="meta">出现 ' + (c.appearances ?? "-") + " 次 · 上次 " + agoText(c.last_seen) + "</div>" +
    "</div>" +
  "</div>";
}

// ---------- 今日 ----------
async function initToday() {
  const box = $("#today");
  try {
    const idx = await getJSON("data/index.json");
    if (!idx.latest) { box.innerHTML = '<p class="empty">还没有任何数据。</p>'; return; }
    const d = await getJSON("data/" + idx.latest + ".json");
    const pill = $("#pill-date"); if (pill) pill.textContent = d.date;
    const du = $("#data-updated"); if (du) du.textContent = d.updated || "-";
    const banners = [];
    if (d.unknown_names && d.unknown_names.length)
      banners.push('<div class="banner warn">有 ' + d.unknown_names.length + " 个名字没有中文：" + esc(d.unknown_names.join("、")) + "。改 scripts/names.json 后推送即可。</div>");
    $("#banners").innerHTML = banners.join("");
    box.innerHTML = d.missions.map(missionCard).join("");
    $("#caches").innerHTML = d.caches.map(cacheCard).join("");
  } catch (e) {
    box.innerHTML = '<div class="banner bad">加载失败：' + esc(e.message) + "。可能是数据还没生成，稍后再试。</div>";
  }
}

// ---------- 历史 ----------
async function initHistory() {
  const idx = await getJSON("data/index.json");
  const list = $("#dates");
  const view = $("#day-view");
  if (!idx.dates.length) { list.innerHTML = '<p class="empty">暂无历史</p>'; return; }
  list.innerHTML = idx.dates.map((d, i) => '<button data-d="' + d + '" class="' + (i === 0 ? "on" : "") + '">' + d.slice(5) + "</button>").join("");
  async function show(date) {
    $$("#dates button").forEach((b) => b.classList.toggle("on", b.dataset.d === date));
    const d = await getJSON("data/" + date + ".json");
    view.innerHTML = '<h2>' + d.date + '</h2>' + d.missions.map(missionCard).join("") +
      (d.caches.length ? "<h2>每日缓存</h2>" + d.caches.map(cacheCard).join("") : "");
  }
  list.onclick = (e) => { const b = e.target.closest("button"); if (b) show(b.dataset.d); };
  show(idx.dates[0]);
}

// ---------- 查询 ----------
async function initItem() {
  const data = await getJSON("data/items.json");
  const items = data.items || [];
  const input = $("#q"), out = $("#results");
  function render(kw) {
    kw = (kw || "").trim().toLowerCase();
    const hit = items.filter((it) => !kw || (it.loot_cn || "").toLowerCase().includes(kw) || (it.loot_en || "").toLowerCase().includes(kw));
    if (!hit.length) { out.innerHTML = '<p class="empty">没有匹配的掉落</p>'; return; }
    out.innerHTML = hit.slice(0, 60).map((it, i) =>
      '<div class="card"><div class="item-row" data-i="' + i + '">' + iconTag(it) +
        '<div class="n"><div class="loot" style="margin:0">' + (it.loot_cn ? esc(it.loot_cn) : '<span style="color:var(--bad)">' + esc(it.loot_en) + "</span>") +
        '</div><div class="c">' + esc(it.loot_en) + " · 出现 " + it.dates.length + " 天</div></div>" +
        '<div class="c">' + (it.dates.length ? it.dates[it.dates.length - 1].date.slice(5) : "") + "</div>" +
      "</div><div class='dates hidden'>" + it.dates.map((x) => "<span>" + x.date.slice(5) + "</span>").join("") + "</div></div>"
    ).join("");
    $$(".item-row", out).forEach((row) => row.onclick = () => row.parentElement.querySelector(".dates").classList.toggle("hidden"));
  }
  input.oninput = (e) => render(e.target.value);
  render("");
}

// ---------- 调试：?debug=1 显示视口与文档宽度 ----------
function debugBox() {
  if (!location.search.includes("debug")) return;
  const d = document.createElement("div");
  d.style.cssText = "position:fixed;left:0;bottom:0;z-index:99;background:#000;color:#0f0;font:12px monospace;padding:4px 8px";
  const upd = () => { d.textContent = "vw=" + innerWidth + " doc=" + document.documentElement.scrollWidth + " body=" + document.body.scrollWidth; };
  upd(); document.body.appendChild(d); addEventListener("resize", upd);
}

// ---------- 启动 ----------
document.addEventListener("DOMContentLoaded", () => {
  initTheme();
  debugBox();
  tickClock();
  setInterval(tickClock, 1000);
  const page = document.body.dataset.page;
  if (page === "today") initToday();
  if (page === "history") initHistory();
  if (page === "item") initItem();
});
