# -*- coding: utf-8 -*-
"""화면 부품 — water-tech-agent2(Water Co-Scientist 쇼케이스)의 디자인 시스템을 그대로 가져와 Urban AI 색으로 바꿈.
고정 상단바 · 카드 그리드 · 지표 타일 · 다크 Plotly. CSS는 이 파일에만 둔다."""
import html
import re
from contextlib import contextmanager

import plotly.graph_objects as go
import streamlit as st

ACCENT, ACCENT2, GOOD, BAD = "#a78bfa", "#22d3ee", "#34d399", "#f87171"
TEXT, MUTED, DIM, LINE, PANEL = "#e2e8f0", "#94a3b8", "#64748b", "#1e293b", "#0f172a"
FONT = "'Pretendard Variable', Pretendard, 'Noto Sans KR', 'Apple SD Gothic Neo', sans-serif"
PLOT_CONFIG = {"displayModeBar": False, "responsive": True}
esc = html.escape

CSS = """
<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css');
:root { --bg:#070d1a; --panel:#0f172a; --panel2:#111c33; --line:#1e293b; --line2:#26344f; --text:#e2e8f0;
        --muted:#94a3b8; --dim:#64748b; --accent:#a78bfa; --accent2:#22d3ee; --good:#34d399; --bad:#f87171; }
html, body, .stApp, .stApp p, .stApp span, .stApp div, .stApp button, .stApp input, .stApp label { font-family: 'Pretendard Variable', Pretendard, 'Noto Sans KR', sans-serif; }
[data-testid="stIconMaterial"], .material-symbols-rounded { font-family: 'Material Symbols Rounded' !important; }
[data-testid="stMarkdownContainer"] > p:empty { display:none; } .stMarkdown { margin-bottom: 0; }
.stApp { background: radial-gradient(1100px 520px at 85% -10%, rgba(167,139,250,.10), transparent 60%),
                     radial-gradient(900px 480px at -10% 10%, rgba(59,130,246,.10), transparent 60%), var(--bg); }
/* Streamlit 기본 장치 숨기기 */
[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="stStatusWidget"],
[data-testid="stSidebarCollapsedControl"], footer, #MainMenu { display:none !important; }
[data-testid="stMainBlockContainer"] { max-width: 1440px; padding: 0 28px 48px; }
[data-testid="stVerticalBlock"] { gap: 14px; }
/* 상단바 */
.st-key-topbar { position: sticky; top: 0; z-index: 1000; margin: 0 -28px 6px; padding: 10px 28px;
  background: rgba(7,13,26,.82); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); border-bottom: 1px solid var(--line); }
.brand { display:flex; align-items:center; gap:12px; text-decoration:none; }
.brand svg { width:34px; height:34px; }
.brand b { display:block; color:#fff; font-size:1.02rem; letter-spacing:-.01em; line-height:1.15; }
.brand span { display:block; color:var(--dim); font-size:.72rem; letter-spacing:.06em; }
.st-key-topnav [data-testid="stPageLink"] a { padding: 7px 13px; border-radius: 9px; transition: background .15s; }
.st-key-topnav [data-testid="stPageLink"] a p, .st-key-topnav [data-testid="stPageLink"] a span { color: var(--muted) !important; font-size: .9rem; font-weight: 500; }
.st-key-topnav [data-testid="stPageLink"] a:hover { background: rgba(148,163,184,.08); }
[class*="st-key-navon"] [data-testid="stPageLink"] a { background: rgba(167,139,250,.10); box-shadow: inset 0 -2px 0 var(--accent); }
[class*="st-key-navon"] [data-testid="stPageLink"] a p, [class*="st-key-navon"] [data-testid="stPageLink"] a span { color: #f3efff !important; }
.live { display:inline-flex; align-items:center; gap:7px; padding:5px 11px; border-radius:999px; font-size:.74rem; color:#a7f3d0;
  background: rgba(52,211,153,.08); border:1px solid rgba(52,211,153,.25); white-space:nowrap; }
.live i { width:7px; height:7px; border-radius:50%; background: var(--good); box-shadow:0 0 0 0 rgba(52,211,153,.6); animation: pulse 2s infinite; }
@keyframes pulse { 0% {box-shadow:0 0 0 0 rgba(52,211,153,.55);} 70% {box-shadow:0 0 0 8px rgba(52,211,153,0);} 100% {box-shadow:0 0 0 0 rgba(52,211,153,0);} }
/* 페이지 머리 */
.ph { display:flex; justify-content:space-between; align-items:flex-end; gap:18px; flex-wrap:wrap; padding: 10px 0 2px; }
.ph .eb { color: var(--accent); font-size:.72rem; letter-spacing:.18em; text-transform:uppercase; font-weight:600; }
.ph h1 { margin: 4px 0 6px; padding:0; color:#fff; font-size: clamp(1.5rem, 2.6vw, 2.05rem); font-weight: 700; letter-spacing:-.02em; }
.ph p { margin:0; color: var(--muted); max-width: 78ch; font-size:.95rem; }
.chips { display:flex; gap:8px; flex-wrap:wrap; }
.chip { font-size:.74rem; color: var(--muted); border:1px solid var(--line2); background: rgba(15,23,42,.6); padding:5px 10px; border-radius:8px; white-space:nowrap; }
.chip b { color: var(--text); font-weight:600; }
/* 지표 타일 */
.kpis { display:grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 14px; }
.kpi { position:relative; overflow:hidden; background: linear-gradient(180deg, rgba(17,28,51,.95), rgba(15,23,42,.95)); border:1px solid var(--line);
  border-radius: 14px; padding: 16px 16px 12px; }
.kpi::before { content:""; position:absolute; left:0; top:0; bottom:0; width:3px; background: var(--c, var(--accent)); }
.kpi .l { color: var(--muted); font-size: .78rem; font-weight: 500; display:flex; align-items:center; gap:6px; }
.kpi .v { color:#fff; font-size: 1.85rem; font-weight: 700; letter-spacing:-.02em; margin-top: 4px; font-variant-numeric: tabular-nums; }
.kpi .v small { font-size: .95rem; color: var(--muted); font-weight: 500; margin-left: 3px; }
.kpi .d { font-size:.76rem; margin-top: 2px; color: var(--dim); }
.kpi .d .up { color: var(--good); font-weight:600; } .kpi .d .dn { color: var(--bad); font-weight:600; }
.kpi svg.spark { position:absolute; right:14px; top:14px; width: 84px; height: 30px; opacity:.95; }
.kpi.sp .l { padding-right: 92px; }
/* 카드 */
[class*="st-key-card-"] { background: linear-gradient(180deg, rgba(17,28,51,.92), rgba(15,23,42,.92)); border:1px solid var(--line);
  border-radius: 16px; padding: 16px 18px 20px; box-shadow: 0 18px 40px -28px rgba(0,0,0,.8); }
.ch { display:flex; justify-content:space-between; align-items:flex-start; gap:10px; }
.ch .t { color: #f1f5f9; font-size: .98rem; font-weight: 650; letter-spacing:-.01em; }
.ch .s { color: var(--dim); font-size: .78rem; margin-top: 2px; }
.ch .tag { font-size:.68rem; letter-spacing:.12em; text-transform:uppercase; color: var(--accent); border:1px solid rgba(167,139,250,.3);
  border-radius:6px; padding:2px 7px; white-space:nowrap; }
.note { color: var(--dim); font-size: .76rem; line-height:1.5; margin: 2px 0 4px; }
/* 순위 목록 */
.rk { display:grid; gap: 9px; margin-top: 4px; }
.rk .r { display:grid; grid-template-columns: 20px minmax(0,1fr) auto; gap: 4px 10px; align-items:center; }
.rk .n { color: var(--dim); font-size:.74rem; font-variant-numeric: tabular-nums; }
.rk .k { color: var(--text); font-size: .86rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.rk .k em { font-style:normal; color: var(--dim); font-size:.74rem; margin-left:6px; }
.rk .val { color: #fff; font-size:.86rem; font-weight:600; font-variant-numeric: tabular-nums; }
.rk .bar { grid-column: 2 / 4; height: 4px; border-radius: 4px; background: rgba(148,163,184,.12); overflow:hidden; }
.rk .bar i { display:block; height:100%; border-radius:4px; }
/* 히어로 */
.hero { position:relative; overflow:hidden; border-radius: 18px; border:1px solid var(--line2); padding: 30px 32px;
  background: linear-gradient(120deg, rgba(38,24,82,.95) 0%, rgba(14,20,44,.95) 55%, rgba(8,47,73,.9) 100%); }
.hero svg.waves { position:absolute; inset:auto 0 0 0; width:100%; height: 100%; opacity:.5; pointer-events:none; }
.hero .in { position:relative; display:grid; grid-template-columns: minmax(0, 1.25fr) minmax(0, 1fr); gap: 26px; align-items:center; }
.hero .eb { color: var(--accent); font-size:.74rem; letter-spacing:.2em; text-transform:uppercase; font-weight:600; }
.hero h1 { color:#fff; font-size: clamp(1.8rem, 3.4vw, 2.75rem); line-height:1.15; letter-spacing:-.03em; margin: 8px 0 12px; padding:0; font-weight:800; }
.hero h1 span { background: linear-gradient(90deg, #c4b5fd, #67e8f9); -webkit-background-clip:text; background-clip:text; color: transparent; }
.hero p { color:#b6c7dc; font-size: 1rem; line-height:1.65; margin:0; max-width: 56ch; }
.hero .facts { display:grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: 12px; }
.hero .f { background: rgba(7,13,26,.45); border:1px solid rgba(148,163,184,.16); border-radius: 12px; padding: 12px 14px; }
.hero .f b { display:block; color:#fff; font-size: 1.45rem; font-weight:700; font-variant-numeric: tabular-nums; letter-spacing:-.02em; }
.hero .f span { color: var(--muted); font-size:.78rem; }
/* 단계 흐름 */
.flow { display:grid; grid-template-columns: repeat(5, minmax(0,1fr)); gap: 10px; margin-top: 6px; }
.flow .st { position:relative; background: rgba(7,13,26,.5); border:1px solid var(--line); border-radius: 12px; padding: 12px; }
.flow .st:not(:last-child)::after { content:"›"; position:absolute; right:-10px; top: 40%; color: var(--accent); font-size:1.1rem; }
.flow .st .i { font-size: .7rem; color: var(--accent); letter-spacing:.12em; font-weight:700; }
.flow .st b { display:block; color:#fff; font-size:.92rem; margin: 3px 0 4px; }
.flow .st span { display:block; color: var(--muted); font-size:.76rem; line-height:1.45; }
/* 에이전트 */
.agents { display:grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 12px; }
.ag { background: rgba(7,13,26,.5); border:1px solid var(--line); border-radius: 12px; padding: 12px 14px; }
.ag .top { display:flex; justify-content:space-between; align-items:center; }
.ag b { color:#fff; font-size:.9rem; }
.ag .st { font-size:.7rem; padding:2px 8px; border-radius:999px; font-weight:600; }
.ag p { color: var(--muted); font-size:.78rem; margin: 6px 0 0; line-height:1.45; }
/* 기술 지도 */
.tmstat { display:grid; grid-template-columns: repeat(3, minmax(0,1fr)); gap: 12px; }
.tmstat .s { background: rgba(7,13,26,.5); border:1px solid var(--line); border-radius: 12px; padding: 12px 14px; }
.tmstat .h { display:flex; justify-content:space-between; align-items:center; gap:8px; }
.tmstat b { color:#fff; font-size:.9rem; } .tmstat p { color: var(--muted); font-size:.76rem; margin:8px 0 0; line-height:1.45; }
.pill { font-size:.7rem; padding:2px 9px; border-radius:999px; font-weight:600; white-space:nowrap; border:1px solid; }
.pill.ok { color:#a7f3d0; background:rgba(52,211,153,.10); border-color:rgba(52,211,153,.35); }
.pill.run { color:#ddd6fe; background:rgba(167,139,250,.10); border-color:rgba(167,139,250,.35); }
.pill.wait { color:#fcd34d; background:rgba(245,158,11,.10); border-color:rgba(245,158,11,.35); }
.pill.bad { color:#fecaca; background:rgba(248,113,113,.10); border-color:rgba(248,113,113,.35); }
.pb { height:5px; border-radius:5px; background: rgba(148,163,184,.12); overflow:hidden; margin-top:9px; }
.pb i { display:block; height:100%; border-radius:5px; background: linear-gradient(90deg, #a78bfa, #22d3ee); }
.ql { display:grid; gap: 12px; }
.ql .q { border-left: 3px solid var(--qc); padding: 2px 0 2px 12px; }
.ql .qh { display:flex; align-items:baseline; gap:8px; } .ql .qh b { color:#fff; font-size:.92rem; }
.ql .qh .c { color: var(--qc); font-weight:700; font-size:1.05rem; font-variant-numeric: tabular-nums; }
.ql .qh span.d { color: var(--dim); font-size:.74rem; }
.ql .us { display:flex; flex-wrap:wrap; gap:6px; margin-top:7px; }
.ql .u { font-size:.76rem; color: var(--text); background: rgba(148,163,184,.08); border:1px solid var(--line2); border-radius:7px; padding:3px 8px; white-space:nowrap; }
.ql .u i { display:inline-block; width:7px; height:7px; border-radius:50%; margin-right:6px; vertical-align:middle; }
.ql .none { color: var(--dim); font-size:.76rem; margin-top:5px; }
.qlg { display:flex; flex-wrap:wrap; gap: 6px 16px; color: var(--muted); font-size:.78rem; margin: 2px 0 2px; }
.qlg i { display:inline-block; width:11px; height:11px; border-radius:3px; margin-right:6px; vertical-align:-1px; }
.fx { display:grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: 8px; }
.fx div { background: rgba(7,13,26,.5); border:1px solid var(--line); border-radius: 10px; padding: 8px 10px; }
.fx span { display:block; color: var(--dim); font-size:.72rem; } .fx b { color:#fff; font-size:1.02rem; font-variant-numeric: tabular-nums; }
.fx b small { color: var(--muted); font-size:.74rem; font-weight:500; margin-left:2px; }
.badge { display:inline-block; font-size:.78rem; font-weight:650; padding:4px 11px; border-radius:8px; border:1px solid; }
.tps { display:flex; flex-wrap:wrap; gap:6px; margin-top:6px; }
.tps span { font-size:.74rem; color:#cbd5e1; border:1px dashed var(--line2); border-radius:7px; padding:3px 8px; }
.tps span em { font-style:normal; color: var(--dim); margin-left:4px; }
.disc { counter-reset: d; display:grid; gap:8px; margin: 4px 0 2px; }
.disc div { position:relative; padding-left: 30px; color: var(--muted); font-size:.82rem; line-height:1.55; }
.disc div::before { counter-increment: d; content: counter(d); position:absolute; left:0; top:1px; width:20px; height:20px; border-radius:6px;
  background: rgba(167,139,250,.12); color: var(--accent); font-size:.72rem; font-weight:700; display:flex; align-items:center; justify-content:center; }
.disc b { color: var(--text); }
/* 수집 현황 */
.nxs { display:grid; gap:7px; margin:6px 0 10px; }
.nx { display:grid; grid-template-columns: 10px minmax(0,1fr) auto auto; gap:10px; align-items:center; padding:6px 10px;
  background: rgba(7,13,26,.5); border:1px solid var(--line); border-radius:10px; }
.nx .dot { width:8px; height:8px; border-radius:50%; background: var(--accent); animation: glow 2s ease-in-out infinite; }
@keyframes glow { 0%,100% { opacity:1; } 50% { opacity:.3; } }
.nx b { color:#fff; font-size:.86rem; } .nx .w { color: var(--dim); font-size:.74rem; font-variant-numeric: tabular-nums; }
.nx .l { color: var(--accent); font-size:.8rem; font-weight:600; font-variant-numeric: tabular-nums; min-width:62px; text-align:right; }
.fns { display:grid; gap:11px; margin-top:6px; }
.fn .fh { display:flex; justify-content:space-between; align-items:baseline; gap:8px; font-size:.84rem; }
.fn .fh span { color: var(--muted); font-size:.76rem; font-variant-numeric: tabular-nums; } .fn .fh span b { color:#fff; }
.fn .fb { position:relative; height:9px; border-radius:6px; background: rgba(148,163,184,.08); margin-top:5px; overflow:hidden; }
.fn .fb i { position:absolute; left:0; top:0; bottom:0; border-radius:6px; }
.tks { display:grid; gap:7px; margin-top:6px; }
.tk { display:grid; grid-template-columns: minmax(0,1.3fr) minmax(0,1fr) auto; gap:10px; align-items:center; }
.tk .n { color: var(--text); font-size:.8rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.tk .b { height:6px; border-radius:6px; background: rgba(148,163,184,.12); overflow:hidden; }
.tk .b i { display:block; height:100%; border-radius:6px; background: linear-gradient(90deg, #199e70, #34d399); }
.tk .v { color:#fff; font-size:.78rem; font-variant-numeric: tabular-nums; min-width:96px; text-align:right; } .tk .v em { color: var(--dim); font-style:normal; }
.term { border:1px solid #1f2a40; border-radius:12px; overflow:hidden; background:#050a14; margin-top:6px; }
.term .bar { display:flex; align-items:center; gap:6px; padding:8px 12px; background:#0b1324; border-bottom:1px solid #1f2a40; }
.term .bar i { width:10px; height:10px; border-radius:50%; background:#f87171; } .term .bar i:nth-child(2) { background:#fbbf24; }
.term .bar i:nth-child(3) { background:#34d399; } .term .bar span { color: var(--dim); font-size:.72rem; margin-left:8px; font-family: ui-monospace, Menlo, Consolas, monospace; }
.term .body { max-height: 430px; overflow-y:auto; padding:10px 12px; font-family: ui-monospace, 'JetBrains Mono', Menlo, Consolas, monospace; font-size:.74rem; line-height:1.65; }
.term .ln { display:flex; gap:10px; white-space:nowrap; } .term .t { color:#475569; } .term .ok { color:#34d399; } .term .bad { color:#f87171; }
.term .run { color:#a78bfa; animation: blink 1.2s steps(1) infinite; } .term .dim { color:#64748b; } .term .evi { color:#c084fc; }
.term .wf { color:#93c5fd; min-width:150px; } .term .lb { color:#cbd5e1; min-width:96px; } .term .ev { color:#64748b; min-width:120px; }
.term .du { color:#fde047; } .term .msg { color:#e2e8f0; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.term .cur { color:#a78bfa; animation: blink 1s steps(1) infinite; }
@keyframes blink { 50% { opacity:0; } }
.scl { display:grid; gap:10px; margin-top:6px; }
.sc { display:grid; grid-template-columns: minmax(0,1.4fr) minmax(0,1fr) auto; gap:12px; align-items:center; }
.sc .k { color: var(--text); font-size:.84rem; } .sc .b { height:8px; border-radius:6px; background: rgba(148,163,184,.1); overflow:hidden; }
.sc .b i { display:block; height:100%; border-radius:6px; }
.sc .v { color:#fff; font-weight:650; font-size:.95rem; font-variant-numeric: tabular-nums; min-width:110px; text-align:right; }
.sc .v em { color: var(--dim); font-style:normal; font-size:.74rem; margin-left:3px; font-weight:500; }
a.live { text-decoration:none; } a.live:hover { background: rgba(52,211,153,.16); }
/* 눈에 덜 띄는 내려받기 (기술 지도 검토표) */
.st-key-tm_dl { margin-top:-6px; }
.st-key-tm_dl button { padding:0 2px !important; min-height:0 !important; }
.st-key-tm_dl button p, .st-key-tm_dl button span { font-size:.74rem !important; color: var(--dim) !important; }
.st-key-tm_dl button:hover p, .st-key-tm_dl button:hover span { color: var(--muted) !important; }
.foot { color: var(--dim); font-size:.74rem; text-align:center; padding: 22px 0 6px; border-top:1px solid var(--line); margin-top: 10px; }
.foot a { color: var(--muted); }
/* 위젯 살짝 */
[data-testid="stSegmentedControl"] button, [data-testid="stButtonGroup"] button { font-size:.82rem; }
[data-testid="stWidgetLabel"] p { color: var(--muted) !important; font-size:.78rem !important; }
@media (max-width: 900px) {
  .hero .in { grid-template-columns: minmax(0,1fr); }
  .flow { grid-template-columns: minmax(0,1fr); } .flow .st::after { display:none; }
  .tmstat { grid-template-columns: minmax(0,1fr); }
  [data-testid="stMainBlockContainer"] { padding: 0 14px 40px; } .st-key-topbar { margin: 0 -14px 6px; padding: 10px 14px; }
}
/* ── Urban AI 추가 ── */
[data-testid="stMarkdownContainer"]:has(> div) { margin-bottom: 0 !important; }   /* HTML 조각이 카드 아래 테두리를 덮지 않게 */
.demo { display:inline-flex; align-items:center; padding:5px 10px; border-radius:999px; font-size:.72rem; color:#fde68a;
  background: rgba(245,158,11,.08); border:1px solid rgba(245,158,11,.3); white-space:nowrap; margin-right:8px; }
.lc { display:grid; grid-template-columns: repeat(7, minmax(0,1fr)); gap:6px; margin:6px 0 2px; }
.lc div { text-align:center; padding:9px 4px; border-radius:9px; font-size:.78rem; color: var(--dim); border:1px solid var(--line); background: rgba(7,13,26,.5); }
.lc div.done { color: var(--muted); border-color: var(--line2); }
.lc div.on { color:#fff; font-weight:700; border-color: var(--accent); background: rgba(167,139,250,.14); box-shadow: inset 0 -2px 0 var(--accent); }
.sites { display:grid; grid-template-columns: repeat(auto-fit, minmax(230px,1fr)); gap:12px; }
.site { background: rgba(7,13,26,.5); border:1px solid var(--line); border-radius:12px; padding:13px 14px; border-top:3px solid var(--c); }
.site b { color:#fff; font-size:.95rem; } .site .r { color: var(--c); font-size:.74rem; font-weight:600; margin-top:2px; }
.site p { color: var(--muted); font-size:.78rem; margin:7px 0 0; line-height:1.5; }
.qs { display:grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap:10px; }
.qs div { background: rgba(7,13,26,.5); border:1px solid var(--line); border-left:3px solid var(--accent); border-radius:10px; padding:10px 12px; }
.qs b { display:block; color:#fff; font-size:.86rem; } .qs span { color: var(--muted); font-size:.76rem; }
.path { display:flex; flex-wrap:wrap; align-items:center; gap:6px; margin:6px 0; }
.path span { font-size:.78rem; color:#fff; background: rgba(248,113,113,.1); border:1px solid rgba(248,113,113,.35); border-radius:8px; padding:4px 9px; }
.path i { color: var(--dim); font-style:normal; }
.voice { display:grid; gap:9px; }
.voice .v { display:grid; grid-template-columns: 34px minmax(0,1fr); gap:10px; align-items:start; }
.voice .av { width:34px; height:34px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-weight:700; font-size:.78rem; color:#0b1020; }
.voice .bb { background: rgba(7,13,26,.55); border:1px solid var(--line); border-radius: 4px 12px 12px 12px; padding:9px 12px; }
.voice .bb b { color:#fff; font-size:.82rem; } .voice .bb p { margin:3px 0 0; color: var(--text); font-size:.82rem; line-height:1.55; }
.voice .bb em { font-style:normal; color: var(--dim); font-size:.72rem; margin-left:6px; }
.cls { display:grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap:8px; margin-top:8px; }
.cls div { background: rgba(7,13,26,.5); border:1px solid var(--line); border-radius:10px; padding:8px 10px; }
.cls span { display:block; color: var(--dim); font-size:.72rem; } .cls b { color:#fff; font-size:.92rem; }
.answer { background: rgba(167,139,250,.06); border:1px solid rgba(167,139,250,.25); border-radius:12px; padding:12px 14px; }
.layer { font-size:.66rem; letter-spacing:.1em; color: var(--dim); text-transform:uppercase; }
@media (max-width: 900px) { .lc { grid-template-columns: repeat(4, minmax(0,1fr)); } .qs, .cls { grid-template-columns: minmax(0,1fr); } }
</style>
"""

