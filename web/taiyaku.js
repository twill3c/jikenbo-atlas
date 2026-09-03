// 事件簿アトラス — 英日対訳ビュー(F-16)。
// data/taiyaku/{case_id}.json の rows(原文段落 en と訳文 ja)を対にして描く。
// 未訳段落は ja=null で届く。空欄で誤魔化さず「未訳」と出す。
const $ = (s) => document.querySelector(s);
const MODES = ["parallel", "alternate", "ja", "en"];
const MODE_LABEL = { parallel: "並列", alternate: "交互", ja: "訳のみ", en: "原文のみ" };

function esc(t) {
  const d = document.createElement("span");
  d.textContent = t;
  return d.innerHTML;
}

// 見出し段落(通番だけの行・全大文字の題名)は本文と区別して組む
function isHeading(row, i) {
  if (i > 2) return false;
  const s = row.en.trim();
  if (/^(chapter|part)?\s*[0-9IVXLC]+\.?$/i.test(s)) return true;
  return s === s.toUpperCase() && /[A-Z]{3}/.test(s) && s.length < 90;
}

function renderRows(rows, mode) {
  const out = [];
  rows.forEach((r, i) => {
    const head = isHeading(r, i);
    const en = `<div class="t-en">${esc(r.en)}</div>`;
    const ja = r.ja
      ? `<div class="t-ja">${esc(r.ja)}</div>`
      : `<div class="t-ja untranslated">（未訳）</div>`;
    const cls = `t-row${head ? " t-head" : ""}`;
    if (mode === "en") out.push(`<div class="${cls} m-en">${en}</div>`);
    else if (mode === "ja") out.push(`<div class="${cls} m-ja">${ja}</div>`);
    else if (mode === "alternate") out.push(`<div class="${cls} m-alt">${ja}${en}</div>`);
    else out.push(`<div class="${cls} m-par">${ja}${en}</div>`);
  });
  return out.join("\n");
}

function setMode(mode) {
  localStorage.setItem("taiyaku-mode", mode);
  document.querySelectorAll("#t-modes button").forEach((b) => {
    b.classList.toggle("on", b.dataset.mode === mode);
    b.setAttribute("aria-pressed", String(b.dataset.mode === mode));
  });
}

function readMode() {
  const q = new URLSearchParams(location.search).get("mode");
  if (MODES.includes(q)) return q;
  let saved = null;
  try {
    saved = localStorage.getItem("taiyaku-mode");
  } catch {
    saved = null;
  }
  return MODES.includes(saved) ? saved : "parallel";
}

async function main() {
  const cid = new URLSearchParams(location.search).get("c");
  if (!cid || !/^[0-9A-Z]{4}$/.test(cid)) {
    $("#t-title").textContent = "事件が指定されていません";
    return;
  }
  let d;
  try {
    d = await (await fetch(`data/taiyaku/${cid}.json`)).json();
  } catch {
    $("#t-title").textContent = "対訳を読み込めませんでした";
    return;
  }

  let index = null;
  try {
    index = (await (await fetch("data/index.json")).json()).cases.find((c) => c.id === cid);
  } catch {
    index = null;
  }
  const titleJa = index ? index.title_ja : d.title_en;
  document.title = `${titleJa} 対訳 — 事件簿アトラス`;
  $("#t-title").textContent = titleJa;
  $("#t-meta").textContent =
    `${d.title_en} / ${d.source.volume_title} / ${d.n_words.toLocaleString()} 語 ` +
    `/ ${d.n_paragraphs.toLocaleString()} 段落`;

  const pct = d.n_paragraphs ? (d.n_translated / d.n_paragraphs) * 100 : 0;
  const done = d.n_translated === d.n_paragraphs;
  $("#t-fill").innerHTML =
    `<span class="fill-bar"><i style="width:${pct.toFixed(1)}%"></i></span>` +
    `<span class="fill-num">和訳 ${d.n_translated.toLocaleString()} / ` +
    `${d.n_paragraphs.toLocaleString()} 段落（${pct.toFixed(1)}%）` +
    `${done ? "— 訳了" : "— 訳出中"}</span>`;

  let mode = readMode();
  const draw = () => {
    $("#taiyaku-body").className = `mode-${mode}`;
    $("#taiyaku-body").innerHTML = renderRows(d.rows, mode);
    setMode(mode);
  };
  document.querySelectorAll("#t-modes button").forEach((b) => {
    b.textContent = MODE_LABEL[b.dataset.mode];
    b.addEventListener("click", () => {
      mode = b.dataset.mode;
      draw();
    });
  });
  draw();

  const t = d.translation;
  $("#taiyaku-foot").innerHTML =
    `<p>原文: <a href="${esc(d.source.url)}">Project Gutenberg #${esc(d.source.ebook_id)} ` +
    `${esc(d.source.volume_title)}</a>（${esc(d.source.fetched_at)} 取得）。` +
    `アーサー・コナン・ドイル（1930 年没）の正典は保護期間が満了しており、PG 版は自由に再利用できる。</p>` +
    (t.translator
      ? `<p>和訳: ${esc(t.translator)}（${esc(t.model)}、${esc(t.translated_at)}）。` +
        `本サイトの新訳であり、既刊の日本語訳を参照・改変したものではない。</p>`
      : `<p>和訳: 未着手。</p>`);
}
main();
