// 事件簿アトラス — 事件簿(ダッシュボード)ビュー
const COLLECTIONS = [
  ["adventures", "冒険"], ["memoirs", "回想"], ["return", "生還"],
  ["his_last_bow", "最後の挨拶"], ["casebook", "事件簿"], ["novel", "長編"],
];
const COL_LABEL = Object.fromEntries(COLLECTIONS);
const TYPES = ["殺人", "盗難・強盗", "恐喝", "失踪・捜索", "詐欺・偽装", "機密・スパイ", "怪事件", "その他"];
const REGIONS = ["ロンドン", "ロンドン近郊", "地方", "海外"];

let CASES = [];

const $ = (s) => document.querySelector(s);
const el = (tag, cls, text) => {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined) e.textContent = text;
  return e;
};

const tip = () => $("#tip");
function bindTip(node, text) {
  node.addEventListener("mousemove", (ev) => {
    const t = tip();
    t.style.display = "block";
    t.textContent = text;
    t.style.left = Math.min(ev.clientX + 14, innerWidth - 270) + "px";
    t.style.top = (ev.clientY + 14) + "px";
  });
  node.addEventListener("mouseleave", () => { tip().style.display = "none"; });
}

function readable(c) {
  return c.works.some((w) => !w.external);
}
function readingMin(c) {
  const w = c.works.find((x) => x.work_id === c.primary_work_id) || c.works.find((x) => !x.external);
  return w && w.reading_minutes ? w.reading_minutes : null;
}

function filtered() {
  const col = $("#f-col").value, ty = $("#f-type").value, rg = $("#f-region").value;
  const de = $("#f-death").value, tx = $("#f-text").value, q = $("#f-q").value.trim();
  return CASES.filter((c) =>
    (!col || c.collection === col) &&
    (!ty || c.case_type === ty) &&
    (!rg || c.region === rg) &&
    (!de || (de === "yes") === c.deaths) &&
    (!tx || (tx === "yes") === readable(c)) &&
    (!q || c.title_ja.includes(q) || c.title_en.toLowerCase().includes(q.toLowerCase()) || c.id.toLowerCase() === q.toLowerCase())
  );
}

function renderStats(stats) {
  const box = $("#stats");
  box.replaceChildren();
  const items = [
    [stats.n_cases, "正典の事件(短編56+長編4)"],
    [stats.n_texts, "青空文庫で読める本文"],
    [stats.n_no_death_shorts + " / " + stats.n_shorts, "死者の出ない短編"],
    ["1887–1927", "発表年の幅"],
  ];
  for (const [num, lbl] of items) {
    const t = el("div", "tile");
    t.append(el("div", "num", String(num)), el("div", "lbl", lbl));
    box.append(t);
  }
}

function barRow(label, total, max, tipText) {
  const row = el("div", "bar-row");
  row.append(el("span", "lbl", label));
  const track = el("div", "bar-track");
  const bar = el("div", "bar");
  bar.style.width = (total / max * 100) + "%";
  track.append(bar, el("span", "bar-val", String(total)));
  bindTip(track, tipText);
  row.append(track);
  return row;
}