LOGO = """<svg viewBox="0 0 40 40" aria-hidden="true"><defs><linearGradient id="lg" x1="0" y1="0" x2="1" y2="1">
<stop offset="0" stop-color="#c4b5fd"/><stop offset="1" stop-color="#22d3ee"/></linearGradient></defs>
<rect x="2" y="2" width="36" height="36" rx="10" fill="url(#lg)"/>
<g fill="#0b1020"><rect x="8" y="20" width="6" height="12" rx="1"/><rect x="16" y="13" width="7" height="19" rx="1"/><rect x="25" y="17" width="7" height="15" rx="1"/></g>
<path d="M23 6h11a2 2 0 0 1 2 2v6a2 2 0 0 1-2 2h-6l-4 3v-3h-1a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2Z" fill="#0b1020"/>
<g fill="#c4b5fd"><circle cx="26" cy="11" r="1.1"/><circle cx="29" cy="11" r="1.1"/><circle cx="32" cy="11" r="1.1"/></g></svg>"""


def h(body: str, width="stretch"):
    """HTML 조각 출력 — st.html은 SVG를 걸러 내므로 st.markdown(unsafe_allow_html) 사용.
    줄바꿈·들여쓰기는 공백 하나로 접어 마크다운이 코드 블록으로 읽지 않게 함."""
    body = re.sub(r"\s*\n\s*", " ", body).replace("~", "&#126;").replace("$", "&#36;")   # 마크다운 취소선·수식 오해 방지
    st.markdown(body, unsafe_allow_html=True, width=width)


