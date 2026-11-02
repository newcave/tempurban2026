# -*- coding: utf-8 -*-
"""주민 Agent · ABM — 주민 유형 6종, 가구 Agent 민원 발생·확산, 유형별 목소리"""
import plotly.graph_objects as go
import streamlit as st

from urb import agents as A
from urb import catalog as C
from urb import data as D
from urb import ui

ui.page_header("Resident agents · ABM", "주민 Agent와 ABM",
               "가구를 주민 Agent로 두고, 유형별 민감도 × 그 달의 공급 갭으로 민원 확률을 정한 뒤 같은 블록 이웃의 민원이 다시 확률을 올리는 "
               "확산까지 시뮬레이션합니다. 목소리는 LLM 페르소나 자리에 넣은 템플릿입니다.",
               ["1 Agent = 10세대", "유형 6종", "LLM 미연결 · 템플릿"])

c0, c1, c2 = st.columns([1.2, 1.2, 1], gap="medium")
with c0:
    z = ui.zone_select("생활권", key="zone_res", zones=[k for k in C.ZONES if k != "MTV-R"])
with c1:
    sid = st.selectbox("비교 시나리오", list(C.SCENARIOS)[1:], index=4, format_func=lambda k: C.SCENARIOS[k]["name"], key="res_scn")
with c2:
    cg = st.slider("이웃 확산 강도", 0.0, 1.5, 0.8, .1, key="res_cg", help="이웃 민원이 내 민원 확률을 올리는 최대 효과(로짓)")

lv = C.SCENARIOS[sid]["levers"]
base_df = D.simulate(z)
alt_df = D.simulate(z, D.key(lv))
r0 = D.abm(z, (), cg)
r1 = D.abm(z, D.key(lv), cg)
f = base_df.attrs["first"]
win = lambda m: m[(m.t >= f) & (m.t < f + 48)]  # noqa: E731
n0, n1 = win(r0["monthly"]).n.sum(), win(r1["monthly"]).n.sum()
byp = win(r0["monthly"]).groupby("persona").n.sum().sort_values(ascending=False)
alarm = int((win(r0["block"]).groupby("t").salience.max() > .8).sum())
ui.kpis([
    {"label": "가구 Agent", "value": f"{r0['agents']:,}", "unit": "개", "sub": f"{base_df.attrs['total_hh']:,}세대 · 블록 {len(base_df.attrs['plan']['blocks'])}", "color": ui.ACCENT},
    {"label": "48개월 민원 (기준)", "value": f"{n0:,}", "unit": "건", "sub": f"첫 입주 {C.ym(f)}부터", "color": "#94a3b8"},
    {"label": f"48개월 민원 ({C.SCENARIOS[sid]['name'][:1]})", "value": f"{n1:,}", "unit": "건",
     "delta": f"{(n1 / n0 - 1) * 100:+.0f}%" if n0 else None, "up": n1 <= n0, "sub": "확산 포함", "color": C.SCN_COLORS[sid]},
    {"label": "민원 최다 유형", "value": C.PERSONAS[byp.index[0]]["name"] if len(byp) else "-",
     "sub": f"{byp.iloc[0] / n0 * 100:.0f}%" if n0 else "", "color": C.PERSONAS[byp.index[0]]["color"] if len(byp) else ui.ACCENT},
    {"label": "확산 경보 개월", "value": f"{alarm}", "unit": "개월", "sub": "블록 이슈 체감도 > 0.8 (기준)", "color": "#f87171"},
])

with ui.card("types", "주민 Agent 유형", "구성비 · 민감도(어떤 불편에 반응하나) · 주 접수 채널", "Personas"):
    cards = []
    for pid, P in C.PERSONAS.items():
        w = [x / sum(P["w"]) for x in P["w"]]
        bars = "".join(f'<div class="tk"><span class="n">{C.VOC_CATS[k]["label"]}</span><span class="b"><i style="width:{w[i] * 100 / max(w):.0f}%;'
                       f'background:{P["color"]}"></i></span><span class="v">{w[i] * 100:.0f}%</span></div>' for i, k in enumerate(C.GAP_CATS) if w[i] > 0)
        cards.append(f'<div class="ag" style="border-top:3px solid {P["color"]}"><div class="top"><b>{P["name"]}</b>'
                     f'<span class="st" style="color:{P["color"]};background:{P["color"]}1f;border:1px solid {P["color"]}55">{P["share"] * 100:.0f}%</span></div>'
                     f'<p>{P["desc"]} · 주 채널 {P["channel"]}</p><div class="tks">{bars}</div></div>')
    ui.h('<div class="agents">' + "".join(cards) + "</div>")

