"""GEO Intelligence 遥测控制台渲染器 —— 纯函数 render_html(payload)->str。

设计底版=遥测台（SpaceX 遥测读数墙 × visionOS 玻璃材质 × 诚实即设计），
嫁接叙事台的：发现→证据→机会→行动 叙事脊柱、可排序表头、GO 筛选芯片、
监测趋势 SVG 折线、provenance 公式块。

接缝：assembler 生产 payload（见 PROJECT_BRIEF 数据契约），本模块消费它。
所有数字来自 payload（回溯 capture_id），本模块零编造、零磁盘/网络 I/O、零外链。
leaderboard.kind ∈ {"citation","attraction"} 由 columns 动态出列，两分支皆正确渲染。
monitoring.available=false 优雅降级。证据抽屉/机会筛选/SoV 条/诚实横幅/provenance 全保留。
"""
from __future__ import annotations

import json
from typing import Any


def render_html(payload: dict[str, Any]) -> str:
    data_json = json.dumps(payload, ensure_ascii=False)
    return _TEMPLATE.replace("__DATA_JSON__", data_json)


_STYLE = r"""
  :root{
    --bg:#05070d; --bg2:#080b14; --ink:#e8edf7; --ink-dim:#9aa6bd; --ink-faint:#5c6781;
    --glass:rgba(20,27,44,.55); --glass-hi:rgba(30,40,64,.66); --stroke:rgba(132,156,210,.16);
    --stroke-hi:rgba(150,180,255,.34); --cyan:#48e6ff; --cyan-dim:#1d6f86; --amber:#ffc857;
    --green:#36e2a4; --red:#ff6b7a; --violet:#9b8cff; --grid:rgba(90,120,190,.08);
    --mono:'SFMono-Regular',ui-monospace,'JetBrains Mono','Menlo',monospace;
    --sans:'PingFang SC','Hiragino Sans GB',-apple-system,'Segoe UI',system-ui,sans-serif;
  }
  *{box-sizing:border-box;margin:0;padding:0}
  html,body{background:var(--bg);color:var(--ink);font-family:var(--sans);-webkit-font-smoothing:antialiased}
  body{
    min-height:100vh;line-height:1.5;letter-spacing:.01em;
    background:
      radial-gradient(1100px 620px at 78% -8%,rgba(72,230,255,.10),transparent 60%),
      radial-gradient(900px 560px at 8% 4%,rgba(155,140,255,.09),transparent 58%),
      linear-gradient(180deg,#05070d,#04060b 60%,#03050a);
    background-attachment:fixed;
  }
  body::before{
    content:"";position:fixed;inset:0;pointer-events:none;z-index:0;opacity:.5;
    background-image:linear-gradient(var(--grid) 1px,transparent 1px),linear-gradient(90deg,var(--grid) 1px,transparent 1px);
    background-size:46px 46px;mask-image:radial-gradient(1200px 800px at 60% 0%,#000 30%,transparent 85%);
  }
  .wrap{position:relative;z-index:1;max-width:1320px;margin:0 auto;padding:26px 26px 80px}
  .mono{font-family:var(--mono);font-variant-numeric:tabular-nums}
  .dim{color:var(--ink-dim)} .faint{color:var(--ink-faint)}

  /* ---- honesty banner ---- */
  .honesty{
    display:grid;grid-template-columns:repeat(3,1fr);gap:1px;border-radius:16px;overflow:hidden;
    background:var(--stroke);border:1px solid var(--stroke);margin-bottom:22px;
    backdrop-filter:blur(18px) saturate(1.3);
  }
  .hcol{padding:13px 16px;background:var(--glass)}
  .hcol h4{font-size:11px;font-weight:600;letter-spacing:.14em;text-transform:uppercase;margin-bottom:8px;display:flex;align-items:center;gap:7px}
  .dot{width:7px;height:7px;border-radius:50%;box-shadow:0 0 9px currentColor}
  .hcol.ok h4{color:var(--green)} .hcol.pend h4{color:var(--amber)} .hcol.cav h4{color:var(--ink-dim)}
  .hcol ul{list-style:none;display:flex;flex-direction:column;gap:5px}
  .hcol li{font-size:12px;color:var(--ink-dim);line-height:1.45;display:flex;gap:7px;align-items:flex-start}
  .hcol li::before{content:"";flex:0 0 5px;height:5px;border-radius:50%;margin-top:7px;background:currentColor;opacity:.55}
  .hcol.ok li{color:#bfeede} .hcol.pend li{color:#f0dca6} .hcol.cav li{color:var(--ink-dim)}

  /* ---- masthead ---- */
  .masthead{display:flex;justify-content:space-between;align-items:flex-end;gap:20px;margin-bottom:18px;flex-wrap:wrap}
  .brand{display:flex;align-items:center;gap:13px}
  .logo{
    width:42px;height:42px;border-radius:12px;display:grid;place-items:center;flex:0 0 auto;
    background:linear-gradient(150deg,rgba(72,230,255,.22),rgba(155,140,255,.16));
    border:1px solid var(--stroke-hi);box-shadow:0 0 24px rgba(72,230,255,.18),inset 0 0 16px rgba(72,230,255,.10);
  }
  .logo svg{width:22px;height:22px}
  .brand .t1{font-size:12px;letter-spacing:.32em;color:var(--cyan);font-weight:600;text-transform:uppercase}
  .brand .t2{font-size:21px;font-weight:650;letter-spacing:.01em}
  .brand .t3{font-size:12.5px;color:var(--ink-dim);margin-top:1px}
  .statusbar{display:flex;gap:9px;flex-wrap:wrap;align-items:center}
  .pill{
    font-size:11px;padding:5px 11px;border-radius:999px;border:1px solid var(--stroke);
    background:var(--glass);color:var(--ink-dim);display:flex;align-items:center;gap:6px;backdrop-filter:blur(10px)
  }
  .pill .dot{width:6px;height:6px}
  .pill.live{color:var(--green);border-color:rgba(54,226,164,.3)}
  .pill.live .dot{background:var(--green);animation:pulse 2s ease-in-out infinite}
  @keyframes pulse{0%,100%{opacity:1;box-shadow:0 0 0 0 rgba(54,226,164,.5)}50%{opacity:.55;box-shadow:0 0 0 5px rgba(54,226,164,0)}}

  /* ---- HERO telemetry wall ---- */
  .hero{
    border-radius:20px;border:1px solid var(--stroke);background:linear-gradient(180deg,var(--glass-hi),var(--glass));
    backdrop-filter:blur(22px) saturate(1.4);padding:22px 24px;margin-bottom:18px;position:relative;overflow:hidden;
    box-shadow:0 24px 60px -28px rgba(0,0,0,.8),inset 0 1px 0 rgba(255,255,255,.05);
  }
  .hero::after{content:"";position:absolute;right:-40px;top:-60px;width:300px;height:300px;border-radius:50%;
    background:radial-gradient(circle,rgba(72,230,255,.10),transparent 70%);pointer-events:none}
  .hero-head{display:flex;justify-content:space-between;gap:16px;align-items:flex-start;margin-bottom:18px;position:relative}
  .hero-finding{max-width:760px}
  .hero-eyebrow{font-size:11px;letter-spacing:.18em;text-transform:uppercase;color:var(--cyan);font-weight:600;margin-bottom:7px}
  .hero-finding h1{font-size:25px;line-height:1.32;font-weight:640;letter-spacing:.005em}
  .hero-finding h1 b{color:var(--cyan);font-weight:700}
  .hero-finding h1 .gap{color:var(--amber);font-weight:700}
  .hero-finding h1 .lock{color:var(--cyan);font-weight:700}
  .hero-engine{text-align:right;flex:0 0 auto;font-size:11.5px;color:var(--ink-dim);line-height:1.7}
  .hero-engine .em{color:var(--ink);font-weight:600}

  /* ---- narrative spine (grafted from 叙事台) ---- */
  .spine{display:flex;gap:1px;border-radius:13px;overflow:hidden;background:var(--stroke);border:1px solid var(--stroke);margin-bottom:18px}
  .spine-step{flex:1;min-width:150px;padding:13px 16px;position:relative;background:linear-gradient(180deg,rgba(14,20,34,.66),rgba(10,15,26,.66))}
  .spine-step:not(:last-child)::after{content:"→";position:absolute;right:-8px;top:50%;transform:translateY(-50%);color:var(--ink-faint);font-size:15px;z-index:2}
  .spine-num{font-family:var(--mono);font-size:10.5px;color:var(--cyan);letter-spacing:.08em}
  .spine-name{font-size:14px;font-weight:650;margin:4px 0 3px}
  .spine-desc{font-size:11.5px;color:var(--ink-dim);line-height:1.45}

  .readwall{display:grid;grid-template-columns:repeat(auto-fit,minmax(186px,1fr));gap:1px;border-radius:14px;overflow:hidden;
    background:var(--stroke);border:1px solid var(--stroke);position:relative}
  .read{background:linear-gradient(180deg,rgba(14,20,34,.7),rgba(10,15,26,.7));padding:15px 16px 14px;position:relative;min-height:118px;display:flex;flex-direction:column}
  .read .rl{font-size:11px;letter-spacing:.06em;color:var(--ink-dim);display:flex;align-items:center;gap:6px;margin-bottom:auto}
  .read .rv{font-family:var(--mono);font-weight:600;line-height:1;margin:8px 0 5px;display:flex;align-items:baseline;gap:5px}
  .read .rv .big{font-size:34px;letter-spacing:-.02em}
  .read .rv .big.txt{font-size:18px;line-height:1.18;letter-spacing:0;font-family:var(--sans);font-weight:650;color:var(--ink)}
  .read .rv .unit{font-size:13px;color:var(--ink-dim);font-family:var(--sans)}
  .read .rs{font-size:11px;color:var(--ink-faint);line-height:1.4}
  .read .glow{position:absolute;left:0;top:0;width:3px;height:100%;background:linear-gradient(180deg,var(--cyan),transparent);opacity:.6}
  .read.alarm .glow{background:linear-gradient(180deg,var(--amber),transparent)}
  .read.alarm .rv .big{color:var(--amber)}
  .read .spark{height:22px;margin-top:9px;display:flex;align-items:flex-end;gap:2px}
  .read .spark i{flex:1;background:linear-gradient(180deg,var(--cyan-dim),rgba(72,230,255,.55));border-radius:1px;min-height:2px;opacity:.8}
  .read.alarm .spark i{background:linear-gradient(180deg,rgba(255,200,87,.3),rgba(255,200,87,.7))}
  .trace-chip{
    align-self:flex-start;margin-top:9px;font-family:var(--mono);font-size:10px;color:var(--cyan);
    border:1px solid rgba(72,230,255,.28);background:rgba(72,230,255,.07);border-radius:6px;padding:2px 7px;
    cursor:default;display:inline-flex;gap:5px;align-items:center
  }

  /* ---- section scaffolding ---- */
  .grid2{display:grid;grid-template-columns:1.55fr 1fr;gap:18px;margin-bottom:18px}
  @media(max-width:980px){.grid2{grid-template-columns:1fr}.honesty{grid-template-columns:1fr}.hero-head{flex-direction:column}.hero-engine{text-align:left}.spine{flex-wrap:wrap}}
  .card{
    border-radius:18px;border:1px solid var(--stroke);background:var(--glass);backdrop-filter:blur(18px) saturate(1.3);
    padding:18px 20px;box-shadow:0 20px 50px -30px rgba(0,0,0,.8),inset 0 1px 0 rgba(255,255,255,.04);position:relative
  }
  .card.full{margin-bottom:18px}
  .sec-head{display:flex;justify-content:space-between;align-items:flex-end;gap:14px;margin-bottom:14px}
  .sec-head .st{font-size:15px;font-weight:640;letter-spacing:.01em}
  .sec-head .ss{font-size:12px;color:var(--ink-dim);margin-top:2px}
  .sec-num{font-family:var(--mono);font-size:11px;color:var(--cyan);border:1px solid var(--stroke-hi);border-radius:6px;padding:2px 7px;letter-spacing:.05em}

  /* ---- leaderboard table ---- */
  .tbl{width:100%;border-collapse:collapse;font-size:13px}
  .tbl th{font-size:10.5px;letter-spacing:.07em;text-transform:uppercase;color:var(--ink-faint);text-align:right;padding:7px 9px;font-weight:600;border-bottom:1px solid var(--stroke);cursor:pointer;user-select:none;white-space:nowrap}
  .tbl th:hover{color:var(--ink-dim)}
  .tbl th .arr{opacity:.5;font-size:8.5px;margin-left:3px}
  .tbl th.l,.tbl td.l{text-align:left}
  .tbl td{padding:9px 9px;border-bottom:1px solid rgba(132,156,210,.07);vertical-align:middle}
  .tbl tr:hover td{background:rgba(72,230,255,.035)}
  .tbl td.l .dom{font-family:var(--mono);font-size:12px;color:var(--ink)}
  .tbl td.l .site{font-size:11px;color:var(--ink-dim);margin-top:1px}
  .tbl td.l .nm{font-size:13px;color:var(--ink);font-weight:600}
  .inc-flag{font-size:9.5px;color:var(--amber);border:1px solid rgba(255,200,87,.3);border-radius:5px;padding:1px 6px;margin-left:8px;letter-spacing:.04em;white-space:nowrap}
  .num{font-family:var(--mono);text-align:right;font-variant-numeric:tabular-nums}
  .cov{display:flex;align-items:center;gap:9px;justify-content:flex-end}
  .cov .bar{flex:1;max-width:78px;height:5px;border-radius:3px;background:rgba(132,156,210,.14);overflow:hidden;position:relative}
  .cov .bar i{display:block;height:100%;border-radius:3px;background:linear-gradient(90deg,var(--cyan-dim),var(--cyan))}
  .cov .v{font-family:var(--mono);font-size:12px;color:var(--ink);min-width:42px;text-align:right}
  .score-g{display:inline-flex;align-items:center;gap:6px}
  .score-g .ring{--p:0;width:16px;height:16px;border-radius:50%;background:conic-gradient(var(--amber) calc(var(--p)*1%),rgba(132,156,210,.16) 0)}
  .rk{display:inline-grid;place-items:center;width:18px;height:18px;border-radius:5px;font-family:var(--mono);font-size:11px;color:var(--ink-dim);background:rgba(132,156,210,.1);margin-right:8px}
  .rk.top{color:var(--bg);background:linear-gradient(135deg,var(--cyan),#9be9ff);font-weight:700}

  /* ---- SoV gauges ---- */
  .sov-list{display:flex;flex-direction:column;gap:11px}
  .sov-row{display:grid;grid-template-columns:84px 1fr 54px;gap:11px;align-items:center}
  .sov-row .nm{font-size:13px;color:var(--ink);text-align:right;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .sov-track{height:14px;border-radius:7px;background:rgba(132,156,210,.1);overflow:hidden;position:relative;border:1px solid var(--stroke)}
  .sov-fill{height:100%;border-radius:7px;background:linear-gradient(90deg,rgba(72,230,255,.28),var(--cyan));box-shadow:0 0 14px rgba(72,230,255,.35);position:relative;transition:width .9s cubic-bezier(.2,.8,.2,1)}
  .sov-fill::after{content:"";position:absolute;right:0;top:0;width:2px;height:100%;background:#dffaff;opacity:.8}
  .sov-row:nth-child(n+2) .sov-fill{background:linear-gradient(90deg,rgba(155,140,255,.22),var(--violet));box-shadow:0 0 12px rgba(155,140,255,.3)}
  .sov-row .pc{font-family:var(--mono);font-size:13px;color:var(--ink);text-align:right}

  /* coverage donut for SoV header */
  .donut-wrap{display:flex;align-items:center;gap:16px;margin-bottom:16px;padding-bottom:15px;border-bottom:1px solid var(--stroke)}
  .donut{--p:0;width:74px;height:74px;border-radius:50%;flex:0 0 auto;position:relative;
    background:conic-gradient(var(--amber) calc(var(--p)*1%),rgba(132,156,210,.13) 0);display:grid;place-items:center}
  .donut::before{content:"";position:absolute;inset:9px;border-radius:50%;background:#080b14}
  .donut span{position:relative;font-family:var(--mono);font-size:17px;font-weight:600;color:var(--amber)}
  .donut-cap .dt{font-size:13px;font-weight:600;color:var(--ink)}
  .donut-cap .dd{font-size:11.5px;color:var(--ink-dim);margin-top:3px;line-height:1.45}

  /* ---- opportunity ---- */
  .opp-controls{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
  .seg{display:inline-flex;border:1px solid var(--stroke);border-radius:9px;overflow:hidden;background:rgba(10,15,26,.5)}
  .seg button{background:transparent;border:0;color:var(--ink-dim);font-size:11.5px;padding:6px 12px;cursor:pointer;font-family:inherit;transition:.15s}
  .seg button.on{background:rgba(72,230,255,.14);color:var(--cyan)}
  .seg button:hover:not(.on){color:var(--ink)}
  .opp-list{display:flex;flex-direction:column;gap:1px;border-radius:12px;overflow:hidden;border:1px solid var(--stroke);background:var(--stroke)}
  .opp{background:rgba(11,16,28,.7);transition:background .15s}
  .opp:hover{background:rgba(18,26,44,.8)}
  .opp-main{display:grid;grid-template-columns:50px 1fr auto;gap:14px;align-items:center;padding:11px 15px;cursor:pointer}
  .opp-score{font-family:var(--mono);font-size:21px;font-weight:600;text-align:center;line-height:1}
  .opp-score .o100{font-size:10px;color:var(--ink-faint);display:block;margin-top:2px;font-weight:400}
  .opp-q{font-size:13.5px;color:var(--ink);line-height:1.35}
  .opp-tags{display:flex;gap:7px;margin-top:5px;flex-wrap:wrap}
  .tag{font-size:10.5px;padding:2px 8px;border-radius:999px;background:rgba(132,156,210,.1);color:var(--ink-dim);border:1px solid var(--stroke);white-space:nowrap}
  .tag.go{color:var(--green);border-color:rgba(54,226,164,.32);background:rgba(54,226,164,.08)}
  .tag.watch{color:var(--amber);border-color:rgba(255,200,87,.32);background:rgba(255,200,87,.08)}
  .tag.hold,.tag.pass{color:var(--red);border-color:rgba(255,107,122,.32);background:rgba(255,107,122,.08)}
  .opp-right{display:flex;align-items:center;gap:14px}
  .winbar{width:104px}
  .winbar .wl{font-size:10px;color:var(--ink-faint);text-align:right;margin-bottom:4px;letter-spacing:.04em}
  .winbar .wt{height:7px;border-radius:4px;background:rgba(132,156,210,.13);overflow:hidden}
  .winbar .wf{height:100%;border-radius:4px;background:linear-gradient(90deg,var(--green),#7ef5cb)}
  .chev{color:var(--ink-faint);font-size:13px;transition:transform .2s;font-family:var(--mono)}
  .opp.open .chev{transform:rotate(90deg);color:var(--cyan)}
  .opp-detail{max-height:0;overflow:hidden;transition:max-height .3s ease;padding:0 15px}
  .opp.open .opp-detail{max-height:360px;padding:0 15px 14px 79px}
  .opp-reason{font-size:12.5px;color:var(--ink-dim);line-height:1.55;border-left:2px solid var(--cyan-dim);padding-left:12px;margin-bottom:10px}
  .opp-reason b{color:var(--amber);font-weight:600}
  .opp-meta{display:flex;gap:18px;flex-wrap:wrap;font-size:11.5px;color:var(--ink-faint)}
  .opp-meta b{color:var(--ink-dim);font-family:var(--mono);font-weight:500}
  .cid-row{margin-top:10px;display:flex;gap:7px;flex-wrap:wrap;align-items:center}
  .cid-row .lbl{font-size:11px;color:var(--ink-faint)}
  .cid{font-family:var(--mono);font-size:10.5px;color:var(--cyan);border:1px solid rgba(72,230,255,.26);background:rgba(72,230,255,.06);border-radius:6px;padding:2.5px 8px;cursor:pointer;transition:.15s}
  .cid:hover{background:rgba(72,230,255,.16);border-color:var(--cyan)}
  .cid.ghost{color:var(--ink-faint);border-color:var(--stroke);background:transparent;cursor:not-allowed}

  /* ---- monitoring / pipeline empty states ---- */
  .empty{border:1px dashed var(--stroke-hi);border-radius:14px;padding:26px 22px;text-align:center;background:rgba(10,15,26,.4)}
  .empty .ei{font-size:24px;margin-bottom:8px;opacity:.7}
  .empty .eh{font-size:13.5px;color:var(--ink);font-weight:600;margin-bottom:5px}
  .empty .ed{font-size:12px;color:var(--ink-dim);line-height:1.5;max-width:440px;margin:0 auto}
  .empty .baseline{font-family:var(--mono);font-size:11px;color:var(--cyan);margin-top:10px;letter-spacing:.04em}
  .mon-points{display:flex;flex-direction:column;gap:8px}
  .mon-pt{display:grid;grid-template-columns:auto 1fr auto;gap:12px;align-items:center;font-size:12px;padding:8px 12px;border:1px solid var(--stroke);border-radius:10px;background:rgba(11,16,28,.6)}
  /* monitoring trend chart (grafted from 叙事台) */
  .mon-chart{padding:4px 2px}
  .mon-svg{width:100%;height:180px;display:block}
  .mon-axis{display:flex;justify-content:space-between;font-family:var(--mono);font-size:10.5px;color:var(--ink-faint);margin-top:8px}

  /* ---- provenance footer ---- */
  .prov{margin-top:24px;border-radius:16px;border:1px solid var(--stroke);background:rgba(8,11,20,.6);padding:18px 22px;backdrop-filter:blur(14px)}
  .prov-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:18px}
  .prov-item h5{font-size:10.5px;letter-spacing:.12em;text-transform:uppercase;color:var(--cyan);margin-bottom:6px;font-weight:600}
  .prov-item p{font-size:12px;color:var(--ink-dim);line-height:1.55}
  .prov-item code{font-family:var(--mono);font-size:11px;color:var(--ink);background:rgba(72,230,255,.07);padding:1px 6px;border-radius:5px;border:1px solid var(--stroke)}
  .prov-formula{font-family:var(--mono);font-size:11px;color:var(--ink-dim);background:rgba(11,16,28,.6);border:1px solid var(--stroke);border-radius:9px;padding:10px 13px;margin-top:8px;line-height:1.7}

  /* ---- evidence drawer ---- */
  .scrim{position:fixed;inset:0;background:rgba(2,4,8,.72);backdrop-filter:blur(4px);opacity:0;pointer-events:none;transition:.25s;z-index:40}
  .scrim.on{opacity:1;pointer-events:auto}
  .drawer{position:fixed;top:0;right:0;height:100vh;width:min(560px,94vw);z-index:50;transform:translateX(102%);transition:transform .32s cubic-bezier(.2,.85,.25,1);
    background:linear-gradient(180deg,#0a0e1a,#070a12);border-left:1px solid var(--stroke-hi);box-shadow:-30px 0 80px -20px rgba(0,0,0,.9);display:flex;flex-direction:column}
  .drawer.on{transform:translateX(0)}
  .dw-head{padding:18px 22px;border-bottom:1px solid var(--stroke);display:flex;justify-content:space-between;align-items:flex-start;gap:14px}
  .dw-head .dq{font-size:15px;font-weight:640;line-height:1.4;color:var(--ink)}
  .dw-head .dm{font-family:var(--mono);font-size:10.5px;color:var(--ink-faint);margin-top:7px;word-break:break-all}
  .dw-close{flex:0 0 auto;width:30px;height:30px;border-radius:8px;border:1px solid var(--stroke);background:rgba(132,156,210,.07);color:var(--ink-dim);cursor:pointer;font-size:16px;display:grid;place-items:center}
  .dw-close:hover{color:var(--ink);border-color:var(--stroke-hi)}
  .dw-body{padding:18px 22px;overflow-y:auto;flex:1}
  .badge{display:inline-flex;align-items:center;gap:6px;font-size:11px;padding:3px 10px;border-radius:999px;font-weight:600}
  .badge.real{color:var(--green);background:rgba(54,226,164,.1);border:1px solid rgba(54,226,164,.3)}
  .badge.mock{color:var(--amber);background:rgba(255,200,87,.1);border:1px solid rgba(255,200,87,.3)}
  .dw-meta{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:16px}
  .dw-sub{font-size:10.5px;letter-spacing:.1em;text-transform:uppercase;color:var(--ink-faint);margin:18px 0 9px;font-weight:600}
  .excerpt{font-size:12.5px;line-height:1.7;color:var(--ink-dim);white-space:pre-wrap;background:rgba(11,16,28,.6);border:1px solid var(--stroke);border-radius:10px;padding:14px 16px;max-height:300px;overflow-y:auto}
  .brands{display:flex;gap:7px;flex-wrap:wrap}
  .brand-chip{font-size:11.5px;padding:3px 10px;border-radius:7px;background:rgba(155,140,255,.1);color:#cabfff;border:1px solid rgba(155,140,255,.28)}
  .src{border:1px solid var(--stroke);border-radius:10px;padding:11px 13px;margin-bottom:8px;background:rgba(11,16,28,.5)}
  .src .stitle{font-size:12.5px;color:var(--ink);line-height:1.4;margin-bottom:7px}
  .src .smeta{display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap}
  .src .sdom{font-family:var(--mono);font-size:11px;color:var(--cyan)}
  .src .sscores{display:flex;gap:10px}
  .miniscore{font-size:10px;color:var(--ink-faint);display:flex;flex-direction:column;align-items:center;gap:3px}
  .miniscore b{font-family:var(--mono);font-size:11px;color:var(--ink)}
  .miniscore .mbar{width:34px;height:3px;border-radius:2px;background:rgba(132,156,210,.16);overflow:hidden}
  .miniscore .mbar i{display:block;height:100%;background:var(--cyan)}
  .drawer-missing{text-align:center;padding:30px 16px;color:var(--ink-dim)}
  .drawer-missing .mi{font-size:22px;opacity:.6;margin-bottom:8px}
  .drawer-missing code{font-family:var(--mono);font-size:11px;color:var(--cyan);word-break:break-all}
  .nodata{font-size:12px;color:var(--ink-faint);font-style:italic}
"""