def inject():
    st.html(CSS)


def topbar(pages: list, current):
    with st.container(key="topbar", horizontal=True, horizontal_alignment="distribute", vertical_alignment="center"):
        h(f'<div class="brand">{LOGO}<div><b>Urban AI</b><span>VOC 기반 도시개발 전주기 AI 시뮬레이션</span></div></div>',
          width="content")
        with st.container(key="topnav", horizontal=True, vertical_alignment="center", width="content", gap="small"):
            for i, p in enumerate(pages):
                with st.container(key=("navon" if p.title == current.title else f"nav{i}"), width="content"):
                    st.page_link(p, label=p.title, icon=p.icon)
            h('<span class="demo">가상 데이터</span><a class="live" href="./agents" target="_self"><i></i>LIVE · 실행 기록</a>', width="content")


def page_header(eyebrow: str, title: str, desc: str, chips=()):
    ch = "".join(f'<span class="chip">{c}</span>' for c in chips)
    h(f'<div class="ph"><div><div class="eb">{esc(eyebrow)}</div><h1>{esc(title)}</h1><p>{desc}</p></div>'
            f'<div class="chips">{ch}</div></div>')


def spark(values, color=ACCENT, w=96, h=34):
    v = [float(x or 0) for x in values or []]
    if len(v) < 2:
        return ""
    lo, hi = min(v), max(v)
    rng = (hi - lo) or 1
    pts = [(i * (w - 4) / (len(v) - 1) + 2, h - 3 - (x - lo) / rng * (h - 8)) for i, x in enumerate(v)]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    area = f"2,{h} " + line + f" {w - 2},{h}"
    gid = f"g{abs(hash((tuple(v), color))) % 10**8}"
    return (f'<svg class="spark" viewBox="0 0 {w} {h}" preserveAspectRatio="none"><defs><linearGradient id="{gid}" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0" stop-color="{color}" stop-opacity=".35"/><stop offset="1" stop-color="{color}" stop-opacity="0"/></linearGradient></defs>'
            f'<polygon points="{area}" fill="url(#{gid})"/><polyline points="{line}" fill="none" stroke="{color}" stroke-width="1.8" '
            f'stroke-linejoin="round" stroke-linecap="round"/><circle cx="{pts[-1][0]:.1f}" cy="{pts[-1][1]:.1f}" r="2.4" fill="{color}"/></svg>')


