# -*- coding: utf-8 -*-
"""사업지 · 공정 — 생애주기 단계, 블록 공정표, 입주 대비 공급, 공급-수요 갭, 단계별 프로파일 비교"""
from datetime import datetime

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from urb import catalog as C
from urb import data as D
from urb import ui


def dt(t):
    return datetime.strptime(C.ym(t), "%Y-%m")


ui.page_header("Sites · Phases", "사업지와 공정",
               "블록별 공정·입주 일정과 학교·교통·상권·공원 공급 시점을 겹쳐 보고, 어디서 공급이 수요를 못 따라가는지(갭) 확인합니다.",
               ["가상 공급 계획", f"기준월 <b>{C.ym(C.NOW_T)}</b>"])

c0, c1 = st.columns([2, 1], gap="medium")
with c0:
    cur_site = C.ZONES[st.session_state.get("zone_shared", "EDC-A")]["site"]
    site = st.segmented_control("사업지", list(C.SITES), default=cur_site, format_func=lambda k: C.SITES[k]["full"], key="site_pick") or cur_site
with c1:
    zones = [k for k, v in C.ZONES.items() if v["site"] == site]
    z = ui.zone_select("생활권", key="zone_sites", zones=zones)

S = C.SITES[site]
stage_i = C.LIFECYCLE.index(S["stage"])
ui.h('<div class="lc">' + "".join(
    f'<div class="{"on" if i == stage_i else "done" if i < stage_i else ""}">{s}</div>' for i, s in enumerate(C.LIFECYCLE)) + "</div>")

df = D.simulate(z)
plan = df.attrs["plan"]
first = plan["first"]
tnow = min(max(C.NOW_T, 0), C.HORIZON - 1)
now = df.iloc[tnow]
ui.kpis([
    {"label": "계획 세대", "value": f"{df.attrs['total_hh']:,}", "unit": "세대", "sub": f"블록 {len(plan['blocks'])}개", "color": S["color"]},
    {"label": "첫 입주", "value": C.ym(first), "sub": f"{S['role']}", "color": "#22d3ee"},
    {"label": f"입주율 ({C.ym(tnow)})", "value": f"{now['H'] / df.attrs['total_hh'] * 100:.0f}", "unit": "%",
     "sub": f"{now['H']:,.0f}세대", "spark": list(df["H"].iloc[max(0, tnow - 23):tnow + 1]), "color": ui.ACCENT},
    {"label": "첫 학교 개교", "value": C.ym(min(t for t, _ in plan["school"])), "sub": f"학교 {len(plan['school'])}곳 계획", "color": "#f59e0b"},
    {"label": "교통 수용 단계", "value": f"{len(plan['transit'])}", "unit": "단계",
     "sub": " · ".join(f"{C.ym(t)}({o})" for t, _, o in sorted(plan["transit"])[:3]), "color": "#f472b6"},
])

with ui.card("gantt", "블록 공정표와 시설 공급 시점", "막대 = 블록 공정 · 세로선 = 개교·교통 개통·공원 개방 · 굵은 선 = 기준월", "Schedule"):
    rows = []
    for b, hh, t0 in plan["blocks"]:
        for ph, a, e in C.PHASES:
            rows.append({"블록": f"{b} · {ph}", "공정": ph, "세대": f"{hh:,}세대",
                         "시작": dt(max(0, t0 + a)), "끝": dt(min(C.HORIZON - 1, max(0, t0 + e)))})
    import pandas as pd
    gdf = pd.DataFrame(rows)
    gdf = gdf[gdf["끝"] > gdf["시작"]]
    fig = px.timeline(gdf, x_start="시작", x_end="끝", y="블록", color="공정", color_discrete_map=C.PHASE_COLORS, hover_data=["세대"])
    fig.update_yaxes(autorange="reversed", title=None)
    marks = [(t, "개교", "#f59e0b") for t, _ in plan["school"]] + [(t, f"교통({o})", "#f472b6") for t, _, o in plan["transit"]] + \
            [(t, "공원", "#34d399") for t, _ in plan["park"]]
    for t, lab, col in marks:
        if 0 <= t < C.HORIZON:
            fig.add_vline(x=dt(t), line=dict(color=col, width=1, dash="dot"))
            fig.add_annotation(x=dt(t), y=1.02, yref="paper", text=lab, showarrow=False, font=dict(size=10, color=col), textangle=-30)
    fig.add_vline(x=dt(tnow), line=dict(color="#e2e8f0", width=2))
    ui.style(fig, 90 + 26 * len(gdf), legend=False, margin=dict(l=10, r=14, t=50, b=10))
    ui.plot(fig, "st_gantt")

