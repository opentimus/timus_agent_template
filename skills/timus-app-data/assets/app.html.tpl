<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
  :root{
    --bg:#141517; --surface:#1c1e21; --surface2:#23262a; --border:#34383e;
    --text:#e8eaed; --muted:#9aa0a8; --hint:#6f757d;
    --accent:#5b9dff; --accent-soft:#1e3354; --ok:#3ecf8e; --warn:#f0b35a; --err:#ff6b6b;
    --radius:10px;
  }
  @media (prefers-color-scheme: light){:root{
    --bg:#f6f7f9; --surface:#fff; --surface2:#f0f2f5; --border:#e3e6eb;
    --text:#1a1d21; --muted:#61676f; --hint:#8a919b; --accent:#2f6bf6; --accent-soft:#eaf1ff;
    --ok:#12805c; --warn:#b7791f; --err:#c0392b;
  }}
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;font-size:14px;line-height:1.6}
  .wrap{max-width:1280px;margin:0 auto;padding:28px 22px 150px}
  h1{font-size:20px;font-weight:600;margin:0 0 4px}
  h2{font-size:15px;font-weight:600;margin:0 0 10px}
  .sub{color:var(--muted);font-size:13px;margin:0}
  .badges{display:flex;gap:8px;flex-wrap:wrap;margin:16px 0 18px}
  .badge{background:var(--surface2);border:1px solid var(--border);border-radius:999px;padding:5px 12px;font-size:12px;color:var(--muted)}
  .badge b{color:var(--text);font-weight:600}
  .badge.ok b{color:var(--ok)}
  .card{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:16px 18px;margin-bottom:18px}
  .hint{font-size:12px;color:var(--hint)}
  .tblwrap{overflow:auto}
  table{width:100%;border-collapse:collapse;min-width:640px}
  th,td{border:1px solid var(--border);padding:8px 9px;text-align:left;vertical-align:top;font-size:13px}
  th{background:var(--surface2);color:var(--muted);font-weight:600;white-space:nowrap}
  td input[type=text]{width:100%;background:var(--surface2);border:1px solid var(--border);border-radius:6px;color:var(--text);padding:7px 8px;font-size:13px;font-family:inherit;outline:none}
  td input:focus{border-color:var(--accent);box-shadow:0 0 0 2px var(--accent-soft)}
  .col-idx{width:44px;text-align:center}
  .src{font-size:11px;color:var(--hint);max-width:220px;word-break:break-word}
  button{cursor:pointer;font-family:inherit;font-size:13px;border-radius:8px;padding:9px 16px;border:1px solid var(--border);background:var(--surface2);color:var(--text);transition:.12s}
  button:hover{border-color:var(--muted)}
  button.primary{background:var(--accent);border-color:var(--accent);color:#0b1626;font-weight:600}
  button.primary:hover{filter:brightness(1.08)}
  button.ghost{background:transparent}
  button:disabled{opacity:.45;cursor:not-allowed}
  .bar{position:fixed;left:0;right:0;bottom:0;background:var(--surface);border-top:1px solid var(--border);padding:12px 22px;display:flex;gap:12px;align-items:center;justify-content:center;flex-wrap:wrap;z-index:10}
  .bar .summary{font-size:13px;color:var(--muted)}
  .bar .summary b{color:var(--text)}
  .hidden{display:none}
  .ro-note{font-size:12px;color:var(--hint);margin-top:10px}
  .pill{display:inline-block;font-size:11px;color:var(--muted);background:var(--surface2);border:1px solid var(--border);border-radius:999px;padding:1px 7px;margin-left:6px}
  pre{background:var(--surface2);border:1px solid var(--border);border-radius:8px;padding:12px;overflow:auto;font-size:12px;line-height:1.6;max-height:300px}
</style>
</head>
<body>
<div class="wrap">
  <h1 id="pageTitle"></h1>
  <p class="sub" id="pageSub"></p>
  <div class="badges" id="badges"></div>

  <div class="card">
    <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:12px">
      <h2 id="tableTitle" style="margin:0"></h2>
      <span class="hint" id="tableHint"></span>
    </div>
    <div class="tblwrap">
      <table>
        <thead id="thead"></thead>
        <tbody id="tbody"></tbody>
      </table>
    </div>
    <div class="ro-note" id="note"></div>
  </div>

  <div class="card hidden" id="exportCard">
    <h2>导出</h2>
    <pre id="exportPre"></pre>
  </div>
</div>

<div class="bar">
  <span class="summary" id="barSummary"></span>
  <button class="primary" id="btnExport">导出待提交数据</button>
  <button class="ghost" id="btnClose">关闭</button>
</div>

<script>
const DATA = __DATA_JSON__;
const $ = id => document.getElementById(id);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const COLS = Array.isArray(DATA.columns) ? DATA.columns : [];
let rows = Array.isArray(DATA.rows) ? DATA.rows.map(r => ({...r})) : [];

function render() {
  $("pageTitle").textContent = DATA.title || "数据页面";
  $("pageSub").textContent = DATA.subtitle || "";
  $("badges").innerHTML = (DATA.badges || []).map(b => '<span class="badge' + (b.ok ? " ok" : "") + '">' + esc(b.label) + ' <b>' + esc(b.value) + '</b></span>').join("");
  $("tableTitle").textContent = DATA.tableTitle || "";
  $("tableHint").textContent = DATA.tableHint || "";
  $("note").textContent = DATA.note || "";
  $("thead").innerHTML = "<tr>" + COLS.map(c => "<th>" + esc(c.label || c.key) + "</th>").join("") + "</tr>";
  $("tbody").innerHTML = rows.length ? rows.map((row, i) =>
    '<tr><td class="col-idx">' + (i + 1) + "</td>" + COLS.map(c => {
      const value = row[c.key] ?? "";
      return DATA.editable
        ? '<td><input type="text" data-i="' + i + '" data-k="' + esc(c.key) + '" value="' + esc(value) + '"></td>'
        : '<td class="' + esc(c.className || "") + '">' + esc(value || "—") + "</td>";
    }).join("") + "</tr>"
  ).join("") : '<tr><td colspan="' + (COLS.length + 1) + '" style="text-align:center;color:var(--hint);padding:30px">暂无数据</td></tr>';
  $("barSummary").innerHTML = "共 <b>" + rows.length + "</b> 条" + (DATA.editable ? " · 可直接编辑" : "");
  $("btnExport").disabled = rows.length === 0;
}

function payload() {
  return {title: DATA.title || "数据页面", columns: COLS.map(c => ({key: c.key, label: c.label || c.key})), rows};
}

function exportJson() {
  $("exportPre").textContent = JSON.stringify(payload(), null, 2);
  $("exportCard").classList.remove("hidden");
  $("exportCard").scrollIntoView({behavior: "smooth"});
}

$("tbody").addEventListener("input", event => {
  const input = event.target.closest("input[data-i]");
  if (!input) return;
  rows[+input.dataset.i][input.dataset.k] = input.value;
});
$("btnExport").onclick = () => {
  exportJson();
  $("barSummary").textContent = "以下为待提交数据（未写入平台），写入须由助手调用连接器 MCP";
};
$("btnClose").onclick = () => { window.close(); $("barSummary").textContent = "请在宿主窗口中关闭本页"; };
render();
</script>
</body>
</html>