def kpis(tiles: list):
    """tiles: dict(label, value, unit='', delta=None(str), up=True|False|None, sub='', color=, spark=[...])"""
    out = []
    for t in tiles:
        d = ""
        if t.get("delta"):
            cls = "up" if t.get("up") else "dn" if t.get("up") is False else ""
            d = f'<span class="{cls}">{t["delta"]}</span> '
        sp = " sp" if t.get("spark") and len(t["spark"]) > 1 else ""
        out.append(f'<div class="kpi{sp}" style="--c:{t.get("color", ACCENT)}"><div class="l">{esc(t["label"])}</div>'
                   f'<div class="v">{t["value"]}<small>{t.get("unit", "")}</small></div>'
                   f'<div class="d">{d}{t.get("sub", "")}</div>{spark(t.get("spark"), t.get("color", ACCENT))}</div>')
    h(f'<div class="kpis">{"".join(out)}</div>')


@contextmanager
def card(key: str, title: str, sub: str = "", tag: str = ""):
    with st.container(key=f"card-{key}"):
        h(f'<div class="ch"><div><div class="t">{esc(title)}</div>'
                + (f'<div class="s">{sub}</div>' if sub else "") + "</div>"
                + (f'<span class="tag">{esc(tag)}</span>' if tag else "") + "</div>")
        yield


