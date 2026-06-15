"""GEO 机会指挥台渲染器 —— 纯函数 render_html(payload)->str。

把两个品类（高端礼盒 + 上海文旅）的全部「机会」聚合进一个跨品类指挥台，
按可赢度（score）降序排，回答「哪些 GEO 空位最值得打、为什么能赢、该产什么内容」。

设计底版 = 遥测台（SpaceX 遥测读数墙 × visionOS 玻璃材质 × 诚实即设计），
与 geo/reporting/dashboard_render.py 共用视觉语言。

红线：所有数字来自 payload（真证据纯函数算的），每条机会可回溯 capture_id；
real/mock 诚实标注；**跨品类评分语义不同必须诚实披露**（caveats[0] 显眼，象限图旁注）。
本模块零编造、零磁盘/网络 I/O、零外链；payload 经 json.dumps 内联，JS 全程用 DATA 渲染。
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
    --gift:#ffb454; --gift-dim:rgba(255,180,84,.16); --tour:#48e6ff; --tour-dim:rgba(72,230,255,.16);
    --mono:'SFMono-Regular',ui-monospace,'JetBrains Mono','Menlo',monospace;
    --sans:'PingFang SC','Hiragino Sans GB',-apple-system,'Segoe UI',system-ui,sans-serif;
  }
  *{box-sizing:border-box;margin:0;padding:0}
  html,body{background:var(--bg);color:var(--ink);font-family:var(--sans);-webkit-font-smoothing:antialiased}
  body{
    min-height:100vh;line-height:1.5;letter-spacing:.01em;
    background:
      radial-gradient(1100px 620px at 78% -8%,rgba(72,230,255,.10),transparent 60%),
      radial-gradient(900px 560px at 8% 4%,rgba(255,180,84,.07),transparent 58%),
      linear-gradient(180deg,#05070d,#04060b 60%,#03050a);
    background-attachment:fixed;
  }
  body::before{
    content:"";position:fixed;inset:0;pointer-events:none;z-index:0;opacity:.5;
    background-image:linear-gradient(var(--grid) 1px,transparent 1px),linear-gradient(90deg,var(--grid) 1px,transparent 1px);
    background-size:46px 46px;mask-image:radial-gradient(1200px 800px at 60% 0%,#000 30%,transparent 85%);
  }
  .wrap{position:relative;z-index:1;max-width:1340px;margin:0 auto;padding:26px 26px 80px}
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
  .hcol.cav li.flag{color:#f7d489;font-weight:500}
  .hcol.cav li.flag::before{background:var(--amber);opacity:1;box-shadow:0 0 7px var(--amber)}

  /* ---- masthead ---- */
  .masthead{display:flex;justify-content:space-between;align-items:flex-end;gap:20px;margin-bottom:18px;flex-wrap:wrap}
  .brand{display:flex;align-items:center;gap:13px}
  .logo{
    width:42px;height:42px;border-radius:12px;display:grid;place-items:center;flex:0 0 auto;
    background:linear-gradient(150deg,rgba(72,230,255,.22),rgba(255,180,84,.16));
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
  .pill.gift{color:var(--gift);border-color:rgba(255,180,84,.3)} .pill.gift .dot{background:var(--gift)}
  .pill.tour{color:var(--tour);border-color:rgba(72,230,255,.3)} .pill.tour .dot{background:var(--tour)}
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
  .hero-finding{max-width:820px}
  .hero-eyebrow{font-size:11px;letter-spacing:.18em;text-transform:uppercase;color:var(--cyan);font-weight:600;margin-bottom:7px}
  .hero-finding h1{font-size:24px;line-height:1.34;font-weight:640;letter-spacing:.005em}
  .hero-finding h1 b{color:var(--cyan);font-weight:700}
  .hero-finding h1 .gap{color:var(--amber);font-weight:700}
  .hero-finding h1 .best{color:var(--green);font-weight:700}
  .hero-engine{text-align:right;flex:0 0 auto;font-size:11.5px;color:var(--ink-dim);line-height:1.7}
  .hero-engine .em{color:var(--ink);font-weight:600}

  .readwall{display:grid;grid-template-columns:repeat(auto-fit,minmax(184px,1fr));gap:1px;border-radius:14px;overflow:hidden;
    background:var(--stroke);border:1px solid var(--stroke);position:relative}
  .read{background:linear-gradient(180deg,rgba(14,20,34,.7),rgba(10,15,26,.7));padding:15px 16px 14px;position:relative;min-height:120px;display:flex;flex-direction:column}
  .read .rl{font-size:11px;letter-spacing:.06em;color:var(--ink-dim);display:flex;align-items:center;gap:6px;margin-bottom:auto}
  .read .rv{font-family:var(--mono);font-weight:600;line-height:1;margin:8px 0 5px;display:flex;align-items:baseline;gap:5px}
  .read .rv .big{font-size:34px;letter-spacing:-.02em}
  .read .rv .unit{font-size:13px;color:var(--ink-dim);font-family:var(--sans)}
  .read .rs{font-size:11px;color:var(--ink-faint);line-height:1.45}
  .read .rs b{color:var(--ink-dim);font-weight:500}
  .read .split{display:flex;gap:10px;margin-top:7px;font-size:11px}
  .read .split .segc{display:flex;align-items:center;gap:5px;color:var(--ink-dim)}
  .read .split .seg-d{width:7px;height:7px;border-radius:2px}
  .read .glow{position:absolute;left:0;top:0;width:3px;height:100%;background:linear-gradient(180deg,var(--cyan),transparent);opacity:.6}
  .read.go .glow{background:linear-gradient(180deg,var(--green),transparent)}
  .read.go .rv .big{color:var(--green)}
  .read.div .glow{background:linear-gradient(180deg,var(--amber),transparent)}
  .read.div .rv .big{color:var(--amber)}
  .read .spark{height:22px;margin-top:9px;display:flex;align-items:flex-end;gap:2px}
  .read .spark i{flex:1;background:linear-gradient(180deg,var(--cyan-dim),rgba(72,230,255,.55));border-radius:1px;min-height:2px;opacity:.8}

  /* ---- section scaffolding ---- */
  .grid2{display:grid;grid-template-columns:1.5fr 1fr;gap:18px;margin-bottom:18px}
  @media(max-width:1040px){.grid2{grid-template-columns:1fr}.honesty{grid-template-columns:1fr}.hero-head{flex-direction:column}.hero-engine{text-align:left}}
  .card{
    border-radius:18px;border:1px solid var(--stroke);background:var(--glass);backdrop-filter:blur(18px) saturate(1.3);
    padding:18px 20px;box-shadow:0 20px 50px -30px rgba(0,0,0,.8),inset 0 1px 0 rgba(255,255,255,.04);position:relative
  }
  .card.full{margin-bottom:18px}
  .sec-head{display:flex;justify-content:space-between;align-items:flex-end;gap:14px;margin-bottom:14px;flex-wrap:wrap}
  .sec-head .st{font-size:15px;font-weight:640;letter-spacing:.01em}
  .sec-head .ss{font-size:12px;color:var(--ink-dim);margin-top:2px;max-width:560px;line-height:1.5}
  .sec-num{font-family:var(--mono);font-size:11px;color:var(--cyan);border:1px solid var(--stroke-hi);border-radius:6px;padding:2px 7px;letter-spacing:.05em}

  /* ---- quadrant scatter ---- */
  .quad-wrap{display:grid;grid-template-columns:1fr 248px;gap:20px;align-items:stretch}
  @media(max-width:1040px){.quad-wrap{grid-template-columns:1fr}}
  .quad-stage{position:relative;border-radius:14px;border:1px solid var(--stroke);background:rgba(8,12,22,.55);overflow:hidden;min-height:380px}
  .quad-svg{width:100%;height:100%;display:block}
  .quad-side{display:flex;flex-direction:column;gap:14px}
  .quad-legend{border:1px solid var(--stroke);border-radius:12px;padding:14px 15px;background:rgba(11,16,28,.6)}
  .quad-legend h5{font-size:10.5px;letter-spacing:.12em;text-transform:uppercase;color:var(--ink-faint);margin-bottom:10px;font-weight:600}
  .leg-row{display:flex;align-items:center;gap:9px;font-size:12px;color:var(--ink-dim);margin-bottom:8px}
  .leg-row:last-child{margin-bottom:0}
  .leg-dot{width:11px;height:11px;border-radius:50%;flex:0 0 auto;box-shadow:0 0 8px currentColor}
  .leg-row .lc{color:var(--ink)} .leg-row .ln{font-family:var(--mono);color:var(--ink-faint);margin-left:auto}
  .quad-note{border:1px solid rgba(255,200,87,.26);border-radius:12px;padding:12px 14px;background:rgba(255,200,87,.05)}
  .quad-note .qh{font-size:10.5px;letter-spacing:.1em;text-transform:uppercase;color:var(--amber);font-weight:600;margin-bottom:6px;display:flex;align-items:center;gap:6px}
  .quad-note p{font-size:11.5px;color:#e9cf9f;line-height:1.55}
  .quad-prime{border:1px solid rgba(54,226,164,.28);border-radius:12px;padding:12px 14px;background:rgba(54,226,164,.06)}
  .quad-prime .qh{font-size:10.5px;letter-spacing:.1em;text-transform:uppercase;color:var(--green);font-weight:600;margin-bottom:6px}
  .quad-prime p{font-size:11.5px;color:#bfeede;line-height:1.55}
  .quad-prime b{color:#dffaee;font-weight:600}
  .quad-empty{display:grid;place-items:center;height:100%;min-height:340px;color:var(--ink-faint);font-style:italic}
  .qtip{position:absolute;pointer-events:none;z-index:8;background:rgba(8,12,22,.95);border:1px solid var(--stroke-hi);border-radius:9px;
    padding:9px 11px;font-size:11.5px;color:var(--ink);max-width:240px;opacity:0;transform:translateY(4px);transition:opacity .12s;backdrop-filter:blur(10px);box-shadow:0 12px 30px -12px rgba(0,0,0,.85)}
  .qtip.on{opacity:1;transform:translateY(0)}
  .qtip .qq{font-weight:600;line-height:1.4;margin-bottom:5px}
  .qtip .qm{font-family:var(--mono);font-size:10.5px;color:var(--ink-dim);display:flex;gap:9px;flex-wrap:wrap}
  .qtip .qcat{display:inline-block;font-size:10px;padding:1px 7px;border-radius:999px;margin-top:6px}
  .qdot{cursor:pointer;transition:r .12s,opacity .12s}

  /* ---- priority tiers ---- */
  .tiers{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-bottom:18px}
  @media(max-width:760px){.tiers{grid-template-columns:1fr}}
  .tier{border-radius:16px;border:1px solid var(--stroke);background:var(--glass);backdrop-filter:blur(16px) saturate(1.3);
    padding:16px 18px;cursor:pointer;transition:.18s;position:relative;overflow:hidden}
  .tier:hover{border-color:var(--stroke-hi);transform:translateY(-1px)}
  .tier.active{border-color:var(--stroke-hi);box-shadow:0 0 0 1px var(--stroke-hi),inset 0 0 30px rgba(72,230,255,.05)}
  .tier .th{display:flex;justify-content:space-between;align-items:center;margin-bottom:9px}
  .tier .tlab{font-size:13px;font-weight:650;display:flex;align-items:center;gap:8px}
  .tier .tdot{width:9px;height:9px;border-radius:50%;box-shadow:0 0 9px currentColor}
  .tier.go .tlab,.tier.go .tnum{color:var(--green)} .tier.go .tdot{background:var(--green)}
  .tier.cand .tlab,.tier.cand .tnum{color:var(--amber)} .tier.cand .tdot{background:var(--amber)}
  .tier.hold .tlab,.tier.hold .tnum{color:var(--red)} .tier.hold .tdot{background:var(--red)}
  .tier .tact{font-size:10px;letter-spacing:.1em;text-transform:uppercase;color:var(--ink-faint)}
  .tier .tnum{font-family:var(--mono);font-size:32px;font-weight:600;line-height:1}
  .tier .tsplit{display:flex;gap:14px;margin-top:9px;font-size:11.5px;color:var(--ink-dim)}
  .tier .tsplit b{font-family:var(--mono);color:var(--ink);font-weight:500}
  .tier .tsplit .sg{display:flex;align-items:center;gap:6px}
  .tier .tsplit .sg i{width:7px;height:7px;border-radius:2px;display:inline-block}

  /* ---- attack board controls ---- */
  .board-controls{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
  .seg{display:inline-flex;border:1px solid var(--stroke);border-radius:9px;overflow:hidden;background:rgba(10,15,26,.5)}
  .seg button{background:transparent;border:0;color:var(--ink-dim);font-size:11.5px;padding:6px 12px;cursor:pointer;font-family:inherit;transition:.15s}
  .seg button.on{background:rgba(72,230,255,.14);color:var(--cyan)}
  .seg button:hover:not(.on){color:var(--ink)}
  .search{display:inline-flex;align-items:center;gap:7px;border:1px solid var(--stroke);border-radius:9px;background:rgba(10,15,26,.5);padding:0 11px}
  .search svg{width:13px;height:13px;stroke:var(--ink-faint);flex:0 0 auto}
  .search input{background:transparent;border:0;color:var(--ink);font-size:12px;padding:7px 0;outline:none;font-family:inherit;width:150px}
  .search input::placeholder{color:var(--ink-faint)}
  .board-count{font-size:11.5px;color:var(--ink-faint);margin-left:auto}
  .board-count b{font-family:var(--mono);color:var(--cyan);font-weight:500}

  /* ---- attack board rows ---- */
  .opp-list{display:flex;flex-direction:column;gap:1px;border-radius:12px;overflow:hidden;border:1px solid var(--stroke);background:var(--stroke)}
  .opp{background:rgba(11,16,28,.7);transition:background .15s}
  .opp:hover{background:rgba(18,26,44,.8)}
  .opp.cat-gift{box-shadow:inset 3px 0 0 var(--gift)}
  .opp.cat-tour{box-shadow:inset 3px 0 0 var(--tour)}
  .opp.lit{background:rgba(72,230,255,.07)}
  .opp-main{display:grid;grid-template-columns:34px 58px 1fr auto;gap:14px;align-items:center;padding:11px 15px 11px 16px;cursor:pointer}
  .opp-rk{font-family:var(--mono);font-size:12px;color:var(--ink-faint);text-align:center}
  .opp-score{font-family:var(--mono);font-size:22px;font-weight:600;text-align:center;line-height:1}
  .opp-score .o100{font-size:10px;color:var(--ink-faint);display:block;margin-top:2px;font-weight:400}
  .opp-q{font-size:13.5px;color:var(--ink);line-height:1.35}
  .opp-tags{display:flex;gap:7px;margin-top:5px;flex-wrap:wrap;align-items:center}
  .tag{font-size:10.5px;padding:2px 8px;border-radius:999px;background:rgba(132,156,210,.1);color:var(--ink-dim);border:1px solid var(--stroke);white-space:nowrap}
  .tag.go{color:var(--green);border-color:rgba(54,226,164,.32);background:rgba(54,226,164,.08)}
  .tag.cand{color:var(--amber);border-color:rgba(255,200,87,.32);background:rgba(255,200,87,.08)}
  .tag.hold{color:var(--red);border-color:rgba(255,107,122,.32);background:rgba(255,107,122,.08)}
  .chip-cat{font-size:10.5px;padding:2px 9px;border-radius:999px;font-weight:600;white-space:nowrap;display:inline-flex;align-items:center;gap:5px}
  .chip-cat i{width:6px;height:6px;border-radius:50%}
  .chip-cat.gift{color:var(--gift);background:var(--gift-dim);border:1px solid rgba(255,180,84,.32)} .chip-cat.gift i{background:var(--gift)}
  .chip-cat.tour{color:var(--tour);background:var(--tour-dim);border:1px solid rgba(72,230,255,.32)} .chip-cat.tour i{background:var(--tour)}
  .opp-right{display:flex;align-items:center;gap:16px}
  .divbar{width:118px}
  .divbar .wl{font-size:10px;color:var(--ink-faint);display:flex;justify-content:space-between;margin-bottom:4px;letter-spacing:.03em}
  .divbar .wl .wv{font-family:var(--mono);color:var(--amber)}
  .divbar .wt{height:7px;border-radius:4px;background:rgba(132,156,210,.13);overflow:hidden}
  .divbar .wf{height:100%;border-radius:4px;background:linear-gradient(90deg,rgba(255,200,87,.5),var(--amber));transition:width .7s cubic-bezier(.2,.8,.2,1)}
  .opp-inc{width:150px;text-align:right}
  .opp-inc .il{font-size:10px;color:var(--ink-faint);letter-spacing:.03em;margin-bottom:3px}
  .opp-inc .iv{font-size:12px;color:var(--ink-dim);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .opp-inc .iv b{font-family:var(--mono);color:var(--ink)}
  .chev{color:var(--ink-faint);font-size:13px;transition:transform .2s;font-family:var(--mono)}
  .opp.open .chev{transform:rotate(90deg);color:var(--cyan)}
  .opp-action{font-size:11px;color:var(--ink-dim);margin-top:6px;display:flex;align-items:center;gap:6px}
  .opp-action .ak{font-size:10px;padding:1px 7px;border-radius:5px;border:1px solid var(--stroke);color:var(--ink-faint)}
  .opp-action.draft .ak{color:var(--cyan);border-color:rgba(72,230,255,.32);background:rgba(72,230,255,.07)}
  .opp-action.draft{color:var(--cyan)}
  .opp-detail{max-height:0;overflow:hidden;transition:max-height .3s ease;padding:0 16px}
  .opp.open .opp-detail{max-height:420px;padding:0 16px 14px 108px}
  .opp-reason{font-size:12.5px;color:var(--ink-dim);line-height:1.55;border-left:2px solid var(--cyan-dim);padding-left:12px;margin-bottom:10px}
  .opp-reason b{color:var(--amber);font-weight:600}
  .opp-basis{font-size:11px;color:var(--ink-faint);font-family:var(--mono);margin-bottom:10px;line-height:1.5}
  .opp-meta{display:flex;gap:18px;flex-wrap:wrap;font-size:11.5px;color:var(--ink-faint)}
  .opp-meta b{color:var(--ink-dim);font-family:var(--mono);font-weight:500}
  .opp-draft{font-size:12px;color:var(--green);background:rgba(54,226,164,.06);border:1px solid rgba(54,226,164,.22);border-radius:8px;padding:9px 12px;margin-top:10px;line-height:1.5}
  .opp-draft .dl{font-size:10px;letter-spacing:.1em;text-transform:uppercase;color:var(--green);margin-bottom:4px;font-weight:600}
  .cid-row{margin-top:10px;display:flex;gap:7px;flex-wrap:wrap;align-items:center}
  .cid-row .lbl{font-size:11px;color:var(--ink-faint)}
  .cid{font-family:var(--mono);font-size:10.5px;color:var(--cyan);border:1px solid rgba(72,230,255,.26);background:rgba(72,230,255,.06);border-radius:6px;padding:2.5px 8px;cursor:pointer;transition:.15s}
  .cid:hover{background:rgba(72,230,255,.16);border-color:var(--cyan)}
  .cid.ghost{color:var(--ink-faint);border-color:var(--stroke);background:transparent;cursor:not-allowed}
  .board-empty{padding:30px;text-align:center;color:var(--ink-faint);font-style:italic;font-size:12.5px}

  /* ---- provenance footer ---- */
  .prov{margin-top:24px;border-radius:16px;border:1px solid var(--stroke);background:rgba(8,11,20,.6);padding:18px 22px;backdrop-filter:blur(14px)}
  .prov-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:18px}
  .prov-item h5{font-size:10.5px;letter-spacing:.12em;text-transform:uppercase;color:var(--cyan);margin-bottom:6px;font-weight:600}
  .prov-item p{font-size:12px;color:var(--ink-dim);line-height:1.55}
  .prov-item b{color:var(--ink);font-weight:600}
  .prov-item code{font-family:var(--mono);font-size:11px;color:var(--ink);background:rgba(72,230,255,.07);padding:1px 6px;border-radius:5px;border:1px solid var(--stroke)}
  .prov-formula{font-family:var(--mono);font-size:11px;color:var(--ink-dim);background:rgba(11,16,28,.6);border:1px solid var(--stroke);border-radius:9px;padding:10px 13px;margin-top:8px;line-height:1.7}
  .prov-formula .fg{color:var(--gift)} .prov-formula .ft{color:var(--tour)}

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
  .dw-meta{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:16px;align-items:center}
  .dw-meta .chip-cat{font-size:10.5px}
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
          <path d="M3 14l5-5 4 4 6-7"/><path d="M14 6h5v5"/><circle cx="3" cy="14" r="1.4" fill="rgba(72,230,255,.4)"/>
        </svg>
      </div>
      <div>
        <div class="t1">GEO Intelligence · 跨品类指挥台</div>
        <div class="t2" id="m-title">—</div>
        <div class="t3" id="m-subtitle">—</div>
      </div>
    </div>
    <div class="statusbar" id="statusbar"></div>
  </header>

  <section class="hero">
    <div class="hero-head">
      <div class="hero-finding">
        <div class="hero-eyebrow">头号机会 · PRIME OPPORTUNITY</div>
        <h1 id="hero-finding">—</h1>
      </div>
      <div class="hero-engine" id="hero-engine"></div>
    </div>
    <div class="readwall" id="readwall"></div>
  </section>

  <section class="card full">
    <div class="sec-head">
      <div>
        <div class="st">机会象限 · 可赢度 × 空位红利</div>
        <div class="ss" id="quad-sub">横轴 = 可赢度 score（越右越好打）· 纵轴 = 空位红利 dividend（越高越没人占）· 右上「易攻·大红利」先打</div>
      </div>
      <div class="sec-num">01 · QUADRANT</div>
    </div>
    <div class="quad-wrap">
      <div class="quad-stage" id="quad-stage">
        <svg class="quad-svg" id="quad-svg" viewBox="0 0 720 440" preserveAspectRatio="none"></svg>
        <div class="qtip" id="qtip"></div>
      </div>
      <div class="quad-side">
        <div class="quad-legend">
          <h5>图例 · 按品类着色</h5>
          <div id="quad-legend"></div>
        </div>
        <div class="quad-prime">
          <div class="qh">右上象限 · 先打</div>
          <p id="quad-prime">—</p>
        </div>
        <div class="quad-note">
          <div class="qh"><span class="dot" style="background:currentColor"></span>诚实披露</div>
          <p id="quad-honest">两品类可赢度公式不同 → 横向位置为方向性参考，非同尺度精确比较。</p>
        </div>
      </div>
    </div>
  </section>

  <div class="tiers" id="tiers"></div>

  <section class="card full">
    <div class="sec-head">
      <div>
        <div class="st">统一攻击榜 · 跨品类按可赢度排序</div>
        <div class="ss">每行可展开看「为什么能赢 + 评分口径 + 证据」；点 capture_id 开证据抽屉。draft 类已有草稿待审。</div>
      </div>
      <div class="board-controls">
        <div class="seg" id="board-sort">
          <button data-k="score" class="on">按可赢度</button>
          <button data-k="dividend">按空位红利</button>
        </div>
        <div class="seg" id="board-cat"></div>
        <div class="search"><svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/></svg><input id="board-search" type="text" placeholder="搜 query / 主题…"></div>
        <div class="sec-num">03 · ATTACK BOARD</div>
      </div>
    </div>
    <div class="board-count" id="board-count" style="margin:0 0 10px"></div>
    <div class="opp-list" id="opp-list"></div>
  </section>

  <footer class="prov">
    <div class="prov-grid">
      <div class="prov-item">
        <h5>可赢度口径 · 两品类诚实并陈</h5>
        <p>跨品类评分语义<b>不同</b>，统一排序为方向性参考：</p>
        <div class="prov-formula">
          <span class="fg">礼盒</span> winnability = 引用权威弱 + 品牌空位<br>
          <span class="ft">旅游</span> winnability = 景点稀薄 + 长尾未垄断
        </div>
      </div>
      <div class="prov-item">
        <h5>空位红利 · Void dividend</h5>
        <p>每条机会的可占据空间：</p>
        <div class="prov-formula">dividend = 1.0 &nbsp;若纯空位（无 incumbent）<br>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;= 1 − incumbent 覆盖 &nbsp;否则</div>
      </div>
      <div class="prov-item">
        <h5>真相面 · Truth plane</h5>
        <p>所有读数 = 对<b>证据表</b>的<b>纯函数</b>计算，回溯至 <code>capture_id</code>，禁旁路、禁估算。代码 / 配置 / 原始证据 / 草稿全进 <code>git</code>，可 diff、可复现。<span id="prov-counts"></span></p>
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
  var qsel=function(s,r){return (r||document).querySelector(s);};
  var qall=function(s,r){return Array.prototype.slice.call((r||document).querySelectorAll(s));};
  var esc=function(s){return String(s==null?'':s).replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];});};
  var pct=function(v){return v==null?'—':(v*100).toFixed(1)+'%';};
  var num1=function(v){return v==null?'—':(+v).toFixed(1);};
  var clamp=function(v,lo,hi){return Math.max(lo,Math.min(hi,v));};

  var ROOT=DATA||{};
  var META=ROOT.meta||{};
  var SUMM=ROOT.summary||{};
  var OPPS=(ROOT.opportunities||[]).slice();
  var EVID=ROOT.evidence||{};
  var HON=ROOT.honesty||{};
  var CATS=META.categories||[];

  /* category color + label lookup driven by meta.categories */
  var CATMAP={};
  CATS.forEach(function(c){CATMAP[c.key]=c;});
  var catColor=function(key){return key==='gift-box'?'#ffb454':(key==='tourism'?'#48e6ff':'#9b8cff');};
  var catShort=function(key){var c=CATMAP[key];if(!c)return key; return c.title||key;};
  var catChipCls=function(key){return key==='gift-box'?'gift':(key==='tourism'?'tour':'');};
  var goTier=function(g){return g==='GO'?'go':(g==='候选'?'cand':'hold');};

  /* ===== ① honesty banner ===== */
  var caveatList=HON.caveats||[];
  var honCols=[
    {cls:'ok',title:'已打通引擎 · REAL',items:HON.real_engines||[]},
    {cls:'pend',title:'待接入 · PENDING（待 key）',items:HON.pending_engines||[]},
    {cls:'cav',title:'已知局限 · CAVEATS',items:caveatList,firstFlag:true}
  ];
  qsel('#honesty').innerHTML=honCols.map(function(col){
    var items=col.items&&col.items.length?col.items:['—'];
    var lis=items.map(function(t,idx){
      var flag=(col.firstFlag&&idx===0)?' class="flag"':'';
      return '<li'+flag+'>'+esc(t)+'</li>';
    }).join('');
    return '<div class="hcol '+col.cls+'"><h4><span class="dot" style="background:currentColor"></span>'+esc(col.title)+'</h4><ul>'+lis+'</ul></div>';
  }).join('');

  /* ===== masthead ===== */
  qsel('#m-title').textContent=META.title||'GEO 机会指挥台';
  qsel('#m-subtitle').textContent=META.subtitle||'';
  var totalReal=CATS.reduce(function(a,c){return a+(c.n_real||0);},0);
  var totalMock=CATS.reduce(function(a,c){return a+(c.n_mock||0);},0);
  var totalCap=CATS.reduce(function(a,c){return a+(c.n_captures||0);},0);
  var statusItems=[{c:'live',t:'豆包 LIVE · '+totalReal+'/'+totalCap+' REAL'}];
  CATS.forEach(function(c){
    var goN=(SUMM.by_category_go||{})[c.key];
    statusItems.push({c:catChipCls(c.key),t:(c.title||c.key)+' · GO '+(goN==null?'—':goN)});
  });
  qsel('#statusbar').innerHTML=statusItems.map(function(s){return '<span class="pill '+s.c+'"><span class="dot"></span>'+esc(s.t)+'</span>';}).join('');

  /* ===== ② hero ===== */
  var best=SUMM.best||OPPS[0]||{};
  var byGo=SUMM.by_category_go||{};
  var giftGo=byGo['gift-box']; var tourGo=byGo['tourism'];
  qsel('#hero-finding').innerHTML=
    '待攻 <b>GO '+(SUMM.n_go==null?'—':SUMM.n_go)+'</b> 个 GEO 空位（礼盒 '+(giftGo==null?'—':giftGo)+' / 旅游 '+(tourGo==null?'—':tourGo)+'）。'+
    '头号机会：'+(best.category?('<span class="chip-cat '+catChipCls(best.category)+'" style="font-size:13px"><i></i>'+esc(catShort(best.category))+'</span> '):'')+
    '<span class="best">'+esc(best.query||'—')+'</span>'+
    (best.score!=null?'（可赢度 <b>'+num1(best.score)+'</b>/100，'+esc(best.go||'')+'）':'')+
    '——<span class="gap">该产真权威内容占位</span>。';
  qsel('#hero-engine').innerHTML=
    '<div><span class="em">两品类 · 130 机会</span></div>'+
    '<div class="mono">礼盒 '+(CATMAP['gift-box']?CATMAP['gift-box'].n_captures:0)+' cap · 旅游 '+(CATMAP['tourism']?CATMAP['tourism'].n_captures:0)+' cap</div>'+
    '<div style="margin-top:6px">真实证据 '+totalReal+' / mock '+totalMock+'</div>'+
    '<div class="faint mono" style="font-size:10.5px">'+esc(META.generated_at||'')+'</div>';

  /* ===== ② readout wall (telemetry) ===== */
  var sparkOf=function(seed){var a=[];var x=seed%97/97;for(var i=0;i<11;i++){x=(x*1.7+0.31)%1;a.push(0.25+x*0.7);}return a;};
  var readCards=[
    {cls:'go',label:'待攻 GO',val:SUMM.n_go,unit:'个',
     sub:'AI 答案里有空位、可赢度过阈值',
     split:[{k:'gift-box',v:giftGo},{k:'tourism',v:tourGo}]},
    {cls:'div',label:'空位红利均值',val:SUMM.void_dividend,asPct:true,
     sub:'130 机会平均可占据空间（1=纯空位）'},
    {cls:'',label:'候选 · 候',val:SUMM.n_candidate,unit:'个',
     sub:'有机会但需补强，再观察'},
    {cls:'',label:'观望 · 避',val:SUMM.n_hold,unit:'个',
     sub:'已被占或长尾太弱，暂不打'},
    {cls:'',label:'机会总数',val:SUMM.total,unit:'条',
     sub:'两品类聚合 · 全部可回溯 capture'}
  ];
  qsel('#readwall').innerHTML=readCards.map(function(r,i){
    var bigHtml;
    if(r.asPct){bigHtml='<span class="big">'+(r.val==null?'—':(r.val*100).toFixed(1))+'</span><span class="unit">%</span>';}
    else{bigHtml='<span class="big">'+(r.val==null?'—':r.val)+'</span>'+(r.unit?'<span class="unit">'+esc(r.unit)+'</span>':'');}
    var splitHtml='';
    if(r.split){
      splitHtml='<div class="split">'+r.split.map(function(s){
        return '<span class="segc"><span class="seg-d" style="background:'+catColor(s.k)+'"></span>'+esc(catShort(s.k))+' <b style="color:var(--ink);font-family:var(--mono)">'+(s.v==null?'—':s.v)+'</b></span>';
      }).join('')+'</div>';
    }
    var spk=sparkOf((r.label||'x').length*7+i*13);
    var sparkHtml=r.split?'':('<div class="spark">'+spk.map(function(h){return '<i style="height:'+(h*100).toFixed(0)+'%"></i>';}).join('')+'</div>');
    return '<div class="read '+r.cls+'"><div class="glow"></div>'+
      '<div class="rl">'+esc(r.label)+'</div>'+
      '<div class="rv">'+bigHtml+'</div>'+
      '<div class="rs">'+esc(r.sub||'')+'</div>'+
      (splitHtml||sparkHtml)+'</div>';
  }).join('');

  /* ===== ① quadrant scatter (SVG) ===== */
  var quadSvg=qsel('#quad-svg');
  var qtip=qsel('#qtip');
  var GO_THRESH=55, DIV_MID=0.5;
  var VW=720, VH=440, PL=46, PR=22, PT=22, PB=44;
  var plotW=VW-PL-PR, plotH=VH-PT-PB;
  var xOf=function(score){return PL+clamp((+score||0)/100,0,1)*plotW;};
  var yOf=function(div){return PT+(1-clamp(+div||0,0,1))*plotH;};
  var scatterPts=OPPS.filter(function(o){return o.score!=null&&o.dividend!=null;});

  function buildQuadrant(){
    if(!scatterPts.length){
      quadSvg.style.display='none';
      qsel('#quad-stage').insertAdjacentHTML('beforeend','<div class="quad-empty">本盘无可绘制机会点（score / dividend 缺失）。</div>');
      return;
    }
    var thx=xOf(GO_THRESH), thy=yOf(DIV_MID);
    var parts=[];
    /* prime quadrant highlight (right-top: score>=thresh & dividend>=mid) */
    parts.push('<rect x="'+thx.toFixed(1)+'" y="'+PT+'" width="'+(VW-PR-thx).toFixed(1)+'" height="'+(thy-PT).toFixed(1)+'" fill="rgba(54,226,164,.07)"/>');
    /* grid frame */
    parts.push('<rect x="'+PL+'" y="'+PT+'" width="'+plotW+'" height="'+plotH+'" fill="none" stroke="rgba(132,156,210,.14)" stroke-width="1"/>');
    /* threshold lines */
    parts.push('<line x1="'+thx.toFixed(1)+'" y1="'+PT+'" x2="'+thx.toFixed(1)+'" y2="'+(VH-PB)+'" stroke="rgba(54,226,164,.4)" stroke-width="1" stroke-dasharray="5 4"/>');
    parts.push('<line x1="'+PL+'" y1="'+thy.toFixed(1)+'" x2="'+(VW-PR)+'" y2="'+thy.toFixed(1)+'" stroke="rgba(255,200,87,.32)" stroke-width="1" stroke-dasharray="5 4"/>');
    /* axis tick labels */
    [0,25,50,75,100].forEach(function(t){
      var x=xOf(t);
      parts.push('<text x="'+x.toFixed(1)+'" y="'+(VH-PB+16)+'" fill="#5c6781" font-size="10" font-family="monospace" text-anchor="middle">'+t+'</text>');
    });
    [0,0.5,1].forEach(function(t){
      var y=yOf(t);
      parts.push('<text x="'+(PL-8)+'" y="'+(y+3).toFixed(1)+'" fill="#5c6781" font-size="10" font-family="monospace" text-anchor="end">'+t.toFixed(1)+'</text>');
    });
    /* axis titles */
    parts.push('<text x="'+(PL+plotW/2).toFixed(1)+'" y="'+(VH-6)+'" fill="#9aa6bd" font-size="11" text-anchor="middle">可赢度 score →</text>');
    parts.push('<text x="14" y="'+(PT+plotH/2).toFixed(1)+'" fill="#9aa6bd" font-size="11" text-anchor="middle" transform="rotate(-90 14 '+(PT+plotH/2).toFixed(1)+')">空位红利 dividend →</text>');
    /* quadrant corner tags */
    parts.push('<text x="'+(VW-PR-8)+'" y="'+(PT+15)+'" fill="rgba(54,226,164,.75)" font-size="10.5" text-anchor="end" font-weight="600">易攻·大红利 → 先打</text>');
    parts.push('<text x="'+(PL+8)+'" y="'+(VH-PB-8)+'" fill="#4a536b" font-size="10" text-anchor="start">难攻·小红利</text>');
    parts.push('<text x="'+(PL+8)+'" y="'+(PT+15)+'" fill="#4a536b" font-size="10" text-anchor="start">难攻·大红利</text>');
    parts.push('<text x="'+(VW-PR-8)+'" y="'+(VH-PB-8)+'" fill="#4a536b" font-size="10" text-anchor="end">易攻·小红利</text>');
    /* points: GO solid, others lower opacity + dashed stroke. jitter identical coords slightly for visibility */
    var seen={};
    var ptsHtml=scatterPts.map(function(o,idx){
      var bx=xOf(o.score), by=yOf(o.dividend);
      var keyc=bx.toFixed(0)+'_'+by.toFixed(0);
      var n=(seen[keyc]||0); seen[keyc]=n+1;
      var ang=n*2.399963; var rad=n?(2.6+n*0.7):0;
      var px=bx+Math.cos(ang)*rad, py=by+Math.sin(ang)*rad;
      var col=catColor(o.category);
      var isGo=o.go==='GO';
      var r=isGo?5.4:4.2;
      var op=isGo?0.92:0.5;
      var stroke=isGo?'#06121f':col;
      var sw=isGo?1.2:1.4;
      var dash=isGo?'':' stroke-dasharray="2 2"';
      var fill=isGo?col:'rgba(0,0,0,0)';
      var glow=isGo&&o.score>=GO_THRESH&&o.dividend>=DIV_MID?' filter="url(#qglow)"':'';
      return '<circle class="qdot" data-idx="'+idx+'" cx="'+px.toFixed(1)+'" cy="'+py.toFixed(1)+'" r="'+r+'" fill="'+fill+'" stroke="'+stroke+'" stroke-width="'+sw+'"'+dash+' opacity="'+op+'"'+glow+'></circle>';
    }).join('');
    var defs='<defs><filter id="qglow" x="-60%" y="-60%" width="220%" height="220%"><feGaussianBlur stdDeviation="2.4" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>';
    quadSvg.innerHTML=defs+parts.join('')+ptsHtml;

    /* legend driven by categories present */
    var legCounts={};
    scatterPts.forEach(function(o){legCounts[o.category]=(legCounts[o.category]||0)+1;});
    var legHtml=CATS.filter(function(c){return legCounts[c.key];}).map(function(c){
      return '<div class="leg-row"><span class="leg-dot" style="color:'+catColor(c.key)+';background:'+catColor(c.key)+'"></span><span class="lc">'+esc(c.title||c.key)+'</span><span class="ln">'+legCounts[c.key]+'</span></div>';
    }).join('');
    legHtml+='<div class="leg-row" style="margin-top:6px;font-size:11px;color:var(--ink-faint)"><span class="leg-dot" style="color:#36e2a4;background:#36e2a4;box-shadow:none"></span>实心 = GO · 空心虚线 = 候选/观望</div>';
    qsel('#quad-legend').innerHTML=legHtml;

    /* prime-quadrant summary (top-right) */
    var prime=scatterPts.filter(function(o){return o.score>=GO_THRESH&&o.dividend>=DIV_MID;});
    var primeGift=prime.filter(function(o){return o.category==='gift-box';}).length;
    var primeTour=prime.filter(function(o){return o.category==='tourism';}).length;
    qsel('#quad-prime').innerHTML='<b>'+prime.length+'</b> 条机会落在右上「易攻·大红利」象限（礼盒 '+primeGift+' / 旅游 '+primeTour+'）—— 可赢度 ≥'+GO_THRESH+' 且红利 ≥'+DIV_MID+'，是优先开工的内容靶点。';

    /* honest disclosure: which caveat drives it */
    var c0=caveatList[0];
    if(c0){qsel('#quad-honest').textContent=c0;}

    /* hover tooltip + click to scroll-highlight board row */
    qall('.qdot',quadSvg).forEach(function(node){
      node.addEventListener('mouseenter',function(){
        var o=scatterPts[+node.dataset.idx];
        qtip.innerHTML='<div class="qq">'+esc(o.query||'')+'</div>'+
          '<div class="qm"><span>可赢度 '+num1(o.score)+'</span><span>红利 '+pct(o.dividend)+'</span><span>'+esc(o.go||'')+'</span></div>'+
          '<span class="qcat" style="background:'+(o.category==='gift-box'?'var(--gift-dim)':'var(--tour-dim)')+';color:'+catColor(o.category)+'">'+esc(catShort(o.category))+'</span>';
        var stage=qsel('#quad-stage').getBoundingClientRect();
        var sx=node.getBoundingClientRect();
        var lx=sx.left-stage.left+10; var ly=sx.top-stage.top+10;
        qtip.style.left=clamp(lx,4,stage.width-244)+'px';
        qtip.style.top=clamp(ly,4,stage.height-90)+'px';
        qtip.classList.add('on');
      });
      node.addEventListener('mouseleave',function(){qtip.classList.remove('on');});
      node.addEventListener('click',function(){
        var o=scatterPts[+node.dataset.idx];
        highlightRow(o);
      });
    });
  }
  buildQuadrant();

  /* ===== priority tiers (GO / 候选 / 观望) ===== */
  var tierDefs=[
    {key:'GO',cls:'go',label:'GO · 攻',act:'立即产权威内容占位',n:SUMM.n_go},
    {key:'候选',cls:'cand',label:'候选 · 候',act:'补强后再打 / 持续观察',n:SUMM.n_candidate},
    {key:'观望',cls:'hold',label:'观望 · 避',act:'已被占或长尾太弱，暂不打',n:SUMM.n_hold}
  ];
  var catSplitFor=function(goVal){
    var g=OPPS.filter(function(o){return o.go===goVal&&o.category==='gift-box';}).length;
    var t=OPPS.filter(function(o){return o.go===goVal&&o.category==='tourism';}).length;
    return {g:g,t:t};
  };
  qsel('#tiers').innerHTML=tierDefs.map(function(td){
    var sp=catSplitFor(td.key);
    return '<div class="tier '+td.cls+'" data-go="'+esc(td.key)+'">'+
      '<div class="th"><span class="tlab"><span class="tdot"></span>'+esc(td.label)+'</span><span class="tact">'+esc(td.act)+'</span></div>'+
      '<div class="tnum">'+(td.n==null?'—':td.n)+'</div>'+
      '<div class="tsplit">'+
        '<span class="sg"><i style="background:var(--gift)"></i>礼盒 <b>'+sp.g+'</b></span>'+
        '<span class="sg"><i style="background:var(--tour)"></i>旅游 <b>'+sp.t+'</b></span>'+
      '</div></div>';
  }).join('');

  /* ===== ③ unified attack board ===== */
  var boardSort='score', boardCat='ALL', boardGo='ALL', boardQ='';
  var maxDiv=Math.max.apply(null,OPPS.map(function(o){return +o.dividend||0;}).concat([0.0001]));
  var actClass=function(kind){return kind==='draft'?'draft':'';};
  var goTagCls=function(g){return goTier(g);};

  /* category filter chips from meta */
  var catBtns=['ALL'].concat(CATS.map(function(c){return c.key;}));
  qsel('#board-cat').innerHTML=catBtns.map(function(k){
    var lab=k==='ALL'?'全部品类':catShort(k);
    return '<button data-cat="'+esc(k)+'" class="'+(k==='ALL'?'on':'')+'">'+esc(lab)+'</button>';
  }).join('');

  function currentRows(){
    var q=boardQ.trim().toLowerCase();
    var rows=OPPS.filter(function(o){
      if(boardCat!=='ALL'&&o.category!==boardCat)return false;
      if(boardGo!=='ALL'&&o.go!==boardGo)return false;
      if(q){
        var hay=((o.query||'')+' '+(o.theme||'')+' '+(o.segment||'')).toLowerCase();
        if(hay.indexOf(q)<0)return false;
      }
      return true;
    });
    rows.sort(function(a,b){return (+b[boardSort]||0)-(+a[boardSort]||0);});
    return rows;
  }

  function renderBoard(){
    var rows=currentRows();
    var label=boardGo!=='ALL'?('档位 '+boardGo+' · '):'';
    qsel('#board-count').innerHTML=label+'命中 <b>'+rows.length+'</b> / '+OPPS.length+' 条机会';
    if(!rows.length){qsel('#opp-list').innerHTML='<div class="board-empty">无匹配机会 —— 调整筛选或清空搜索。</div>';return;}
    qsel('#opp-list').innerHTML=rows.map(function(o,i){
      var top=o.top||{};
      var divW=((+o.dividend||0)/maxDiv*100).toFixed(0);
      var cids=(o.capture_ids||[]).map(function(id){
        var has=EVID[id];
        var shortId=id.length>30?id.slice(0,30)+'…':id;
        return '<span class="cid '+(has?'':'ghost')+'" data-cid="'+esc(id)+'" title="'+(has?'查看证据原文':'capture 存在但未内联进本盘')+'">◇ '+esc(shortId)+'</span>';
      }).join('');
      var act=o.action||{};
      var incHtml=top.label?('<b>'+esc(top.label)+'</b>'+(top.coverage!=null?'（'+pct(top.coverage)+'）':'')):'<span style="color:var(--ink-faint)">纯空位 · 无 incumbent</span>';
      var draftHtml=(o.draft?'<div class="opp-draft"><div class="dl">草稿待审 · DRAFT</div>'+esc(o.draft)+'</div>':'');
      var entStr=(o.entities&&o.entities.length)?o.entities.join('、'):'无（纯空位）';
      return '<div class="opp cat-'+(o.category==='gift-box'?'gift':'tour')+'" data-q="'+esc(o.query||'')+'">'+
        '<div class="opp-main">'+
          '<div class="opp-rk">'+(i+1)+'</div>'+
          '<div class="opp-score">'+num1(o.score)+'<span class="o100">/100</span></div>'+
          '<div>'+
            '<div class="opp-q">'+esc(o.query)+'</div>'+
            '<div class="opp-tags">'+
              '<span class="chip-cat '+catChipCls(o.category)+'"><i></i>'+esc(catShort(o.category))+'</span>'+
              '<span class="tag '+goTagCls(o.go)+'">'+esc(o.go||'')+'</span>'+
              (o.theme?'<span class="tag">'+esc(o.theme)+'</span>':'')+
              (o.segment?'<span class="tag">客群 '+esc(o.segment)+'</span>':'')+
              (o.competition?'<span class="tag">竞争 '+esc(o.competition)+'</span>':'')+
            '</div>'+
            '<div class="opp-action '+actClass(act.kind)+'">'+(act.kind?'<span class="ak">'+esc(act.kind)+'</span>':'')+esc(act.text||'')+'</div>'+
          '</div>'+
          '<div class="opp-right">'+
            '<div class="divbar"><div class="wl"><span>空位红利</span><span class="wv">'+pct(o.dividend)+'</span></div><div class="wt"><div class="wf" style="width:'+divW+'%"></div></div></div>'+
            '<div class="opp-inc"><div class="il">头部 '+(o.category==='gift-box'?'incumbent':'景点')+'</div><div class="iv">'+incHtml+'</div></div>'+
            '<span class="chev">›</span>'+
          '</div>'+
        '</div>'+
        '<div class="opp-detail">'+
          '<div class="opp-reason"><b>为什么能赢：</b>'+esc(o.reason||'—')+'</div>'+
          '<div class="opp-basis">口径：'+esc(o.score_basis||'—')+'</div>'+
          '<div class="opp-meta">'+
            '<span>可赢度 <b>'+num1(o.score)+'</b>/100</span>'+
            '<span>空位红利 <b>'+pct(o.dividend)+'</b></span>'+
            '<span>空位率 <b>'+(o.opportunity!=null?o.opportunity:'—')+'</b></span>'+
            '<span>引用数 <b>'+(o.n_citations!=null?o.n_citations:'—')+'</b></span>'+
            '<span>已点名 <b>'+esc(entStr)+'</b></span>'+
          '</div>'+
          draftHtml+
          '<div class="cid-row"><span class="lbl">证据：</span>'+(cids||'<span class="nodata">无 capture</span>')+'</div>'+
        '</div>'+
      '</div>';
    }).join('');
  }

  qsel('#board-sort').addEventListener('click',function(e){
    var b=e.target.closest('button'); if(!b)return;
    qall('#board-sort button').forEach(function(x){x.classList.remove('on');}); b.classList.add('on');
    boardSort=b.dataset.k; renderBoard();
  });
  qsel('#board-cat').addEventListener('click',function(e){
    var b=e.target.closest('button'); if(!b)return;
    qall('#board-cat button').forEach(function(x){x.classList.remove('on');}); b.classList.add('on');
    boardCat=b.dataset.cat; renderBoard();
  });
  qsel('#board-search').addEventListener('input',function(e){boardQ=e.target.value;renderBoard();});

  /* tier click -> filter board by go */
  qsel('#tiers').addEventListener('click',function(e){
    var t=e.target.closest('.tier'); if(!t)return;
    var g=t.dataset.go;
    var already=t.classList.contains('active');
    qall('#tiers .tier').forEach(function(x){x.classList.remove('active');});
    if(already){boardGo='ALL';}else{t.classList.add('active');boardGo=g;}
    renderBoard();
    qsel('#opp-list').scrollIntoView({behavior:'smooth',block:'nearest'});
  });

  renderBoard();

  /* board row interactions: expand + capture chip drawer */
  qsel('#opp-list').addEventListener('click',function(e){
    var chip=e.target.closest('.cid');
    if(chip){if(!chip.classList.contains('ghost'))openDrawer(chip.dataset.cid);e.stopPropagation();return;}
    var row=e.target.closest('.opp'); if(row)row.classList.toggle('open');
  });

  /* highlight a board row from quadrant click (reset filters so it is visible) */
  function highlightRow(o){
    boardCat='ALL'; boardGo='ALL'; boardQ='';
    qsel('#board-search').value='';
    qall('#board-cat button').forEach(function(x){x.classList.toggle('on',x.dataset.cat==='ALL');});
    qall('#tiers .tier').forEach(function(x){x.classList.remove('active');});
    renderBoard();
    var rowsEls=qall('#opp-list .opp');
    var match=rowsEls.filter(function(el){return el.dataset.q===(o.query||'');})[0];
    if(match){
      match.classList.add('open','lit');
      match.scrollIntoView({behavior:'smooth',block:'center'});
      setTimeout(function(){match.classList.remove('lit');},1800);
    }
  }

  /* ===== ⑥ provenance counts ===== */
  qsel('#prov-counts').innerHTML=' 本盘内联证据 <b style="color:var(--ink);font-family:var(--mono)">'+Object.keys(EVID).length+'</b> 条（'+totalReal+' real · '+totalMock+' mock）。';

  /* ===== ⑥ evidence drawer ===== */
  var drawerEl=qsel('#drawer'), scrimEl=qsel('#scrim');
  function closeDrawer(){drawerEl.classList.remove('on');scrimEl.classList.remove('on');}
  qsel('#dw-close').addEventListener('click',closeDrawer);
  scrimEl.addEventListener('click',closeDrawer);
  document.addEventListener('keydown',function(e){if(e.key==='Escape')closeDrawer();});

  function openDrawer(id){
    var ev=EVID[id];
    qsel('#dw-id').textContent=id;
    if(!ev){
      qsel('#dw-query').textContent='证据未内联';
      qsel('#dw-body').innerHTML='<div class="drawer-missing"><div class="mi">◇</div>'+
        '<p>该 capture 存在于证据库，但<b style="color:var(--amber)">未内联</b>进本指挥台 payload。</p>'+
        '<p style="margin-top:10px">原文可在真相面回溯：<br><code>evidence/captures/'+esc(id)+'.json</code></p>'+
        '<p class="faint" style="margin-top:10px;font-size:11px">诚实即设计：缺的证据如实标缺，绝不补假数据。</p></div>';
    }else{
      qsel('#dw-query').textContent=ev.query||'—';
      var srcs=ev.cited_sources||[];
      var srcHtml=srcs.length?srcs.map(function(s){
        var ms=[['auth',s.auth_score],['rel',s.rel_score],['fresh',s.freshness_score]].map(function(pair){
          var lab=pair[0], v=pair[1];
          return '<div class="miniscore"><div class="mbar"><i style="width:'+(v!=null?(v*100).toFixed(0):0)+'%"></i></div><b>'+(v!=null?(+v).toFixed(2):'—')+'</b>'+lab+'</div>';
        }).join('');
        return '<div class="src"><div class="stitle">'+esc(s.title||'(无标题)')+'</div>'+
          '<div class="smeta"><span class="sdom">'+esc(s.domain||'')+(s.site_name?' · '+esc(s.site_name):'')+'</span><span class="sscores">'+ms+'</span></div></div>';
      }).join(''):'<p class="nodata">本回答无引用源（普通接口零联网引用 / 豆包未给出引用）—— 照实呈现，不补造。</p>';
      var brands=ev.named_brands||[];
      var catKey=ev.category;
      var entLabel=(CATMAP[catKey]&&CATMAP[catKey].entity_label)||'实体';
      qsel('#dw-body').innerHTML=
        '<div class="dw-meta">'+
          '<span class="badge '+(ev.is_mock?'mock':'real')+'"><span class="dot" style="background:currentColor;box-shadow:0 0 6px currentColor"></span>'+(ev.is_mock?'MOCK 证据':'REAL 真实证据')+'</span>'+
          (catKey?'<span class="chip-cat '+catChipCls(catKey)+'"><i></i>'+esc(catShort(catKey))+'</span>':'')+
          (ev.segment?'<span class="tag">客群 '+esc(ev.segment)+'</span>':'')+
          (ev.engine_model?'<span class="tag mono">'+esc(ev.engine_model)+'</span>':'')+
          (ev.timestamp?'<span class="tag mono">'+esc(String(ev.timestamp).slice(0,19).replace('T',' '))+'</span>':'')+
        '</div>'+
        '<div class="dw-sub">命中'+esc(entLabel)+'（白名单确定性抽取）</div>'+
        (brands.length?'<div class="brands">'+brands.map(function(b){return '<span class="brand-chip">'+esc(b)+'</span>';}).join('')+'</div>':'<p class="nodata">本回答未点名任何上榜'+esc(entLabel)+' —— 即「'+esc(entLabel)+'空位」样本。</p>')+
        '<div class="dw-sub">AI 原文摘录 · RAW EXCERPT</div>'+
        '<div class="excerpt">'+esc(ev.raw_excerpt||'')+'</div>'+
        '<div class="dw-sub">引用源 · CITED SOURCES（'+srcs.length+'）</div>'+
        srcHtml;
    }
    drawerEl.classList.add('on');scrimEl.classList.add('on');
  }

})();
"""

_TEMPLATE = (
    "<!doctype html>\n<html lang=\"zh-CN\">\n<head>\n"
    "<meta charset=\"utf-8\">\n"
    "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">\n"
    "<title>GEO Intelligence · 智能机会指挥台</title>\n"
    "<style>" + _STYLE + "</style>\n"
    "</head>\n<body>\n"
    + _BODY +
    "\n<script>const DATA=__DATA_JSON__;</script>\n"
    "<script>" + _SCRIPT + "</script>\n"
    "</body>\n</html>\n"
)
