// 事件簿アトラス — ロンドン事件地図(Leaflet)
// 配色は dataviz 検証済みの 2 系: 蘇芳=死者あり / 藍=死者なし。推定座標は白抜き二重丸。
const COLLECTIONS = [
  ["adventures", "冒険"], ["memoirs", "回想"], ["return", "生還"],
  ["his_last_bow", "最後の挨拶"], ["casebook", "事件簿"], ["novel", "長編"],
];
const TYPES = ["殺人", "盗難・強盗", "恐喝", "失踪・捜索", "詐欺・偽装", "機密・スパイ", "怪事件", "その他"];
const BAKER_221B = [51.5238, -0.1586];
const LONDON_VIEW = { center: [51.505, -0.11], zoom: 11 };
const WIDE_VIEW = { center: [52.0, -1.5], zoom: 6 };

const $ = (s) => document.querySelector(s);
let CASES = [], map, layer;

function css(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

function filtered() {
  const col = $("#f-col").value, ty = $("#f-type").value, de = $("#f-death").value;
  return CASES.filter((c) =>
    (!col || c.collection === col) &&
    (!ty || c.case_type === ty) &&
    (!de || (de === "yes") === c.deaths)
  );
}

function popupHtml(c) {
  const reader = c.works && c.works.some((w) => !w.external)
    ? `<a href="reader.html?w=${c.primary_work_id ?? c.works.find((w) => !w.external).work_id}">本文を読む →</a>`
    : "<span style='color:#999'>本文未収録</span>";
  return `<strong>${c.title_ja}</strong> <span class="en">${c.title_en}</span><br>` +
    `${c.site.label}${c.site.approx ? "(推定)" : ""}<br>` +
    `${c.pub_year}年 / ${c.case_type} / ${c.deaths ? "死者あり" : "死者なし"}<br>${reader}`;
}

function render() {
  const list = filtered();
  $("#f-count").textContent = `${list.length} / ${CASES.length} 件`;
  if (layer) layer.remove();
  layer = L.layerGroup();
  const cDeath = css("--accent"), cSafe = css("--accent-2"), paper = css("--card");
  for (const c of list) {
    const color = c.deaths ? cDeath : cSafe;
    const m = L.circleMarker([c.site.lat, c.site.lon], {
      radius: 7,
      color,
      weight: 2,
      fillColor: c.site.approx ? paper : color,
      fillOpacity: 1,
    });
    m.bindPopup(popupHtml(c));
    m.bindTooltip(`${c.title_ja}(${c.pub_year})`);
    layer.addLayer(m);
  }
  const home = L.marker(BAKER_221B, {
    icon: L.divIcon({ className: "", html: `<div style="font-size:20px;line-height:20px;color:${cDeath}">★</div>`, iconSize: [20, 20], iconAnchor: [10, 10] }),
    zIndexOffset: 1000,
  }).bindTooltip("ベーカー街221B");
  layer.addLayer(home);
  layer.addTo(map);
}

function renderLegend() {
  const lg = $("#legend");
  lg.innerHTML =
    `<span><i style="background:${css("--accent")}"></i>死者あり</span>` +
    `<span><i style="background:${css("--accent-2")}"></i>死者なし</span>` +
    `<span><i style="background:${css("--card")};border:2px solid ${css("--ink-3")}"></i>推定座標</span>`;
}

function setView() {
  const v = $("#f-london").checked ? LONDON_VIEW : WIDE_VIEW;
  map.setView(v.center, v.zoom);
}

function fillSelect(sel, label, opts) {
  const s = $(sel);
  s.append(new Option(`${label}: すべて`, ""));
  for (const [v, t] of opts) s.append(new Option(t, v));
}

async function main() {
  map = L.map("map", { scrollWheelZoom: true });
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 18,
    attribution: "&copy; OpenStreetMap contributors",
  }).addTo(map);
  const idx = await (await fetch("data/index.json")).json();
  CASES = idx.cases;
  fillSelect("#f-col", "短編集", COLLECTIONS);
  fillSelect("#f-type", "種別", TYPES.map((t) => [t, t]));
  for (const s of ["#f-col", "#f-type", "#f-death"]) $(s).addEventListener("change", render);
  $("#f-london").addEventListener("change", setView);
  renderLegend();
  setView();
  render();
}
main();
