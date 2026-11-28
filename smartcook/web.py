"""Web 入口:零依赖 http.server,单页 + JSON API。

启动:`python -m smartcook web --port 8000`,浏览器打开 http://127.0.0.1:8000
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from . import agent, llm, recipes
from . import db as dbmod

# 冷蓝为主 + 单一暖橙点缀(契合项目审美:清爽、圆润、温柔)。
PAGE = """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>食光 · 用现有食材做一顿饭</title>
<style>
  :root {
    --bg:#f4f7fb; --card:#ffffff; --ink:#1f2937; --muted:#6b7280;
    --blue:#2563eb; --blue-soft:#dbeafe; --amber:#f59e0b; --amber-soft:#fef3c7;
    --line:#e5e7eb; --radius:16px;
  }
  * { box-sizing:border-box; }
  body { margin:0; font-family:system-ui,-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;
         background:var(--bg); color:var(--ink); }
  .wrap { max-width:860px; margin:0 auto; padding:32px 20px 80px; }
  header h1 { font-size:26px; margin:0 0 4px; letter-spacing:.5px; }
  header p { color:var(--muted); margin:0 0 24px; }
  .badge { display:inline-block; font-size:12px; padding:3px 10px; border-radius:999px;
           background:var(--blue-soft); color:var(--blue); margin-left:8px; vertical-align:2px; }
  .tabs { display:flex; gap:8px; margin-bottom:20px; flex-wrap:wrap; }
  .tab { padding:9px 18px; border-radius:999px; border:1px solid var(--line);
         background:var(--card); cursor:pointer; font-size:14px; color:var(--muted); }
  .tab.active { background:var(--blue); color:#fff; border-color:var(--blue); }
  .card { background:var(--card); border:1px solid var(--line); border-radius:var(--radius);
          padding:20px; margin-bottom:20px; box-shadow:0 1px 2px rgba(16,24,40,.04); }
  label { display:block; font-size:13px; color:var(--muted); margin:0 0 6px; }
  textarea, input[type=text] { width:100%; padding:12px 14px; border:1px solid var(--line);
          border-radius:12px; font-size:15px; font-family:inherit; resize:vertical; }
  textarea:focus, input:focus { outline:none; border-color:var(--blue);
          box-shadow:0 0 0 3px var(--blue-soft); }
  .row { display:flex; gap:12px; align-items:flex-end; }
  .row > div { flex:1; }
  button { background:var(--blue); color:#fff; border:none; padding:12px 22px; border-radius:12px;
           font-size:15px; cursor:pointer; white-space:nowrap; }
  button:hover { filter:brightness(1.06); }
  button.warm { background:var(--amber); color:#1f2937; }
  .hint { color:var(--muted); font-size:12px; margin-top:8px; }
  .result { display:none; }
  .result.show { display:block; }
  .dish { border:1px solid var(--line); border-radius:14px; padding:14px 16px; margin-bottom:12px; }
  .dish h4 { margin:0 0 6px; font-size:16px; }
  .pill { display:inline-block; font-size:12px; padding:2px 8px; border-radius:6px;
          background:var(--amber-soft); color:#92400e; margin-right:6px; }
  .pill.miss { background:#fee2e2; color:#b91c1c; }
  .pill.have { background:#dcfce7; color:#15803d; }
  .meta { color:var(--muted); font-size:13px; margin:4px 0 10px; }
  ol { margin:8px 0; padding-left:20px; } li { margin:4px 0; line-height:1.6; }
  .tag { font-size:12px; color:var(--muted); margin-top:8px; }
  .verdict { font-size:18px; font-weight:600; margin:6px 0 10px; }
  .spin { display:inline-block; width:16px; height:16px; border:2px solid #fff;
          border-top-color:transparent; border-radius:50%; animation:sp .7s linear infinite; }
  @keyframes sp { to { transform:rotate(360deg); } }

h1{font-size:clamp(31px,5vw,39px);line-height:1.26}
.prod{display:block;font-size:11px;line-height:1.4;letter-spacing:.18em;font-weight:650;margin-bottom:8px;opacity:.72}
.lede,.sub{max-width:62ch;line-height:1.75}
.route{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1px;margin:0 0 20px;border:1px solid var(--line);background:var(--line)}
.route span{padding:11px 13px;background:var(--card);font-size:12px;line-height:1.5}
.route b{display:block;font-size:10px;letter-spacing:.1em;margin-bottom:3px;opacity:.66}
button{min-height:46px}
input,select{min-height:44px}
@media(max-width:680px){
  .wrap{padding:20px 16px 56px}
  .route{grid-template-columns:1fr}
  h1{font-size:30px!important}
  .row>div{min-width:100%!important}
  button{width:100%}
}

body{background:#f7f1e5;color:#27231e;font-family:"PingFang SC","Microsoft YaHei",sans-serif}
.wrap{max-width:920px}
header{padding:8px 0 20px;border-bottom:4px solid #d24b33;margin-bottom:22px}
header h1{font-size:39px;line-height:1.25;letter-spacing:-.03em;font-weight:800}
header p{color:#6d6155;font-size:14px}
.card{background:#fffdf7;border:1px solid #e1d2bc;border-radius:8px;box-shadow:0 2px 0 #eadcc8}
button{background:#d24b33;border-radius:8px;font-size:15px;font-weight:700;letter-spacing:.04em}
button:hover{background:#bb3e28}
textarea,input,select{background:#fffefb;border-color:#decdb6;border-radius:8px}
textarea:focus,input:focus,select:focus{border-color:#d24b33;box-shadow:0 0 0 3px #f1d8cf}
.item{border-left:4px solid #d24b33;padding-left:14px}
h3{color:#a33c29;letter-spacing:.07em}


/* palette-normalized */
:root{--bg:#f7f1e5;--card:#fffdf7;--ink:#27231e;--text:#27231e;--dim:#6d6155;--line:#e1d2bc;--accent:#d24b33}

/* polish-batch1 */
button.ghost,button.secondary{background:transparent!important;color:#d24b33!important;border:1px solid #e1d2bc!important}

/* mobile-32 */

@media(max-width:760px){
  main{grid-template-columns:1fr!important}
  aside{border-right:0!important;border-bottom:1px solid #e1d2bc;width:auto!important}
  section{padding:16px!important}
  .row{flex-wrap:wrap!important}
  .row>div{min-width:100%!important}
  h1{font-size:30px!important}
  .route{grid-template-columns:1fr!important}
  button{min-height:48px}
  pre{overflow-x:auto}
}

/* mobile-height */
@media(max-width:760px){main{min-height:auto!important}aside{min-height:0!important}}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1><span class="prod">食光</span>用现有食材，做一顿饭 <span class="badge" id="status-badge">…</span></h1>
    <p class="lede">给下班后做两菜一汤的人：先说有啥、几人吃、还剩多久和过敏项，再把菜排成共用锅具和灶眼的顺序。</p>
  </header>
  <div class="route" aria-label="任务步骤"><span><b>01</b>报食材和时间</span><span><b>02</b>排锅具与灶眼</span><span><b>03</b>照着步骤做完</span></div>


  <div class="tabs">
    <div class="tab active" data-tab="suggest">🍳 推荐</div>
    <div class="tab" data-tab="cook">🍽 做法</div>
    <div class="tab" data-tab="swap">🔄 替代</div>
    <div class="tab" data-tab="diet">🥗 忌口</div>
  </div>

  <div class="card" id="pane-suggest">
    <label>家里有什么食材?(自然语言即可)</label>
    <textarea id="sug-ing" rows="3" placeholder="例:家里有半颗白菜、两个番茄、一点肉末和几个鸡蛋"></textarea>
    <div class="hint">支持口语化描述,模型会自动理解并整理成规范食材。</div>
    <div style="margin-top:12px"><button id="btn-suggest">开始推荐</button></div>
    <div class="result" id="res-suggest"></div>
  </div>

  <div class="card" id="pane-cook" style="display:none">
    <div class="row">
      <div><label>菜名</label><input type="text" id="cook-name" placeholder="例:番茄炒蛋"></div>
      <div><label>忌口(可选)</label><input type="text" id="cook-diet" placeholder="例:不吃辣"></div>
    </div>
    <div class="hint" style="margin:8px 0 12px">做法由模型生成,可结合忌口个性化调整。</div>
    <button id="btn-cook">生成做法</button>
    <div class="result" id="res-cook"></div>
  </div>

  <div class="card" id="pane-swap" style="display:none">
    <label>缺什么食材?</label>
    <input type="text" id="swap-ing" placeholder="例:香醋">
    <div style="margin-top:12px"><button id="btn-swap" class="warm">找替代品</button></div>
    <div class="result" id="res-swap"></div>
  </div>

  <div class="card" id="pane-diet" style="display:none">
    <div class="row">
      <div><label>菜名</label><input type="text" id="diet-dish" placeholder="例:宫保鸡丁"></div>
      <div><label>忌口/要求</label><input type="text" id="diet-rest" placeholder="例:花生过敏"></div>
    </div>
    <div style="margin-top:12px"><button id="btn-diet">判断</button></div>
    <div class="result" id="res-diet"></div>
  </div>
</div>

<script>
const $ = s => document.querySelector(s);
function esc(s){return String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));}

document.querySelectorAll('.tab').forEach(t=>t.onclick=()=>{
  document.querySelectorAll('.tab').forEach(x=>x.classList.remove('active'));
  t.classList.add('active');
  ['suggest','cook','swap','diet'].forEach(k=>$('#pane-'+k).style.display = k===t.dataset.tab?'':'none');
});

async function post(path, body){
  const r = await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  return r.json();
}
function btnLoading(btn,on){ btn.disabled=on; if(on){ btn.dataset.label=btn.dataset.label||btn.textContent.trim(); btn.innerHTML='<span class="spin"></span>'; } else { btn.innerHTML=btn.dataset.label||btn.textContent; } }

function renderIng(i){ return typeof i==='object' ? esc(i.name)+(i.amount?' '+esc(i.amount):'') : esc(i); }

$('#btn-suggest').onclick=async()=>{
  const el=$('#res-suggest'); el.classList.remove('show');
  btnLoading($('#btn-suggest'),true);
  try{
    const r = await post('/api/suggest',{ingredients:$('#sug-ing').value});
    let h = '<p style="color:var(--muted)">识别食材:'+(r.ingredients.length?r.ingredients.map(esc).join('、'):'—')+'</p>';
    if(!r.dishes.length){ h+='<p>没匹配到合适的菜,换个说法或补充食材试试。</p>'; }
    r.dishes.forEach(d=>{
      h+='<div class="dish"><h4>'+esc(d.name)+'</h4>';
      if(d.match) h+='<span class="pill have">已有:'+esc(d.match)+'</span>';
      (d.missing||[]).forEach(m=>h+='<span class="pill miss">缺 '+esc(m)+'</span>');
      if(d.reason) h+='<div class="tag">'+esc(d.reason)+'</div>';
      h+='</div>';
    });
    el.innerHTML=h;
  }catch(e){ el.innerHTML='<p style="color:#b91c1c">请求失败:'+esc(e)+'</p>'; }
  el.classList.add('show'); btnLoading($('#btn-suggest'),false);
};

$('#btn-cook').onclick=async()=>{
  const el=$('#res-cook'); el.classList.remove('show');
  btnLoading($('#btn-cook'),true);
  try{
    const r = await post('/api/cook',{name:$('#cook-name').value,diet:$('#cook-diet').value});
    let h = '<div class="dish"><h4>'+esc(r.name)+'</h4>';
    let meta=[r.time_minutes?r.time_minutes+' 分钟':'',r.difficulty?'难度 '+esc(r.difficulty):'',r.servings?esc(r.servings):''].filter(Boolean);
    if(meta.length) h+='<div class="meta">'+meta.join(' · ')+'</div>';
    if(r.ingredients&&r.ingredients.length) h+='<div><b>食材</b>:'+r.ingredients.map(renderIng).join('、')+'</div>';
    if(r.steps&&r.steps.length){ h+='<ol>'; r.steps.forEach(s=>h+='<li>'+esc(s)+'</li>'); h+='</ol>'; }
    if(r.tips&&r.tips.length){ h+='<div class="tag">贴士:'+r.tips.map(esc).join(';')+'</div>'; }
    h+='</div>';
    el.innerHTML=h;
  }catch(e){ el.innerHTML='<p style="color:#b91c1c">请求失败:'+esc(e)+'</p>'; }
  el.classList.add('show'); btnLoading($('#btn-cook'),false);
};

$('#btn-swap').onclick=async()=>{
  const el=$('#res-swap'); el.classList.remove('show');
  btnLoading($('#btn-swap'),true);
  try{
    const r = await post('/api/swap',{ingredient:$('#swap-ing').value});
    let h='<div class="dish"><h4>「'+esc(r.original)+'」的替代</h4>';
    r.substitutes.forEach((s,i)=>h+='<li>'+esc(s.name)+(s.note?' —— '+esc(s.note):'')+'</li>');
    h+='</div>';
    el.innerHTML=h;
  }catch(e){ el.innerHTML='<p style="color:#b91c1c">请求失败:'+esc(e)+'</p>'; }
  el.classList.add('show'); btnLoading($('#btn-swap'),false);
};

$('#btn-diet').onclick=async()=>{
  const el=$('#res-diet'); el.classList.remove('show');
  btnLoading($('#btn-diet'),true);
  try{
    const r = await post('/api/diet',{dish:$('#diet-dish').value,restrictions:$('#diet-rest').value});
    let h='<div class="dish"><h4>'+esc(r.dish)+'</h4><div class="verdict">'+esc(r.verdict)+'</div>';
    if(r.reasons&&r.reasons.length) h+='<div><b>原因</b>:<ul>'+r.reasons.map(x=>'<li>'+esc(x)+'</li>').join('')+'</ul></div>';
    if(r.adjustments&&r.adjustments.length) h+='<div><b>建议</b>:<ul>'+r.adjustments.map(x=>'<li>'+esc(x)+'</li>').join('')+'</ul></div>';
    h+='</div>';
    el.innerHTML=h;
  }catch(e){ el.innerHTML='<p style="color:#b91c1c">请求失败:'+esc(e)+'</p>'; }
  el.classList.add('show'); btnLoading($('#btn-diet'),false);
};

fetch('/api/status').then(r=>r.json()).then(s=>{
  const b=$('#status-badge');
  if(s.mock){ b.textContent='离线模式'; b.style.background='#fee2e2'; b.style.color='#b91c1c'; }
  else{ b.textContent=s.model||'模型已连接'; b.style.background='#dcfce7'; b.style.color='#15803d'; }
}).catch(()=>{});
</script>
</body>
</html>
"""


def _make_handler(db, cfg, force_mock):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, body: bytes, ctype: str, status: int = 200):
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _json(self, obj, status: int = 200):
            self._send(json.dumps(obj, ensure_ascii=False).encode("utf-8"),
                       "application/json; charset=utf-8", status)

        def _read_json(self):
            n = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(n)
            # 浏览器/JSON 默认 UTF-8;兼容部分 Windows 客户端按本地码页(GBK)发送的情况
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                text = raw.decode("gbk", errors="replace")
            return json.loads(text) if text else {}

        def do_GET(self):
            path = urlparse(self.path).path
            if path in ("/", "/index.html"):
                self._send(PAGE.encode("utf-8"), "text/html; charset=utf-8")
            elif path == "/api/status":
                mock_mode = force_mock or not cfg.get("api_key")
                self._json({"mock": mock_mode, "model": None if mock_mode else cfg.get("model"),
                            "recipes": len(db.all_recipes())})
            elif path == "/api/recipes":
                self._json(db.all_recipes())
            else:
                self._json({"error": "not found"}, 404)

        def do_POST(self):
            path = urlparse(self.path).path
            try:
                body = self._read_json()
                if path == "/api/suggest":
                    self._json(agent.suggest(body.get("ingredients", ""), config=cfg, db=db, force_mock=force_mock))
                elif path == "/api/cook":
                    self._json(agent.cook(body.get("name", ""), config=cfg, db=db,
                                          diet=body.get("diet"), on_hand=body.get("on_hand"),
                                          force_mock=force_mock))
                elif path == "/api/swap":
                    self._json(agent.swap(body.get("ingredient", ""), config=cfg, force_mock=force_mock))
                elif path == "/api/diet":
                    self._json(agent.diet(body.get("dish", ""), body.get("restrictions", ""),
                                          config=cfg, db=db, force_mock=force_mock))
                else:
                    self._json({"error": "not found"}, 404)
            except llm.LLMError as e:
                self._json({"error": str(e)}, 400)
            except Exception as e:  # noqa: BLE001
                self._json({"error": str(e)}, 500)

        def log_message(self, *args):  # 静默默认日志
            pass

    return Handler


def serve(host: str = "127.0.0.1", port: int = 8000, db_path: str | None = None, force_mock: bool = False):
    db = dbmod.Database(db_path)
    recipes.ensure_seeded(db)
    cfg = llm.config_from_args(None) if False else llm.default_config()

    handler = _make_handler(db, cfg, force_mock)
    httpd = ThreadingHTTPServer((host, port), handler)
    mode = "离线模式(未配置 key)" if (force_mock or not cfg.get("api_key")) else f"模型:{cfg.get('model')}"
    print(f"🍳 食光已启动:http://{host}:{port}  [{mode}]")
    print("   按 Ctrl+C 停止")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
