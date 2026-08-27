"""Dashboard stylesheet and client-side script, inlined into the HTML output.

Kept in its own module so :mod:`render.html` stays about structure and content.
Nothing here loads from the network: the dashboard is one file that works from
a local disk, an intranet share, or GitHub Pages, identically.
"""

CSS = """
:root{
  --bg:#07080c; --bg-soft:#0c0e15; --panel:#101320; --panel-2:#141828;
  --line:#1e2334; --line-soft:#181c2b;
  --text:#e8ebf5; --muted:#8b93a8; --dim:#5b6478;
  --accent:#14f195; --accent-2:#9945ff; --info:#38bdf8;
  --warn:#f59e0b; --crit:#fb5f6d; --ok:#14f195;
  --mono:ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,"Liberation Mono",monospace;
  --sans:-apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Roboto,"Helvetica Neue",Arial,sans-serif;
  --radius:14px;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth;scroll-padding-top:86px}
body{
  margin:0;background:var(--bg);color:var(--text);font-family:var(--sans);
  font-size:14.5px;line-height:1.55;-webkit-font-smoothing:antialiased;
  background-image:
    radial-gradient(900px 500px at 12% -8%,rgba(153,69,255,.16),transparent 60%),
    radial-gradient(800px 460px at 92% -12%,rgba(20,241,149,.11),transparent 62%);
  background-attachment:fixed;
}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline}
.wrap{max-width:1280px;margin:0 auto;padding:0 20px 80px}

/* ---------- top bar ---------- */
header.top{
  position:sticky;top:0;z-index:50;backdrop-filter:blur(14px);
  background:rgba(7,8,12,.82);border-bottom:1px solid var(--line);
}
.top-inner{max-width:1280px;margin:0 auto;padding:11px 20px;display:flex;
  align-items:center;gap:18px;flex-wrap:wrap}
.brand{display:flex;align-items:center;gap:10px;font-weight:650;letter-spacing:-.2px;font-size:16px}
.brand .mark{width:26px;height:26px;border-radius:8px;
  background:linear-gradient(135deg,var(--accent-2),var(--accent));
  display:grid;place-items:center;font-size:13px;color:#07080c;font-weight:800}
.pulse-dot{width:8px;height:8px;border-radius:50%;background:var(--ok);
  box-shadow:0 0 0 0 rgba(20,241,149,.6);animation:pulse 2.4s infinite}
@keyframes pulse{0%{box-shadow:0 0 0 0 rgba(20,241,149,.55)}70%{box-shadow:0 0 0 9px rgba(20,241,149,0)}100%{box-shadow:0 0 0 0 rgba(20,241,149,0)}}
nav.jump{display:flex;gap:2px;flex-wrap:wrap;margin-left:auto}
nav.jump a{color:var(--muted);font-size:12.5px;padding:5px 9px;border-radius:8px}
nav.jump a:hover{color:var(--text);background:var(--panel);text-decoration:none}
.top-meta{font-family:var(--mono);font-size:11.5px;color:var(--dim);display:flex;
  align-items:center;gap:8px}

/* ---------- hero ---------- */
.hero{padding:34px 0 22px}
.hero h1{font-size:30px;line-height:1.15;margin:0 0 8px;letter-spacing:-.7px;font-weight:680}
.hero h1 span{background:linear-gradient(96deg,var(--accent),var(--accent-2));
  -webkit-background-clip:text;background-clip:text;color:transparent}
.hero p{margin:0;color:var(--muted);max-width:74ch}
.chips{display:flex;gap:8px;flex-wrap:wrap;margin-top:16px}
.chip{font-family:var(--mono);font-size:11.5px;color:var(--muted);border:1px solid var(--line);
  background:var(--panel);padding:5px 10px;border-radius:999px;display:flex;align-items:center;gap:7px}
.chip b{color:var(--text);font-weight:600}
.chip.ok b{color:var(--ok)} .chip.warn b{color:var(--warn)} .chip.crit b{color:var(--crit)}

/* ---------- kpis ---------- */
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(196px,1fr));gap:12px;margin:8px 0 26px}
.kpi{background:linear-gradient(180deg,var(--panel),var(--bg-soft));border:1px solid var(--line);
  border-radius:var(--radius);padding:14px 15px 10px;position:relative;overflow:hidden;
  transition:border-color .18s ease,transform .18s ease}
.kpi:hover{border-color:#2b3245;transform:translateY(-1px)}
.kpi .k{font-size:11.5px;color:var(--muted);text-transform:uppercase;letter-spacing:.06em;
  display:flex;align-items:center;justify-content:space-between;gap:6px}
.kpi .v{font-family:var(--mono);font-size:24px;font-weight:620;margin-top:5px;letter-spacing:-.6px}
.kpi .s{font-size:12px;color:var(--dim);margin-top:2px;min-height:17px}
.kpi .spark{width:100%;height:34px;display:block;margin-top:6px;opacity:.9}
.up{color:var(--ok)} .down{color:var(--crit)} .flat{color:var(--muted)}

/* ---------- sections & cards ---------- */
section{margin:38px 0 0}
.sec-head{display:flex;align-items:baseline;gap:12px;margin:0 0 14px;flex-wrap:wrap}
.sec-head h2{font-size:19px;margin:0;letter-spacing:-.3px;font-weight:640}
.sec-head .n{font-family:var(--mono);font-size:11px;color:var(--accent-2);border:1px solid #2a2140;
  background:rgba(153,69,255,.10);padding:2px 7px;border-radius:6px}
.sec-head p{margin:0;color:var(--muted);font-size:13px}
.grid{display:grid;gap:14px}
.g2{grid-template-columns:repeat(2,minmax(0,1fr))}
.g3{grid-template-columns:repeat(3,minmax(0,1fr))}
@media(max-width:940px){.g2,.g3{grid-template-columns:1fr}}
.card{background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);
  padding:16px 17px;min-width:0}
.card h3{margin:0 0 3px;font-size:13.5px;font-weight:620;letter-spacing:-.1px}
.card .sub{color:var(--dim);font-size:12px;margin:0 0 12px}
.card.span2{grid-column:1 / -1}

/* ---------- stat lists ---------- */
.stats{list-style:none;margin:0;padding:0}
.stats li{display:flex;justify-content:space-between;gap:14px;padding:7px 0;
  border-bottom:1px solid var(--line-soft);font-size:13px}
.stats li:last-child{border-bottom:0}
.stats .k{color:var(--muted);min-width:0}
.stats .v{font-family:var(--mono);font-weight:560;text-align:right;white-space:nowrap}

/* ---------- tables ---------- */
.tbl-wrap{overflow-x:auto;margin:0 -4px}
table{width:100%;border-collapse:collapse;font-size:12.8px}
th{text-align:left;color:var(--muted);font-weight:560;font-size:11.5px;text-transform:uppercase;
  letter-spacing:.05em;padding:8px 10px;border-bottom:1px solid var(--line);
  position:sticky;top:0;background:var(--panel);white-space:nowrap}
td{padding:7px 10px;border-bottom:1px solid var(--line-soft);white-space:nowrap}
tbody tr:hover{background:var(--panel-2)}
td.num,th.num{text-align:right;font-family:var(--mono)}
.mono{font-family:var(--mono)}
.scroll-y{max-height:430px;overflow-y:auto}
.pill{font-size:10.5px;padding:2px 7px;border-radius:999px;border:1px solid var(--line);
  color:var(--muted);font-family:var(--mono)}
.pill.ok{color:var(--ok);border-color:#14502f;background:rgba(20,241,149,.08)}
.pill.bad{color:var(--crit);border-color:#5a2029;background:rgba(251,95,109,.09)}
.pill.warn{color:var(--warn);border-color:#5a4212;background:rgba(245,158,11,.09)}
.pill.info{color:var(--info);border-color:#17415e;background:rgba(56,189,248,.09)}

/* ---------- alerts ---------- */
.alerts{display:grid;gap:10px}
.alert{display:flex;gap:12px;padding:13px 15px;border-radius:12px;border:1px solid var(--line);
  background:var(--panel);border-left-width:3px}
.alert.critical{border-left-color:var(--crit);background:linear-gradient(90deg,rgba(251,95,109,.09),var(--panel) 42%)}
.alert.warning{border-left-color:var(--warn);background:linear-gradient(90deg,rgba(245,158,11,.08),var(--panel) 42%)}
.alert.info{border-left-color:var(--info);background:linear-gradient(90deg,rgba(56,189,248,.07),var(--panel) 42%)}
.alert .body{min-width:0}
.alert .t{font-weight:620;font-size:13.5px;display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.alert .d{color:var(--muted);font-size:12.8px;margin-top:3px}
.alert .icon{font-size:15px;line-height:1.3}
.quiet{border:1px dashed var(--line);border-radius:12px;padding:18px;color:var(--muted);
  text-align:center;background:var(--bg-soft)}
.quiet b{color:var(--ok)}

/* ---------- charts ---------- */
svg.chart{width:100%;height:auto;display:block}
.chart-empty{color:var(--dim);font-size:12.5px;padding:22px;text-align:center;
  border:1px dashed var(--line);border-radius:10px}
.donut-wrap{display:flex;gap:16px;align-items:center;flex-wrap:wrap}
.legend{list-style:none;margin:0;padding:0;flex:1;min-width:150px}
.legend li{display:flex;align-items:center;gap:8px;font-size:12.3px;padding:2.5px 0}
.legend .dot{width:9px;height:9px;border-radius:3px;flex:none}
.legend .k{color:var(--muted);flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.legend .v{font-family:var(--mono);font-size:11.5px}
.gauge{position:relative;height:26px;border-radius:8px;background:var(--panel-2);
  border:1px solid var(--line);overflow:hidden}
.gauge-fill{height:100%;background:linear-gradient(90deg,var(--accent-2),var(--accent));opacity:.55}
.gauge-text{position:absolute;inset:0;display:grid;place-items:center;font-family:var(--mono);
  font-size:12px;font-weight:600}

/* ---------- controls ---------- */
.controls{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:11px;align-items:center}
input[type=search],select{background:var(--bg-soft);border:1px solid var(--line);color:var(--text);
  border-radius:9px;padding:7px 11px;font-size:12.8px;font-family:var(--sans);outline:none}
input[type=search]{min-width:230px}
input[type=search]:focus,select:focus{border-color:var(--accent-2)}
.count{font-family:var(--mono);font-size:11.5px;color:var(--dim);margin-left:auto}
button.ghost{background:var(--bg-soft);border:1px solid var(--line);color:var(--muted);
  border-radius:9px;padding:7px 11px;font-size:12.5px;cursor:pointer}
button.ghost:hover{color:var(--text);border-color:#2b3245}
button.ghost[aria-pressed=true]{color:var(--accent);border-color:#14502f;background:rgba(20,241,149,.08)}

/* ---------- news ---------- */
.news{list-style:none;margin:0;padding:0;max-height:430px;overflow-y:auto}
.news li{padding:10px 0;border-bottom:1px solid var(--line-soft)}
.news li:last-child{border-bottom:0}
.news .meta{font-family:var(--mono);font-size:11px;color:var(--dim);display:flex;gap:8px;margin-bottom:3px}
.news .ttl{font-size:13.2px;font-weight:560;line-height:1.4}
.news .sum{color:var(--muted);font-size:12.2px;margin-top:3px}

/* ---------- misc ---------- */
.note{color:var(--dim);font-size:12px;margin-top:10px;line-height:1.5}
.degraded{border:1px solid #5a2029;background:rgba(251,95,109,.07);border-radius:10px;
  padding:11px 13px;color:#ffb3b9;font-size:12.6px;margin-bottom:12px;font-family:var(--mono)}
footer{margin-top:52px;padding-top:22px;border-top:1px solid var(--line);color:var(--dim);
  font-size:12.3px;display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap}
details.method{border:1px solid var(--line);border-radius:12px;background:var(--panel);padding:0}
details.method>summary{cursor:pointer;padding:13px 16px;font-weight:600;font-size:13.5px;list-style:none}
details.method>summary::-webkit-details-marker{display:none}
details.method>summary::before{content:"▸ ";color:var(--accent-2)}
details.method[open]>summary::before{content:"▾ "}
details.method .inner{padding:0 16px 16px;color:var(--muted);font-size:13px}
details.method h4{color:var(--text);margin:14px 0 5px;font-size:13px}
details.method code{font-family:var(--mono);font-size:11.8px;background:var(--bg-soft);
  border:1px solid var(--line);border-radius:5px;padding:1px 5px;color:var(--accent)}
@media(max-width:640px){
  .hero h1{font-size:23px}
  nav.jump{display:none}
  .top-inner{gap:10px}
}
"""

