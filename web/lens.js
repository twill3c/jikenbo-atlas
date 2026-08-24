// 事件簿アトラス — 人物ネットワーク+文体レンズ
const $ = (s) => document.querySelector(s);
const css = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();

function bindTip(node, text) {
  node.addEventListener("mousemove", (ev) => {
    const t = $("#tip");
    t.style.display = "block";
    t.textContent = text;
    t.style.left = Math.min(ev.clientX + 14, innerWidth - 270) + "px";
    t.style.top = (ev.clientY + 14) + "px";
  });
  node.addEventListener("mouseleave", () => { $("#tip").style.display = "none"; });
}

function renderNetwork(net, caseTitle, primaryOf) {
  const W = $("#network").clientWidth || 1000, H = 560;
  const charNodes = net.chars.map((c) => ({ id: "c:" + c.name, label: c.name, kind: "char", deg: c.cases }));
  const caseIds = [...new Set(net.edges.map((e) => e.case_id))];
  const caseNodes = caseIds.map((k) => ({ id: "k:" + k, label: caseTitle[k] || k, kind: "case", key: k }));
  const nodes = [...charNodes, ...caseNodes];
  const links = net.edges.map((e) => ({ source: "c:" + e.char, target: "k:" + e.case_id, count: e.count }));

  const svg = d3.select("#network").append("svg").attr("viewBox", `0 0 ${W} ${H}`);
  const sim = d3.forceSimulation(nodes)
    .force("link", d3.forceLink(links).id((d) => d.id).distance(95).strength((l) => Math.min(0.7, l.count / 60 + 0.1)))
    .force("charge", d3.forceManyBody().strength(-340))
    .force("center", d3.forceCenter(W / 2, H / 2))
    .force("collide", d3.forceCollide(30));

  const link = svg.append("g").selectAll("line").data(links).join("line")
    .attr("stroke", css("--line")).attr("stroke-width", (l) => Math.min(6, 0.8 + Math.log2(l.count)));

  const node = svg.append("g").selectAll("g").data(nodes).join("g").style("cursor", (d) => d.kind === "case" ? "pointer" : "default");
  node.append("circle")
    .attr("r", (d) => d.kind === "char" ? 9 + Math.min(9, d.deg) : 7)
    .attr("fill", (d) => d.kind === "char" ? css("--accent") : css("--card"))
    .attr("stroke", (d) => d.kind === "char" ? "none" : css("--accent-2"))
    .attr("stroke-width", 2);
  node.append("text")
    .text((d) => d.label)
    .attr("font-size", (d) => d.kind === "char" ? 13 : 11)
    .attr("dx", 12).attr("dy", 4)
    .attr("fill", css("--ink"));
  node.filter((d) => d.kind === "case").on("click", (_ev, d) => {
    const wid = primaryOf[d.key];
    if (wid) location.href = `reader.html?w=${wid}`;
  });
  node.each(function (d) {
    bindTip(this, d.kind === "char" ? `${d.label} — ${d.deg} 事件に登場(実測)` : `${d.label} — クリックで本文へ`);
  });
  node.call(d3.drag()
    .on("start", (ev, d) => { if (!ev.active) sim.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
    .on("drag", (ev, d) => { d.fx = ev.x; d.fy = ev.y; })
    .on("end", (ev, d) => { if (!ev.active) sim.alphaTarget(0); d.fx = null; d.fy = null; }));

  sim.on("tick", () => {
    for (const n of nodes) {
      n.x = Math.max(30, Math.min(W - 30, n.x));
      n.y = Math.max(20, Math.min(H - 20, n.y));
    }
    link.attr("x1", (l) => l.source.x).attr("y1", (l) => l.source.y)
      .attr("x2", (l) => l.target.x).attr("y2", (l) => l.target.y);
    node.attr("transform", (d) => `translate(${d.x},${d.y})`);
  });
}

function pctBar(container, label, ratio, max, color, tipText) {
  const row = document.createElement("div");
  row.className = "bar-row";
  const lbl = document.createElement("span");
  lbl.className = "lbl"; lbl.textContent = label;
  const track = document.createElement("div");
  track.className = "bar-track";
  const bar = document.createElement("div");
  bar.className = "bar";
  bar.style.background = color;
  bar.style.width = (ratio / max * 100) + "%";
  const val = document.createElement("span");
  val.className = "bar-val"; val.textContent = (ratio * 100).toFixed(1) + "%";
  track.append(bar, val);
  bindTip(track, tipText);
  row.append(lbl, track);
  container.append(row);
}

function renderRatios(worksMap) {
  const box = $("#ratios");
  const rows = Object.values(worksMap).sort((a, b) => b.quote_ratio - a.quote_ratio);
  const max = Math.max(...rows.map((r) => r.quote_ratio));
  for (const r of rows) {
    pctBar(box, r.title, r.quote_ratio, max, css("--accent"),
      `${r.title}(${r.translators.join("・")}訳): 台詞 ${(r.quote_ratio * 100).toFixed(1)}% / ${r.chars.toLocaleString()} 字`);
  }
}

function renderPairs(pairs, caseTitle) {
  const box = $("#pairs");
  const colors = [css("--accent-2"), css("--accent")];
  for (const p of pairs) {
    const div = document.createElement("div");
    div.className = "pair";
    const h = document.createElement("h4");
    h.textContent = `${caseTitle[p.case_id] || p.case_id}(${p.case_id})`;
    div.append(h);
    const max = Math.max(...p.works.map((w) => w.quote_ratio));
    p.works.forEach((w, i) => {
      const row = document.createElement("div");
      row.className = "row";
      const lbl = document.createElement("span");
      lbl.className = "lbl";
      lbl.textContent = `${w.translators.join("・")}訳「${w.title}」`;
      const track = document.createElement("div");
      track.className = "bar-track";
      const bar = document.createElement("div");
      bar.className = "bar";
      bar.style.background = colors[i % 2];
      bar.style.width = (w.quote_ratio / max * 100) + "%";
      const val = document.createElement("span");
      val.className = "bar-val";
      val.textContent = `台詞 ${(w.quote_ratio * 100).toFixed(1)}%`;
      track.append(bar, val);
      bindTip(track, `${w.title}: ${w.chars.toLocaleString()} 字 / ルビ ${w.ruby_per_1000}/千字`);
      row.append(lbl, track);
      div.append(row);
      const meta = document.createElement("div");
      meta.className = "meta";
      meta.style.marginLeft = "11.5em";
      meta.textContent = `${w.chars.toLocaleString()} 字 ・ ルビ ${w.ruby_per_1000}/千字`;
      div.append(meta);
    });
    box.append(div);
  }
}

async function main() {
  const [analysis, idx] = await Promise.all([
    (await fetch("data/analysis.json")).json(),
    (await fetch("data/index.json")).json(),
  ]);
  const caseTitle = {}, primaryOf = {};
  for (const c of idx.cases) {
    caseTitle[c.id] = c.title_ja;
    const w = c.works && c.works.find((x) => !x.external);
    if (w) primaryOf[c.id] = c.primary_work_id ?? w.work_id;
  }
  renderNetwork(analysis.network, caseTitle, primaryOf);
  renderRatios(analysis.works);
  renderPairs(analysis.pairs, caseTitle);
}
main();