c1, c2 = st.columns([1.5, 1], gap="medium")
with c1:
    with ui.card("abm", "ABM 월별 민원 (유형별)", f"영역 = {C.SCENARIOS[sid]['name']} · 점선 = 기준계획 합계 · 3개월 이동평균", "ABM"):
        m1 = r1["monthly"].groupby(["t", "persona"]).n.sum().unstack(fill_value=0)
        m0 = r0["monthly"].groupby("t").n.sum()
        lo, hi = max(0, f - 3), min(C.HORIZON, f + 54)
        idx = range(lo, hi)
        m1 = m1.reindex(idx, fill_value=0).rolling(3, min_periods=1).mean()
        x = [C.ym(t) for t in idx]
        fig = go.Figure()
        for pid in C.PERSONAS:
            if pid in m1:
                fig.add_scatter(x=x, y=m1[pid], name=C.PERSONAS[pid]["name"], stackgroup="a", mode="none",
                                fillcolor=C.PERSONAS[pid]["color"] + "b0", hovertemplate=C.PERSONAS[pid]["name"] + " %{y}건<extra></extra>")
        fig.add_scatter(x=x, y=m0.reindex(idx, fill_value=0).rolling(3, min_periods=1).mean(), name="기준계획 합계",
                        line=dict(color="#e2e8f0", width=1.6, dash="dot"))
        ui.style(fig, 330)
        fig.update_xaxes(type="category", nticks=10)
        ui.plot(fig, "res_abm")
with c2:
    with ui.card("diff", "블록별 이슈 체감도 (확산)", "이웃 민원의 지수평활 → 0~1 · 기준계획", "Diffusion"):
        b = r0["block"]
        b = b[(b.t >= lo) & (b.t < hi)]
        fig = go.Figure()
        pal = ["#a78bfa", "#22d3ee", "#f59e0b"]
        for i, (blk, g) in enumerate(b.groupby("block")):
            fig.add_scatter(x=[C.ym(t) for t in g.t], y=g.salience, name=blk, line=dict(color=pal[i % 3], width=2, shape="spline"))
        fig.add_hline(y=.8, line=dict(color="#f87171", dash="dash", width=1), annotation_text="경보", annotation_font=dict(color="#f87171", size=10))
        ui.style(fig, 330)
        fig.update_xaxes(type="category", nticks=6)
        fig.update_yaxes(range=[0, 1.05])
        ui.plot(fig, "res_diff")

with ui.card("voice", "주민 Agent 목소리", "기준계획 상황에서의 한마디 + 비교 시나리오가 시행되면 (LLM 자리 · 지금은 템플릿)", "Voices"):
    tv = st.select_slider("시점", options=list(range(f, min(C.HORIZON - 1, f + 42) + 1)), value=min(max(C.NOW_T, f + 3), f + 42),
                          format_func=C.ym, key="res_t", help="첫 입주 이후 42개월까지")
    st.caption(f"{C.ym(tv)} · 첫 입주 후 {tv - f}개월")
    vs = sorted([A.voice(p, A.drivers_at(base_df, tv), A.drivers_at(alt_df, tv)) for p in C.PERSONAS], key=lambda x: -x["level"])
    ui.h('<div class="voice">' + "".join(
        f'<div class="v"><div class="av" style="background:{v["color"]}">{v["name"][:2]}</div><div class="bb"><b>{v["name"]}</b>'
        f'<em>체감 불편 {v["level"] * 100:.0f}</em><p>{ui.esc(v["text"])}</p></div></div>' for v in vs) + "</div>")

with ui.card("xcheck", "두 모형 교차 확인", "집계모형(VOC 기대건수) vs ABM(가구 Agent 합계) — 기준계획", "Check"):
    agg = base_df.set_index("t")["voc"].reindex(idx)
    fig = go.Figure()
    fig.add_scatter(x=x, y=agg, name="집계모형", line=dict(color="#22d3ee", width=2))
    fig.add_scatter(x=x, y=m0.reindex(idx, fill_value=0), name="ABM", line=dict(color="#a78bfa", width=2))
    ui.style(fig, 260)
    fig.update_xaxes(type="category", nticks=10)
    ui.plot(fig, "res_xcheck")
    ui.note("ABM은 이웃 확산 때문에 집계모형보다 봉우리가 높고 대안 효과도 크게 나옵니다. 실제 VOC 패턴으로 확산 강도를 보정하는 것이 PoC 과제입니다.")