function renderCharts(list) {
  const box = $("#charts");
  box.replaceChildren();

  // 図1: 事件種別の件数(単色=量の比較)
  const c1 = el("div", "chart");
  c1.append(el("h3", null, "事件種別ごとの件数"));
  const counts = TYPES.map((t) => [t, list.filter((c) => c.case_type === t).length]);
  const max1 = Math.max(1, ...counts.map(([, n]) => n));
  for (const [t, n] of counts) c1.append(barRow(t, n, max1, `${t}: ${n} 件`));
  box.append(c1);

  // 図2: 短編集ごとの本文充足(藍=本文あり/残余=非強調)
  const c2 = el("div", "chart");
  c2.append(el("h3", null, "短編集ごとの本文充足(青空文庫)"));
  const lg = el("div", "legend");
  const l1 = el("span"); const i1 = el("i"); i1.style.background = "var(--accent-2)";
  l1.append(i1, document.createTextNode("本文あり"));
  const l2 = el("span"); const i2 = el("i"); i2.style.background = "var(--remain)";
  l2.append(i2, document.createTextNode("本文なし"));
  lg.append(l1, l2);
  c2.append(lg);
  const max2 = Math.max(...COLLECTIONS.map(([k]) => list.filter((c) => c.collection === k).length), 1);
  for (const [key, label] of COLLECTIONS) {
    const grp = list.filter((c) => c.collection === key);
    if (!grp.length) { c2.append(barRow(label, 0, max2, `${label}: 0 件`)); continue; }
    const has = grp.filter(readable).length;
    const row = el("div", "bar-row");
    row.append(el("span", "lbl", label));
    const track = el("div", "bar-track");
    if (has) {
      const b = el("div", "bar b2");
      b.style.width = (has / max2 * 100) + "%";
      if (has === grp.length) b.style.borderRadius = "0 4px 4px 0";
      track.append(b);
    }
    if (grp.length - has) {
      const r = el("div", "bar rem");
      r.style.width = ((grp.length - has) / max2 * 100) + "%";
      track.append(r);
    }
    track.append(el("span", "bar-val", `${has}/${grp.length}`));
    bindTip(track, `${label}: 全 ${grp.length} 件中、本文あり ${has} 件`);
    row.append(track);
    c2.append(row);
  }
  box.append(c2);
}

function renderList(list) {
  const box = $("#case-list");
  box.replaceChildren();
  $("#f-count").textContent = `${list.length} / ${CASES.length} 件`;
  for (const c of list) {
    const card = el("article", "case");
    const ttl = el("span", "ttl", c.title_ja);
    const en = el("span", "en", c.title_en);
    card.append(ttl, en);
    if (readable(c)) {
      const wid = c.primary_work_id ?? c.works.find((w) => !w.external).work_id;
      const min = readingMin(c);
      const a = el("a", "read");
      a.href = `reader.html?w=${wid}`;
      a.textContent = `読む${min ? `(約${min}分)` : ""} →`;
      card.append(a);
    } else if (c.pg) {
      // 青空文庫に本文が無い事件は PG 原文の自前和訳へ(F-16)。
      // 充填率をその場に出す — 訳了かどうかを開く前に分かるようにする
      const a = el("a", "read");
      a.href = `taiyaku.html?c=${c.id}`;
      const done = c.pg.n_translated === c.pg.n_paragraphs;
      const pct = Math.round((c.pg.n_translated / c.pg.n_paragraphs) * 100);
      a.textContent = done ? "対訳で読む →" : `対訳(和訳 ${pct}%) →`;
      if (!done) a.classList.add("partial");
      card.append(a);
    } else {
      card.append(el("span", "noread", "本文未収録"));
    }
    const meta = el("div", "meta");
    meta.append(
      el("span", "chip", COL_LABEL[c.collection] + (c.is_novel ? "" : "集")),
      el("span", "chip", String(c.pub_year)),
      el("span", "chip", c.case_type),
      el("span", "chip", c.region),
    );
    if (c.deaths) meta.append(el("span", "chip death", "死者あり"));
    const who = el("span", null, `依頼: ${c.client} / 動機: ${c.motive}`);
    who.style.color = "var(--ink-3)";
    meta.append(who);
    card.append(meta);
    box.append(card);
  }
}

function rerender() {
  const list = filtered();
  renderCharts(list);
  renderList(list);
}

function fillSelect(sel, label, opts) {
  const s = $(sel);
  s.append(new Option(`${label}: すべて`, ""));
  for (const [v, t] of opts) s.append(new Option(t, v));
}

async function main() {
  const idx = await (await fetch("data/index.json")).json();
  CASES = idx.cases;
  CASES.sort((a, b) => a.pub_year - b.pub_year || a.id.localeCompare(b.id));
  renderStats(idx.stats);
  fillSelect("#f-col", "短編集", COLLECTIONS.map(([k, v]) => [k, v]));
  fillSelect("#f-type", "種別", TYPES.map((t) => [t, t]));
  fillSelect("#f-region", "舞台", REGIONS.map((r) => [r, r]));
  for (const s of ["#f-col", "#f-type", "#f-region", "#f-death", "#f-text"])
    $(s).addEventListener("change", rerender);
  $("#f-q").addEventListener("input", rerender);
  rerender();
}
main();