def ranked(rows: list, fmt="{:.1f}%", color=ACCENT, max_val=None):
    """rows: dict(label, value, sub='', color=)"""
    mx = max_val or max((r["value"] or 0) for r in rows) or 1
    out = []
    for i, r in enumerate(rows, 1):
        w = max(2, (r["value"] or 0) / mx * 100)
        c = r.get("color", color)
        out.append(f'<div class="r"><span class="n">{i:02d}</span><span class="k">{esc(r["label"])}'
                   + (f'<em>{esc(r["sub"])}</em>' if r.get("sub") else "")
                   + f'</span><span class="val">{fmt.format(r["value"])}</span>'
                   f'<span class="bar"><i style="width:{w:.1f}%;background:{c}"></i></span></div>')
    h(f'<div class="rk">{"".join(out)}</div>')


def note(text: str):
    h(f'<div class="note">{text}</div>')


def footer(updated: str):
    h(f'<div class="foot">tempurban2026 · Urban AI 기획연구 시연판 · <b>모든 수치는 가상 데이터</b>이며 실제 사업 계획·민원 통계가 아닙니다 · '
      f'계수·대안 비용은 예시값 · 갱신 {esc(updated)}</div>')


def style(fig: go.Figure, height=320, legend=True, margin=None):
    fig.update_layout(
        height=height, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, color="#cbd5e1", size=12), margin=margin or dict(l=10, r=14, t=34, b=10),
        hoverlabel=dict(bgcolor="#0b1222", bordercolor="#26344f", font=dict(family=FONT, color="#e2e8f0", size=12)),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0, bgcolor="rgba(0,0,0,0)", font=dict(size=11, color=MUTED)),
        showlegend=legend, hovermode="closest")
    fig.update_xaxes(automargin=True, gridcolor="rgba(148,163,184,.10)", zeroline=False, linecolor="rgba(148,163,184,.18)",
                     tickfont=dict(color=MUTED, size=11), title_font=dict(color=DIM, size=11))
    fig.update_yaxes(automargin=True, gridcolor="rgba(148,163,184,.10)", zeroline=False, linecolor="rgba(148,163,184,.18)",
                     tickfont=dict(color=MUTED, size=11), title_font=dict(color=DIM, size=11))
    return fig


