# -*- coding: utf-8 -*-
"""What-if — 표준 시나리오 상대비교 · 직접 만드는 대안 · ±20% 민감도 · 다목적(VOC·비용·공정) 탐색"""
import plotly.graph_objects as go
import streamlit as st

from urb import catalog as C
from urb import data as D
from urb import sim as S
from urb import ui

ui.page_header("What-if decision support", "What-if 시나리오",
               "기준계획 대비 대안을 같은 조건에서 돌려 상대비교합니다. 절대 건수보다 <b>대안 간 순위</b>가 판단 근거이고, "
               "±20% 민감도로 그 순위가 흔들리는지 확인합니다. 레버마다 누가 결정할 수 있는지(주체)도 함께 봅니다.",
               ["평가 구간 = 첫 입주 후 48개월", "비용·효과 계수는 예시값"])

z = ui.zone_select("생활권", key="zone_wi", zones=[k for k in C.ZONES if k != "MTV-R"],
                   help="김포 1생활권은 계획 단계 — 레버가 가장 많이 남은 시점의 적용 조건 검토용")
cmp_ = D.compare(z)
base = cmp_.iloc[0]

with ui.card("cmp", "표준 시나리오 상대비교", "PoC 정량목표: 시나리오 5건 내외 · 통학·통근 접근성, 생활불편, VOC 위험등급, 추가비용, 공정영향", "Compare"):
    owners = {"S0": "-", "S1": C.LEVERS["school_shift"]["owner"], "S2": C.LEVERS["transit_boost"]["owner"],
              "S3": C.LEVERS["temp"]["owner"], "S4": C.LEVERS["volume_shift"]["owner"], "S5": "K-water + 협의"}
    t = cmp_.assign(owner=cmp_.id.map(owners))[["name", "voc_total", "voc_delta", "inconv", "commute", "school", "bad_months", "cost", "delay", "owner"]]
    st.dataframe(t.rename(columns={"name": "시나리오", "voc_total": "VOC(48개월)", "voc_delta": "VOC 변화%", "inconv": "생활불편",
                                   "commute": "통근(분)", "school": "통학(분)", "bad_months": "D·E등급 개월", "cost": "추가비용(억)",
                                   "delay": "공정(+개월)", "owner": "레버 주체"}),
                 hide_index=True,
                 column_config={"VOC(48개월)": st.column_config.NumberColumn(format="%.0f"),
                                "VOC 변화%": st.column_config.NumberColumn(format="%+.1f"),
                                "생활불편": st.column_config.NumberColumn(format="%.1f"),
                                "통근(분)": st.column_config.NumberColumn(format="%.1f"),
                                "통학(분)": st.column_config.NumberColumn(format="%.1f"),
                                "추가비용(억)": st.column_config.NumberColumn(format="%.0f")})
    picks = st.multiselect("그래프에 넣을 시나리오", list(C.SCENARIOS), default=list(C.SCENARIOS),
                           format_func=lambda k: C.SCENARIOS[k]["name"], key="wi_picks")
    fig = go.Figure()
    f0 = D.simulate(z).attrs["first"]
    for sid in picks:
        d = D.simulate(z, D.key(C.SCENARIOS[sid]["levers"]))
        d = d[(d.t >= f0 - 3) & (d.t < f0 + 54)]
        fig.add_scatter(x=d.ym, y=d.voc, name=C.SCENARIOS[sid]["name"],
                        line=dict(color=C.SCN_COLORS[sid], width=3 if sid == "S0" else 2, dash="dot" if sid == "S0" else "solid", shape="spline"))
    ui.style(fig, 320)
    fig.update_xaxes(type="category", nticks=10)
    fig.update_yaxes(title="VOC 기대건수(건/월)")
    ui.plot(fig, "wi_lines")

c1, c2 = st.columns([1, 1.25], gap="medium")
with c1:
    with ui.card("build", "대안 직접 만들기", "레버를 움직이면 바로 다시 계산합니다", "Builder"):
        lv = {}
        for k, L in C.LEVERS.items():
            step = 1 if L["max"] > 1 else .25
            lv[k] = st.slider(f"{L['label']} · {L['owner']}", 0.0 if step < 1 else 0, float(L["max"]) if step < 1 else int(L["max"]),
                              0.0 if step < 1 else 0, step, key=f"wi_{k}", help=L["unit"])
        lv = {k: v for k, v in lv.items() if v}