SCRIPT = """
(function(){
  var raw=document.getElementById('pulse-data');
  var DATA=raw?JSON.parse(raw.textContent):{validators:[]};

  /* Validator table: search, sort, delinquent-only filter, incremental render. */
  var rows=DATA.validators||[];
  var body=document.getElementById('vrows');
  var search=document.getElementById('vsearch');
  var sortSel=document.getElementById('vsort');
  var delinqBtn=document.getElementById('vdelinq');
  var counter=document.getElementById('vcount');
  var PAGE=60, shown=PAGE, delinqOnly=false;

  function fmtSol(v){
    if(v>=1e6) return (v/1e6).toFixed(2)+'M';
    if(v>=1e3) return (v/1e3).toFixed(1)+'K';
    return v.toFixed(0);
  }
  function filtered(){
    var q=(search&&search.value||'').trim().toLowerCase();
    var out=rows.filter(function(r){
      if(delinqOnly&&!r.d) return false;
      if(!q) return true;
      return (r.v&&r.v.toLowerCase().indexOf(q)>=0)||(r.n&&r.n.toLowerCase().indexOf(q)>=0);
    });
    var mode=sortSel?sortSel.value:'stake';
    if(mode==='commission') out.sort(function(a,b){return (a.c-b.c)||(b.s-a.s);});
    else if(mode==='commission_desc') out.sort(function(a,b){return (b.c-a.c)||(b.s-a.s);});
    else if(mode==='stake_asc') out.sort(function(a,b){return a.s-b.s;});
    else out.sort(function(a,b){return b.s-a.s;});
    return out;
  }
  function render(){
    if(!body) return;
    var list=filtered(), slice=list.slice(0,shown), html='';
    for(var i=0;i<slice.length;i++){
      var r=slice[i];
      html+='<tr><td class="num">'+r.r+'</td>'
        +'<td class="mono">'+r.v.slice(0,8)+'…'+r.v.slice(-6)+'</td>'
        +'<td class="mono">'+(r.n?r.n.slice(0,6)+'…':'—')+'</td>'
        +'<td class="num">'+fmtSol(r.s)+'</td>'
        +'<td class="num">'+r.p.toFixed(3)+'%</td>'
        +'<td class="num">'+r.c+'%</td>'
        +'<td><span class="pill '+(r.d?'bad':'ok')+'">'+(r.d?'delinquent':'active')+'</span></td></tr>';
    }
    body.innerHTML=html||'<tr><td colspan="7" style="color:var(--dim);padding:18px">No validators match.</td></tr>';
    if(counter) counter.textContent='showing '+slice.length+' of '+list.length+' validators';
    var more=document.getElementById('vmore');
    if(more) more.style.display=(slice.length<list.length)?'inline-block':'none';
  }
  if(search) search.addEventListener('input',function(){shown=PAGE;render();});
  if(sortSel) sortSel.addEventListener('change',function(){shown=PAGE;render();});
  if(delinqBtn) delinqBtn.addEventListener('click',function(){
    delinqOnly=!delinqOnly; delinqBtn.setAttribute('aria-pressed',delinqOnly?'true':'false');
    shown=PAGE; render();
  });
  var more=document.getElementById('vmore');
  if(more) more.addEventListener('click',function(){shown+=PAGE*3;render();});
  render();

  /* Relative "generated N minutes ago" clock, refreshed in place. */
  var stamps=document.querySelectorAll('.age');
  if(stamps.length&&DATA.generated_at){
    var t=new Date(DATA.generated_at);
    var tick=function(){
      var s=Math.max(0,(Date.now()-t.getTime())/1000);
      var txt=s<90?Math.round(s)+'s':(s<5400?Math.round(s/60)+' min':(s<172800?Math.round(s/3600)+' hr':Math.round(s/86400)+' d'));
      for(var i=0;i<stamps.length;i++) stamps[i].textContent=txt+' ago';
    };
    tick(); setInterval(tick,15000);
  }

  /* Show the reader's local time alongside the UTC stamp. */
  var local=document.getElementById('localtime');
  if(local&&DATA.generated_at){
    try{ local.textContent=new Date(DATA.generated_at).toLocaleString(); }catch(e){}
  }
})();
"""