lo, hi = max(0, first - 12), min(C.HORIZON, first + 60)
w = df.iloc[lo:hi]
c1, c2 = st.columns(2, gap="medium")
with c1:
    with ui.card("supply", "입주 대비 공급", "왼쪽: 입주 세대 vs 교통 수용 · 오른쪽: 학생 수요 vs 학교 정원", "Supply"):
        fig = make_subplots(rows=1, cols=2, horizontal_spacing=.12)
        fig.add_scatter(x=w.ym, y=w.H, name="입주 세대", fill="tozeroy", line=dict(color="#a78bfa", width=2), row=1, col=1)
        fig.add_scatter(x=w.ym, y=w.transit_cap, name="교통 수용", line=dict(color="#f472b6", width=2, shape="hv"), row=1, col=1)
        fig.add_scatter(x=w.ym, y=w.H * .30, name="학생 수요", fill="tozeroy", line=dict(color="#22d3ee", width=2), row=1, col=2)
        fig.add_scatter(x=w.ym, y=w.seats, name="학교 정원", line=dict(color="#f59e0b", width=2, shape="hv"), row=1, col=2)
        ui.style(fig, 300)
        fig.update_xaxes(type="category", nticks=6)
        ui.plot(fig, "st_supply")
with c2:
    with ui.card("gap", "공급-수요 갭", "칸 색 = 부족률(0~100%) · 공사 강도는 인접 공사 물량 비중", "Gap"):
        cats = C.GAP_CATS
        fig = go.Figure(go.Heatmap(z=[w[f"g_{k}"] * 100 for k in cats], x=w.ym, y=[C.VOC_CATS[k]["driver"] for k in cats],
                                   colorscale=[[0, "#0f172a"], [.35, "#4c1d95"], [.7, "#a78bfa"], [1, "#f5d0fe"]], zmin=0, zmax=100,
                                   hovertemplate="%{y} · %{x} · %{z:.0f}%<extra></extra>", colorbar=dict(thickness=8, len=.8, ticksuffix="%")))
        ui.style(fig, 300, legend=False)
        fig.update_xaxes(type="category", nticks=6)
        ui.plot(fig, "st_gap")

with ui.card("profile", "단계별 프로파일 비교", "x = 첫 입주 후 경과 개월 · y = 1천 세대당 월 VOC 기대건수 (입주 300세대 이상 구간)", "Compare"):
    fig = go.Figure()
    for zid, zz in C.ZONES.items():
        d = D.simulate(zid)
        f = d.attrs["first"]
        dd = d[(d.t >= max(0, f - 6)) & (d.t < f + 54)]
        col = C.SITES[zz["site"]]["color"]
        fig.add_scatter(x=dd.t - f, y=dd.per1000, name=zz["name"], mode="lines",
                        line=dict(color=col, width=3 if zid == z else 1.6, dash="solid" if zz.get("poc") or zid == z else "dot"),
                        hovertemplate=zz["name"] + " · %{x}개월 · %{y:.1f}건<extra></extra>")
    for hi_, g, c in C.RISK_BANDS[:4]:
        fig.add_hline(y=hi_, line=dict(color=c, width=1, dash="dash"), annotation_text=f"{g}/{chr(ord(g) + 1)}",
                      annotation_font=dict(size=10, color=c), annotation_position="right")
    ui.style(fig, 320)
    fig.update_xaxes(title="첫 입주 후 개월")
    fig.update_yaxes(title="건/1천 세대·월")
    ui.plot(fig, "st_profile")
    ui.note("시화MTV는 2022년 이전 입주분이 화면 기간 밖이라 일부만 보입니다. 김포는 계획 단계라 전 구간이 예측값입니다.")