with c2:
    my = D.simulate(z, D.key(lv))
    k1 = S.kpis(my, lv)
    k0 = S.kpis(D.simulate(z), {})
    with ui.card("myres", "내 대안 결과", "기준계획 대비", "Result"):
        dv = (k1["voc_total"] / k0["voc_total"] - 1) * 100 if k0["voc_total"] else 0
        ui.kpis([
            {"label": "VOC (48개월)", "value": f"{k1['voc_total']:,.0f}", "unit": "건", "delta": f"{dv:+.1f}%", "up": dv <= 0, "sub": "", "color": ui.ACCENT},
            {"label": "생활불편지수", "value": f"{k1['inconv']:.1f}", "delta": f"{k1['inconv'] - k0['inconv']:+.1f}p", "up": k1["inconv"] <= k0["inconv"], "color": "#f59e0b"},
            {"label": "추가비용", "value": f"{k1['cost']:.0f}", "unit": "억", "sub": f"공정 +{k1['delay']:.0f}개월", "color": "#f472b6"},
        ])
        d0 = D.simulate(z)
        w0 = d0[(d0.t >= f0 - 3) & (d0.t < f0 + 54)]
        w1 = my[(my.t >= f0 - 3) & (my.t < f0 + 54)]
        fig = go.Figure()
        fig.add_scatter(x=w0.ym, y=w0.voc, name="기준계획", line=dict(color="#94a3b8", width=2, dash="dot"))
        fig.add_scatter(x=w1.ym, y=w1.voc, name="내 대안", fill="tonexty", line=dict(color="#a78bfa", width=2.4), fillcolor="rgba(167,139,250,.15)")
        ui.style(fig, 230)
        fig.update_xaxes(type="category", nticks=8)
        ui.plot(fig, "wi_my")
        if lv.get("bridge_shift"):
            ui.note("광역교통 조기 개통은 K-water가 정할 수 없는 외부 변수입니다. '이렇게 되면'을 보는 용도로만 쓰세요.")

c1, c2 = st.columns([1, 1.25], gap="medium")
with c1:
    with ui.card("sens", "±20% 민감도", "내 대안 기준 · 막대 = VOC(48개월) 변화 건수", "Sensitivity"):
        s, b = D.sensitivity(z, D.key(lv))
        fig = go.Figure()
        fig.add_bar(y=s.label, x=s.low, orientation="h", name="−20%", marker_color="#22d3ee", hovertemplate="%{y} −20% · %{x:+.0f}건<extra></extra>")
        fig.add_bar(y=s.label, x=s.high, orientation="h", name="+20%", marker_color="#a78bfa", hovertemplate="%{y} +20% · %{x:+.0f}건<extra></extra>")
        ui.style(fig, 300)
        fig.update_layout(barmode="overlay")
        ui.plot(fig, "wi_sens")
        ui.note("가장 긴 막대의 값부터 실측 보정이 필요합니다. 기본 발생률은 모든 대안을 같이 움직여 순위에는 영향이 작습니다.")
with c2:
    with ui.card("pareto", "다목적 탐색 (54개 조합)", "학교 0/3/6개월 × 교통 0/50/100% × 임시대책 유무 × 물량 0/3/6개월", "Multi-objective"):
        a, b_, c_ = st.columns(3)
        wv = a.slider("VOC 가중", 0, 100, 50, 5, key="wi_wv")
        wc = b_.slider("비용 가중", 0, 100, 30, 5, key="wi_wc")
        wd = c_.slider("공정 가중", 0, 100, 20, 5, key="wi_wd")
        only = st.toggle("K-water가 정할 수 있는 레버만 (임시대책·물량)", key="wi_only")
        g = D.search(z).copy()
        if only:
            g = g[(g.school_shift == 0) & (g.transit_boost == 0)]
        g["score"] = S.score(g, wv, wc, wd)
        fig = go.Figure()
        fig.add_scatter(x=g.cost, y=g.voc_cut, mode="markers",
                        marker=dict(size=[13 if p else 8 for p in g.pareto], color=g.score, colorscale=[[0, "#334155"], [1, "#a78bfa"]],
                                    line=dict(color=["#f5d0fe" if p else "rgba(0,0,0,0)" for p in g.pareto], width=1.5),
                                    colorbar=dict(title="점수", thickness=8, len=.8)),
                        customdata=g[["school_shift", "transit_boost", "temp", "volume_shift", "delay"]],
                        hovertemplate="학교 %{customdata[0]}개월 · 교통 %{customdata[1]:.0%} · 임시 %{customdata[2]:.0f} · 물량 %{customdata[3]}개월"
                                      "<br>비용 %{x:.0f}억 · VOC %{y:.1f}%↓ · 공정 +%{customdata[4]:.0f}개월<extra></extra>")
        ui.style(fig, 280, legend=False)
        fig.update_xaxes(title="추가비용(억)")
        fig.update_yaxes(title="VOC 감소(%)")
        ui.plot(fig, "wi_pareto")
        top = g.sort_values("score", ascending=False).head(5)
        ui.ranked([{"label": " + ".join(x for x in [f"학교 {r.school_shift}개월" if r.school_shift else "", f"교통 {r.transit_boost:.0%}" if r.transit_boost else "",
                                                     "임시대책" if r.temp else "", f"물량 {r.volume_shift}개월" if r.volume_shift else ""] if x) or "기준계획",
                    "sub": f"VOC {-r.voc_cut:+.1f}% · {r.cost:.0f}억 · +{r.delay:.0f}개월", "value": r.score} for r in top.itertuples()],
                  fmt="{:.0f}점", max_val=100)
        ui.note("테두리 = 파레토 안(VOC·비용·공정 어느 쪽으로도 더 나은 안이 없는 조합).")