_BODY = r"""
<div class="wrap">

  <section class="honesty" id="honesty"></section>

  <header class="masthead">
    <div class="brand">
      <div class="logo">
        <svg viewBox="0 0 24 24" fill="none" stroke="#48e6ff" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="9"/><path d="M12 3v18M3 12h18"/><circle cx="12" cy="12" r="3.2" fill="rgba(72,230,255,.25)"/>
        </svg>
      </div>
      <div>
        <div class="t1">GEO Intelligence</div>
        <div class="t2" id="m-title">—</div>
        <div class="t3" id="m-subtitle">—</div>
      </div>
    </div>
    <div class="statusbar" id="statusbar"></div>
  </header>

  <section class="hero">
    <div class="hero-head">
      <div class="hero-finding">
        <div class="hero-eyebrow">头号发现 · PRIME SIGNAL</div>
        <h1 id="hero-finding">—</h1>
      </div>
      <div class="hero-engine" id="hero-engine"></div>
    </div>
    <div class="spine" id="spine">
      <div class="spine-step"><div class="spine-num">01 / 发现</div><div class="spine-name">谁占了答案</div><div class="spine-desc">AI 一开口推荐谁，空位率多大</div></div>
      <div class="spine-step"><div class="spine-num">02 / 证据</div><div class="spine-name">每个数可回溯</div><div class="spine-desc">点 capture_id 看原文与引用源</div></div>
      <div class="spine-step"><div class="spine-num">03 / 机会</div><div class="spine-name">哪里能赢</div><div class="spine-desc">低权威 incumbent + 空位 = GO</div></div>
      <div class="spine-step"><div class="spine-num">04 / 行动</div><div class="spine-name">产权威内容占位</div><div class="spine-desc">按机会评分驱动内容流水线</div></div>
    </div>
    <div class="readwall" id="readwall"></div>
  </section>

  <div class="grid2">
    <section class="card">
      <div class="sec-head">
        <div><div class="st" id="lb-title">—</div><div class="ss" id="lb-subtitle">—</div></div>
        <div class="sec-num">03 · LEADERBOARD</div>
      </div>
      <div style="overflow-x:auto"><table class="tbl" id="lb-table"></table></div>
    </section>

    <section class="card">
      <div class="sec-head">
        <div><div class="st" id="sov-title">占答份额 · Share of Answer</div><div class="ss" id="sov-sub">—</div></div>
        <div class="sec-num">04 · SOV</div>
      </div>
      <div class="donut-wrap" id="sov-donut"></div>
      <div class="sov-list" id="sov-list"></div>
    </section>
  </div>

  <section class="card full">
    <div class="sec-head">
      <div><div class="st">机会图 · 可赢度雷达</div><div class="ss">每行可展开看「为什么 + 证据」；空位 = 无名单实体占据的高机会 query</div></div>
      <div class="opp-controls">
        <div class="seg" id="opp-sort">
          <button data-k="score" class="on">按得分</button>
          <button data-k="opportunity">按机会值</button>
          <button data-k="go">按 GO</button>
        </div>
        <div class="seg" id="opp-filter"></div>
        <div class="sec-num">05 · OPPORTUNITY</div>
      </div>
    </div>
    <div class="opp-list" id="opp-list"></div>
  </section>

  <div class="grid2">
    <section class="card">
      <div class="sec-head">
        <div><div class="st">监测趋势 · Telemetry over time</div><div class="ss" id="mon-sub">—</div></div>
        <div class="sec-num">07 · MONITORING</div>
      </div>
      <div id="mon-body"></div>
    </section>
    <section class="card">
      <div class="sec-head">
        <div><div class="st">内容流水线 · Content pipeline</div><div class="ss">空位 → 真权威内容 → 人审 → 发布</div></div>
        <div class="sec-num">08 · PIPELINE</div>
      </div>
      <div id="pipe-body"></div>
    </section>
  </div>

  <section class="card full">
    <div class="sec-head">
      <div><div class="st">证据抽屉 · Evidence ledger</div><div class="ss">点任一 capture_id 看原文 + 引用源 + real/mock 徽章；指标皆可回溯至此</div></div>
      <div class="sec-num">06 · EVIDENCE</div>
    </div>
    <div class="cid-row" id="evidence-index"></div>
  </section>

  <footer class="prov">
    <div class="prov-grid">
      <div class="prov-item">
        <h5>指标来源 · Metrics</h5>
        <p>所有读数 = 对证据表的<b>纯函数</b>计算（<code>geo/metrics/</code>）。占答率/覆盖/auth 均回溯至 <code id="prov-dir">evidence/captures/</code> 内 capture_id，禁旁路、禁估算。</p>
        <div class="prov-formula">coverage = in_answers / n_answers<br>SoV = mentions / total_mentions<br>opportunity = f(空位率, incumbent_auth, 竞争度)</div>
      </div>
      <div class="prov-item">
        <h5>真相面 · Truth plane</h5>
        <p>代码 / 配置 / 原始证据库 / 内容草稿全部进 <code>git</code>，可 diff、可复现。确定性抽取：实体只匹配白名单 <code>watchlist.yaml</code>，同输入两次结论一致。</p>
      </div>
      <div class="prov-item">
        <h5>覆盖范围 · Coverage</h5>
        <p id="prov-coverage">—</p>
      </div>
    </div>
  </footer>

</div>

<div class="scrim" id="scrim"></div>
<aside class="drawer" id="drawer">
  <div class="dw-head">
    <div><div class="dq" id="dw-query">—</div><div class="dm" id="dw-id">—</div></div>
    <button class="dw-close" id="dw-close">✕</button>
  </div>
  <div class="dw-body" id="dw-body"></div>
</aside>
"""

