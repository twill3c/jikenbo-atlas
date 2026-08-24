// 事件簿アトラス — リーダー。data/stories/{work_id}.json のセグメント列を描画する。
// 注記(［＃…］)の扱いは実測方針(SPEC F-06): 挿絵=プレースホルダ、傍点=圏点、
// 見出し/字下げ/地付き/改ページ対応、その他は非表示(title で原文保持)。
const $ = (s) => document.querySelector(s);

function esc(t) {
  const d = document.createElement("span");
  d.textContent = t;
  return d.innerHTML;
}

function applyBoten(html, target) {
  // 直前テキストのうち target と一致する末尾側の並びに圏点を付す
  const i = html.lastIndexOf(esc(target));
  if (i < 0) return html;
  return html.slice(0, i) + `<span class="em-dots">${esc(target)}</span>` + html.slice(i + esc(target).length);
}

function renderLine(segs) {
  let html = "";
  let cls = [];
  let tag = "p";
  let sashie = null;
  for (const seg of segs) {
    const [kind, a, b, explicit] = seg;
    if (kind === "text") {
      html += esc(a);
    } else if (kind === "ruby") {
      html += `<ruby>${esc(a)}<rt>${esc(b)}</rt></ruby>`;
    } else {
      const n = a; // note 原文 ［＃…］
      let m;
      if ((m = n.match(/^［＃挿絵|^［＃図|^［＃紙/))) {
        sashie = n;
      } else if (n.match(/^［＃ここから[0-9０-９]+字下げ/)) {
        cls.push("indent");
      } else if (n === "［＃ここで字下げ終わり］") {
        // ブロック終端 — 行単位描画では開始行のみ字下げ(簡易)
      } else if ((m = n.match(/^［＃「(.+?)」に傍点］$/))) {
        html = applyBoten(html, m[1]);
      } else if (n.match(/は中見出し］$|は大見出し］$/)) {
        tag = "h2"; cls.push("mid");
      } else if (n === "［＃改ページ］" || n === "［＃改丁］") {
        return `<hr class="pagebreak">`;
      } else if (n.match(/^［＃地付き］|^［＃地から/)) {
        cls.push("right");
      } else if (n.match(/^［＃[0-9０-９]+字下げ］/)) {
        cls.push("indent");
      } else {
        html += `<span hidden title="${esc(n)}"></span>`;
      }
    }
  }
  if (sashie) {
    return `<div class="sashie" title="${esc(sashie)}">〔挿絵〕</div>` + (html ? `<${tag} class="${cls.join(" ")}">${html}</${tag}>` : "");
  }
  if (!html) return "<p>&nbsp;</p>";
  return `<${tag} class="${cls.join(" ")}">${html}</${tag}>`;
}

async function main() {
  const wid = new URLSearchParams(location.search).get("w");
  if (!wid || !/^\d+$/.test(wid)) { $("#r-title").textContent = "作品が指定されていません"; return; }
  const pad = String(wid).padStart(5, "0");
  let story;
  try {
    story = await (await fetch(`data/stories/${pad}.json`)).json();
  } catch {
    $("#r-title").textContent = "本文を読み込めませんでした";
    return;
  }
  document.title = `${story.title} — 事件簿アトラス`;
  $("#r-title").textContent = story.title;
  $("#r-meta").textContent =
    `${story.translators.join("・")} 訳 / 約${story.reading_minutes}分(${story.chars.toLocaleString()}字) / 事件 ${story.case_id}`;
  const frag = story.body.map(renderLine).join("\n");
  $("#reader-body").innerHTML = frag;
  $("#reader-foot").textContent =
    story.footer.filter((l) => l).join("\n") +
    `\n\n出典: ${story.source.card_url}(${story.source.fetched_at} 取得)`;
}
main();