def plot(fig, key):
    st.plotly_chart(fig, theme=None, config=PLOT_CONFIG, key=key, width="stretch")


def fmt_pct(v, plus=True, nd=0):
    if v is None:
        return "–"
    return (f"{v:+.{nd}f}%" if plus else f"{v:.{nd}f}%")


def zone_select(label="생활권", key="zone", zones=None, help=None):
    """화면 사이에서 고른 생활권을 이어 쓴다."""
    from . import catalog as C
    opts = list(zones or C.ZONES)
    cur = st.session_state.get("zone_shared", "EDC-A")
    idx = opts.index(cur) if cur in opts else 0
    z = st.selectbox(label, opts, index=idx, format_func=lambda k: C.ZONES[k]["name"], key=key, help=help)
    st.session_state["zone_shared"] = z
    return z


def bar_answer(chart: dict, key: str, height=260):
    """에이전트 답변에 딸린 작은 차트."""
    import plotly.graph_objects as go
    if not chart:
        return
    d = chart["data"]
    k = chart["kind"]
    fig = go.Figure()
    if k == "bar":
        fig.add_bar(x=d[chart["x"]], y=d[chart["y"]], marker_color=list(d["color"]) if "color" in d else ACCENT,
                    hovertemplate="%{x} · %{y:,.1f}<extra></extra>")
    elif k == "line":
        fig.add_scatter(x=d[chart["x"]], y=d[chart["y"]], mode="lines+markers", line=dict(color=ACCENT, width=2.4, shape="spline"),
                        hovertemplate="%{x} · %{y:,.1f}건<extra></extra>")
        fig.update_xaxes(type="category", nticks=8)
    elif k == "scatter":
        fig.add_scatter(x=d["cost"], y=d["voc_cut"], mode="markers",
                        marker=dict(size=9, color=["#a78bfa" if p else "#475569" for p in d["pareto"]], line=dict(width=0)),
                        hovertemplate="비용 %{x:.0f}억 · VOC %{y:.1f}% 감소<extra></extra>")
        fig.update_xaxes(title="추가비용(억)")
        fig.update_yaxes(title="VOC 감소(%)")
    elif k == "tornado":
        fig.add_bar(y=d["label"], x=d["low"], orientation="h", name="−20%", marker_color="#22d3ee")
        fig.add_bar(y=d["label"], x=d["high"], orientation="h", name="+20%", marker_color="#a78bfa")
        fig.update_layout(barmode="overlay")
    style(fig, height, legend=(k == "tornado"), margin=dict(l=10, r=14, t=30, b=10))
    fig.update_layout(title=dict(text=chart.get("title", ""), font=dict(size=12, color=MUTED), x=0, y=.98))
    plot(fig, key)