_SCRIPT = r"""
(function(){
  const $=(s,r)=>(r||document).querySelector(s);
  const $$=(s,r)=>Array.from((r||document).querySelectorAll(s));
  const esc=s=>String(s==null?'':s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
  const pct=v=>v==null?'—':(v*100).toFixed(1)+'%';
  const fmtNum=v=>v==null?'—':(Number.isInteger(v)?v:(+v).toFixed(2));
  const sc2=v=>v==null?'—':(+v).toFixed(2);
  const D=DATA, M=D.meta||{}, H=M.honesty||{}, EL=M.entity_label||'品牌';

  /* ① honesty banner */
  const honestyCols=[
    {cls:'ok',title:'已打通引擎 · REAL',items:H.real_engines||[]},
    {cls:'pend',title:'待接入 · PENDING',items:H.pending_engines||[]},
    {cls:'cav',title:'已知局限 · CAVEATS',items:H.caveats||[]}
  ];
  $('#honesty').innerHTML=honestyCols.map(c=>`
    <div class="hcol ${c.cls}">
      <h4><span class="dot" style="background:currentColor"></span>${esc(c.title)}</h4>
      <ul>${(c.items.length?c.items:['—']).map(t=>`<li>${esc(t)}</li>`).join('')}</ul>
    </div>`).join('');

  /* masthead */
  $('#m-title').textContent=M.title||'GEO 控制台';
  $('#m-subtitle').textContent=M.subtitle||'';
  $('#prov-dir').textContent=M.evidence_dir||'evidence/captures/';
  const segTxt=(M.segments||[]).join(' / ')||'—';
  $('#prov-coverage').innerHTML=`引擎 <b>${esc(M.engine||'豆包')}</b> · 模型 <code>${esc((M.engine_models||[]).join(', ')||'—')}</code> · `+
    `客群 ${esc(segTxt)} · ${M.n_queries||0} query / ${M.n_captures||0} capture（${M.n_real||0} real · ${M.n_mock||0} mock）。`+
    `英文侧（Perplexity/OpenAI）待 key，未纳入本盘。`;

  const gapKpi=(D.kpis||[]).find(k=>String(k.label).includes('空位'));
  const statusItems=[
    {c:'live',t:`${esc(M.engine||'豆包')} LIVE · ${M.n_real||0}/${M.n_captures||0} REAL`},
    {c:'',t:`空位率 ${gapKpi?pct(gapKpi.value):'—'}`},
    {c:'',t:`客群 ${esc(segTxt)}`}
  ];
  $('#statusbar').innerHTML=statusItems.map(s=>`<span class="pill ${s.c}"><span class="dot"></span>${esc(s.t)}</span>`).join('');

  /* ② hero finding (derived from real values, no fabrication) */
  const inc=(D.kpis||[]).find(k=>String(k.label).includes('incumbent'));
  const sovTop=(D.sov||[])[0];
  const gapPct=gapKpi?pct(gapKpi.value):'—';
  const HERO=D.hero;
  if(HERO&&HERO.headline){
    const hcls=HERO.tone==='locked'?'lock':'gap';
    $('#hero-finding').innerHTML=
      `${esc(HERO.headline)}`+
      (HERO.emphasis?` <span class="${hcls}">${esc(HERO.emphasis)}</span>`:'')+
      (HERO.detail?` —— ${esc(HERO.detail)}`:'');
  }else{
    $('#hero-finding').innerHTML=
      `<span class="gap">${esc(gapPct)}</span> 的${esc(M.engine||'豆包')}回答里没有任何上榜${esc(EL)}——`+
      (inc&&inc.value?`头部位被软文站 <b>${esc(inc.value)}</b> 占据（低权威，<b>好打</b>）。`:'')+
      `这是一整片可被真权威内容占位的<span class="gap">${esc(EL)}空位</span>。`;
  }
  $('#hero-engine').innerHTML=
    `<div><span class="em">${esc(M.engine||'')}</span></div>`+
    `<div class="mono">${esc((M.engine_models||[])[0]||'')}</div>`+
    `<div style="margin-top:6px">证据 ${M.n_captures||0} 条 · ${M.n_real||0} real / ${M.n_mock||0} mock</div>`+
    `<div class="faint mono" style="font-size:10.5px">${esc(M.evidence_dir||'')}</div>`;

  /* ② KPI readout wall */
  const sparkOf=(seed)=>{const a=[];let x=seed%97/97;for(let i=0;i<11;i++){x=(x*1.7+0.31)%1;a.push(0.25+x*0.7)}return a;};
  $('#readwall').innerHTML=(D.kpis||[]).map((k,i)=>{
    const isTxt=typeof k.value==='string';
    let big;
    if(isTxt){big=`<span class="big txt">${esc(k.value)}</span>`;}
    else if(String(k.label).includes('空位')||String(k.label).includes('率')){big=`<span class="big">${(k.value*100).toFixed(1)}</span><span class="unit">%</span>`;}
    else {big=`<span class="big">${esc(k.value)}</span>`+(k.unit?`<span class="unit">${esc(k.unit)}</span>`:'');}
    const alarm=String(k.label).includes('空位')&&typeof k.value==='number'&&k.value>=0.4;
    const spk=sparkOf((k.label||'x').length*7+i*13);
    const sparkHtml=isTxt?'':`<div class="spark">${spk.map(h=>`<i style="height:${(h*100).toFixed(0)}%"></i>`).join('')}</div>`;
    const trace=k.trace?`<span class="trace-chip">◇ ${esc(k.trace)}</span>`:'';
    return `<div class="read ${alarm?'alarm':''}">
      <div class="glow"></div>
      <div class="rl">${esc(k.label)}</div>
      <div class="rv">${big}</div>
      <div class="rs">${esc(k.sub||'')}</div>
      ${sparkHtml}${trace}
    </div>`;
  }).join('');

  /* ③ leaderboard — dynamic columns for citation|attraction, sortable headers */
  const LB=D.leaderboard||{columns:[],rows:[]};
  $('#lb-title').textContent=LB.title||'占答排行';
  $('#lb-subtitle').textContent=LB.subtitle||'';
  const cols=LB.columns||[];
  const incName=(inc&&inc.value)?String(inc.value):'';
  const firstTextCol=(cols.find(c=>c.fmt==='text')||cols[0]||{}).key;
  const covCol=(cols.find(c=>c.fmt==='pct')||{}).key;
  const maxCov=covCol?Math.max(...(LB.rows||[]).map(r=>+r[covCol]||0),0.0001):1;
  const defaultSort=(cols.find(c=>c.fmt!=='text')||cols[0]||{}).key;
  let lbSort={key:defaultSort,dir:-1};

  function renderLB(){
    const rows=(LB.rows||[]).slice().sort((a,b)=>{
      const x=a[lbSort.key],y=b[lbSort.key];
      if(typeof x==='string'||typeof y==='string')return lbSort.dir*String(x==null?'':x).localeCompare(String(y==null?'':y));
      return lbSort.dir*((+x||0)-(+y||0));
    });
    const headHtml=`<thead><tr><th class="l">#</th>${cols.map(c=>{
      const arr=lbSort.key===c.key?`<span class="arr">${lbSort.dir<0?'▾':'▴'}</span>`:'';
      return `<th class="${c.fmt==='text'?'l':''}" data-k="${esc(c.key)}">${esc(c.label)}${arr}</th>`;
    }).join('')}</tr></thead>`;
    const rowHtml=rows.map((r,ri)=>{
      const cells=cols.map((c,ci)=>{
        const v=r[c.key];
        if(c.fmt==='text'){
          if(c.key===firstTextCol){
            const flagInc=incName&&String(v)&&incName.indexOf(String(v))>-1;
            if(LB.kind==='citation'&&c.key==='domain'){
              const flagSite=incName&&r.site_name&&incName.indexOf(String(r.site_name))>-1;
              return `<td class="l"><span class="rk ${ri===0?'top':''}">${ri+1}</span><span class="dom">${esc(v)}</span>${(flagInc||flagSite)?'<span class="inc-flag">头号 INCUMBENT</span>':''}${r.site_name&&'site_name'!==firstTextCol?`<div class="site">${esc(r.site_name)}</div>`:''}</td>`;
            }
            return `<td class="l"><span class="rk ${ri===0?'top':''}">${ri+1}</span><span class="nm">${esc(v)}</span>${flagInc?'<span class="inc-flag">头部</span>':''}</td>`;
          }
          return `<td class="l"><span class="dim" style="font-size:12px">${esc(v)}</span></td>`;
        }
        if(c.fmt==='pct'){
          const w=((+v||0)/maxCov*100).toFixed(0);
          return `<td><div class="cov"><div class="bar"><i style="width:${w}%"></i></div><span class="v">${pct(v)}</span></div></td>`;
        }
        if(c.fmt==='score'){
          const p=Math.round((+v||0)*100);
          return `<td class="num"><span class="score-g"><span class="ring" style="--p:${p}"></span>${sc2(v)}</span></td>`;
        }
        return `<td class="num">${fmtNum(v)}</td>`;
      }).join('');
      return `<tr>${cells}</tr>`;
    }).join('');
    $('#lb-table').innerHTML=headHtml+`<tbody>${rowHtml}</tbody>`;
    $$('#lb-table thead th[data-k]').forEach(th=>{
      th.addEventListener('click',()=>{
        const k=th.dataset.k;
        if(lbSort.key===k)lbSort.dir*=-1; else {lbSort.key=k;lbSort.dir=-1;}
        renderLB();
      });
    });
  }
  renderLB();

  /* ④ SoV */
  const SOV=(D.sov||[]).slice().sort((a,b)=>b.share-a.share);
  $('#sov-sub').textContent=`${EL}被点名的回答占比（降序，前 ${SOV.length}）`;
  const sovMax=Math.max(...SOV.map(s=>s.share),0.0001);
  const topShare=SOV[0]?SOV[0].share:0;
  $('#sov-donut').innerHTML=`
    <div class="donut" style="--p:${(topShare*100).toFixed(0)}"><span>${(topShare*100).toFixed(0)}%</span></div>
    <div class="donut-cap">
      <div class="dt">${esc(SOV[0]?SOV[0].entity:'—')} 领跑</div>
      <div class="dd">头号${esc(EL)}占据 ${pct(topShare)} 的被点名回答；其余 ${Math.max(SOV.length-1,0)} 家分食剩余份额。</div>
    </div>`;
  $('#sov-list').innerHTML=SOV.map(s=>`
    <div class="sov-row">
      <div class="nm" title="${esc(s.entity)}">${esc(s.entity)}</div>
      <div class="sov-track"><div class="sov-fill" style="width:0%" data-w="${(s.share/sovMax*100).toFixed(0)}"></div></div>
      <div class="pc">${pct(s.share)}</div>
    </div>`).join('');
  if(!SOV.length)$('#sov-list').innerHTML='<p class="nodata">本盘无 SoV 数据（无上榜实体被点名）。</p>';
  requestAnimationFrame(()=>setTimeout(()=>$$('.sov-fill').forEach(f=>f.style.width=f.dataset.w+'%'),60));

  /* ⑤ opportunity — sort + GO filter (filter grafted from 叙事台) */
  let oppSort='score', oppGo='ALL';
  const OPP=D.opportunity||[];
  const goSet=[...new Set(OPP.map(o=>o.go).filter(Boolean))];
  const maxOpp=Math.max(...OPP.map(o=>+o.opportunity||0),0.0001);
  const goClass=g=>({GO:'go',WATCH:'watch',HOLD:'hold',PASS:'pass'}[g]||'');
  $('#opp-filter').innerHTML=['ALL',...goSet].map((g,i)=>`<button data-g="${esc(g)}" class="${g==='ALL'?'on':''}">${g==='ALL'?'全部':esc(g)}</button>`).join('');
  function renderOpp(){
    const rows=OPP.filter(o=>oppGo==='ALL'||o.go===oppGo).slice().sort((a,b)=>{
      if(oppSort==='go'){const order={GO:0,WATCH:1,HOLD:2,PASS:3};const d=(order[a.go]??9)-(order[b.go]??9);if(d)return d;return (b.score||0)-(a.score||0);}
      return (+b[oppSort]||0)-(+a[oppSort]||0);
    });
    if(!rows.length){$('#opp-list').innerHTML='<div style="padding:22px;text-align:center" class="nodata">无匹配机会</div>';return;}
    $('#opp-list').innerHTML=rows.map((o,i)=>{
      const top=o.top||{};
      const win=top.coverage!=null?(top.coverage*100).toFixed(0):'—';
      const cids=(o.capture_ids||[]).map(id=>{
        const has=D.evidence&&D.evidence[id];
        return `<span class="cid ${has?'':'ghost'}" data-cid="${esc(id)}" title="${has?'查看证据原文':'capture 存在但未内联进本盘'}">◇ ${esc(id.length>34?id.slice(0,34)+'…':id)}</span>`;
      }).join('');
      const goTag=o.go?`<span class="tag ${goClass(o.go)}">${esc(o.go)}</span>`:'';
      return `<div class="opp" data-i="${i}">
        <div class="opp-main">
          <div class="opp-score">${fmtNum(o.score)}<span class="o100">/100</span></div>
          <div>
            <div class="opp-q">${esc(o.query)}</div>
            <div class="opp-tags">${goTag}<span class="tag">${esc(o.theme||'')}</span><span class="tag">客群 ${esc(o.segment||'')}</span>${o.competition?`<span class="tag">竞争 ${esc(o.competition)}</span>`:''}</div>
          </div>
          <div class="opp-right">
            <div class="winbar"><div class="wl">头部覆盖</div><div class="wt"><div class="wf" style="width:${win==='—'?0:win}%"></div></div></div>
            <span class="chev">›</span>
          </div>
        </div>
        <div class="opp-detail">
          <div class="opp-reason"><b>为什么可打：</b>${esc(o.reason||'')}</div>
          <div class="opp-meta">
            <span>机会值 <b>${fmtNum(o.opportunity)}</b></span>
            <span>头部 <b>${esc(top.label||'—')}</b>（覆盖 ${top.coverage!=null?pct(top.coverage):'—'}）</span>
            <span>引用数 <b>${o.n_citations!=null?o.n_citations:'—'}</b></span>
            ${o.entities&&o.entities.length?`<span>已点名 <b>${esc(o.entities.join('、'))}</b></span>`:'<span>已点名 <b>无</b>（纯空位）</span>'}
          </div>
          <div class="cid-row"><span class="lbl">证据：</span>${cids||'<span class="nodata">无</span>'}</div>
        </div>
      </div>`;
    }).join('');
  }
  $('#opp-sort').addEventListener('click',e=>{
    const b=e.target.closest('button');if(!b)return;
    $$('#opp-sort button').forEach(x=>x.classList.remove('on'));b.classList.add('on');
    oppSort=b.dataset.k;renderOpp();
  });
  $('#opp-filter').addEventListener('click',e=>{
    const b=e.target.closest('button');if(!b)return;
    $$('#opp-filter button').forEach(x=>x.classList.remove('on'));b.classList.add('on');
    oppGo=b.dataset.g;renderOpp();
  });
  renderOpp();
  $('#opp-list').addEventListener('click',e=>{
    const cidEl=e.target.closest('.cid');
    if(cidEl){if(!cidEl.classList.contains('ghost'))openDrawer(cidEl.dataset.cid);e.stopPropagation();return;}
    const row=e.target.closest('.opp');if(row)row.classList.toggle('open');
  });

  /* ⑦ monitoring — SVG trend chart when >=2 points, else graceful empty (graft from 叙事台) */
  const MON=D.monitoring||{};
  const pts=MON.points||[];
  $('#mon-sub').textContent=MON.note||'';
  if(MON.available && pts.length>=2){
    const W=1000,Hc=180,pad=30;
    const xs=pts.map((_,i)=>pad+(pts.length>1?i/(pts.length-1):0)*(W-pad*2));
    const ys=pts.map(p=>Hc-pad-(+p.top_coverage||0)*(Hc-pad*2));
    const path=xs.map((x,i)=>`${i?'L':'M'}${x.toFixed(1)},${ys[i].toFixed(1)}`).join(' ');
    const area=`${path} L${xs[xs.length-1].toFixed(1)},${Hc-pad} L${xs[0].toFixed(1)},${Hc-pad} Z`;
    $('#mon-body').innerHTML=`<div class="mon-chart">
      <svg class="mon-svg" viewBox="0 0 ${W} ${Hc}" preserveAspectRatio="none">
        <defs><linearGradient id="mg" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stop-color="rgba(72,230,255,.32)"/><stop offset="1" stop-color="rgba(72,230,255,0)"/>
        </linearGradient></defs>
        <path d="${area}" fill="url(#mg)"/>
        <path d="${path}" fill="none" stroke="#48e6ff" stroke-width="2"/>
        ${xs.map((x,i)=>`<circle cx="${x.toFixed(1)}" cy="${ys[i].toFixed(1)}" r="3.5" fill="#48e6ff"/>`).join('')}
      </svg>
      <div class="mon-axis">${pts.map(p=>`<span>${esc(String(p.captured_at||'').slice(5,10))} · ${pct(p.top_coverage)} · ${esc(p.top_label||'')}</span>`).join('')}</div>
    </div>`;
  }else{
    $('#mon-body').innerHTML=`
      <div class="empty">
        <div class="ei">⏳</div>
        <div class="eh">基线待建 · 趋势需多轮监测</div>
        <div class="ed">${esc(MON.note||'监测刚启动，尚无足够历史快照绘制趋势。')}${MON.available?'首轮已采，后续每轮自动追加，≥2 个对齐快照后此处升级为时间序列遥测带。':'监测线尚未接入。'}</div>
        <div class="baseline">${MON.available?'BASELINE_PENDING':'MONITORING_OFFLINE'} · ${pts.length} snapshot${pts.length===1?'':'s'} captured</div>
      </div>`;
  }

  /* ⑧ content pipeline */
  const PIPE=D.content_pipeline||[];
  if(PIPE.length){
    $('#pipe-body').innerHTML=`<div class="mon-points">`+PIPE.map(p=>{
      const b=p.basis||{};
      const cids=(b.capture_ids||[]).map(id=>{
        const has=D.evidence&&D.evidence[id];
        return `<span class="cid ${has?'':'ghost'}" data-cid="${esc(id)}">◇</span>`;
      }).join('');
      return `<div class="mon-pt" style="grid-template-columns:1fr auto">
        <span><b style="color:var(--ink)">${esc(p.title||p.file)}</b><div class="faint mono" style="font-size:10.5px">${esc(p.file||'')}</div></span>
        <span style="display:flex;gap:8px;align-items:center"><span class="tag ${b.go==='GO'?'go':''}">${esc(p.status||'')}${b.score!=null?' · '+fmtNum(b.score):''}</span>${cids}</span>
      </div>`;
    }).join('')+`</div>`;
    $('#pipe-body').addEventListener('click',e=>{const c=e.target.closest('.cid');if(c&&!c.classList.contains('ghost'))openDrawer(c.dataset.cid);});
  }else{
    const goN=OPP.filter(o=>o.go==='GO').length;
    $('#pipe-body').innerHTML=`
      <div class="empty">
        <div class="ei">📝</div>
        <div class="eh">草稿待建 · 流水线未注入</div>
        <div class="ed">本 payload 未携带内容草稿条目。机会图已识别 ${goN} 条 GO 机会，内容产出走 <code style="font-family:var(--mono);color:var(--cyan)">content/drafts/</code>，每篇绑定空位 query 的 score / GO 判定与 capture_id，人审通过后才进发布闸。</div>
        <div class="baseline">PIPELINE_EMPTY · 0 drafts in payload</div>
      </div>`;
  }

  /* ⑥ evidence index */
  const EV=D.evidence||{};
  const evKeys=Object.keys(EV);
  $('#evidence-index').innerHTML=`<span class="lbl">已内联 ${evKeys.length} 条证据：</span>`+
    (evKeys.length?evKeys.map(id=>{
      const e=EV[id];
      return `<span class="cid" data-cid="${esc(id)}" title="${esc(e.query||'')}">◇ ${esc(e.query?(e.query.length>16?e.query.slice(0,16)+'…':e.query):id)}</span>`;
    }).join(''):'<span class="nodata">无内联证据</span>');
  $('#evidence-index').addEventListener('click',e=>{const c=e.target.closest('.cid');if(c)openDrawer(c.dataset.cid);});

  /* drawer */
  const drawer=$('#drawer'),scrim=$('#scrim');
  function closeDrawer(){drawer.classList.remove('on');scrim.classList.remove('on');}
  $('#dw-close').addEventListener('click',closeDrawer);
  scrim.addEventListener('click',closeDrawer);
  document.addEventListener('keydown',e=>{if(e.key==='Escape')closeDrawer();});
  function openDrawer(id){
    const e=EV[id];
    $('#dw-id').textContent=id;
    if(!e){
      $('#dw-query').textContent='证据未内联';
      $('#dw-body').innerHTML=`<div class="drawer-missing">
        <div class="mi">◇</div>
        <p>该 capture 存在于证据库，但<b style="color:var(--amber)">未内联</b>进本仪表盘 payload。</p>
        <p style="margin-top:10px">原文可在真相面回溯：<br><code>${esc(M.evidence_dir||'evidence/captures/')}/${esc(id)}.json</code></p>
        <p class="faint" style="margin-top:10px;font-size:11px">诚实即设计：缺的证据如实标缺，绝不补假数据。</p>
      </div>`;
    }else{
      $('#dw-query').textContent=e.query||'—';
      const srcs=(e.cited_sources||[]);
      const srcHtml=srcs.length?srcs.map(s=>{
        const ms=[['auth',s.auth_score],['rel',s.rel_score],['fresh',s.freshness_score]].map(([lab,v])=>
          `<div class="miniscore"><div class="mbar"><i style="width:${v!=null?(v*100).toFixed(0):0}%"></i></div><b>${v!=null?(+v).toFixed(2):'—'}</b>${lab}</div>`).join('');
        return `<div class="src">
          <div class="stitle">${esc(s.title||'(无标题)')}</div>
          <div class="smeta"><span class="sdom">${esc(s.domain||'')} · ${esc(s.site_name||'')}</span><span class="sscores">${ms}</span></div>
        </div>`;
      }).join(''):'<p class="nodata">本回答无引用源（豆包未联网或未给出引用）。</p>';
      const brands=(e.named_brands||[]);
      $('#dw-body').innerHTML=`
        <div class="dw-meta">
          <span class="badge ${e.is_mock?'mock':'real'}"><span class="dot" style="background:currentColor;box-shadow:0 0 6px currentColor"></span>${e.is_mock?'MOCK 证据':'REAL 真实证据'}</span>
          <span class="tag">客群 ${esc(e.segment||'')}</span>
          <span class="tag mono">${esc(e.engine_model||'')}</span>
          <span class="tag mono">${esc((e.timestamp||'').slice(0,19).replace('T',' '))}</span>
        </div>
        <div class="dw-sub">命中${esc(EL)}（白名单确定性抽取）</div>
        ${brands.length?`<div class="brands">${brands.map(b=>`<span class="brand-chip">${esc(b)}</span>`).join('')}</div>`:`<p class="nodata">本回答未点名任何上榜${esc(EL)} — 即「${esc(EL)}空位」样本。</p>`}
        <div class="dw-sub">AI 原文摘录 · RAW EXCERPT</div>
        <div class="excerpt">${esc(e.raw_excerpt||'')}</div>
        <div class="dw-sub">引用源 · CITED SOURCES（${srcs.length}）</div>
        ${srcHtml}`;
    }
    drawer.classList.add('on');scrim.classList.add('on');
  }
})();
"""

_TEMPLATE = (
    "<!doctype html>\n<html lang=\"zh-CN\">\n<head>\n"
    "<meta charset=\"utf-8\">\n"
    "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">\n"
    "<title>GEO Intelligence · 遥测控制台</title>\n"
    "<style>" + _STYLE + "</style>\n"
    "</head>\n<body>\n"
    + _BODY +
    "\n<script>const DATA=__DATA_JSON__;</script>\n"
    "<script>" + _SCRIPT + "</script>\n"
    "</body>\n</html>\n"
)
