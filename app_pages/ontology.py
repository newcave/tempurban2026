# -*- coding: utf-8 -*-
"""온톨로지 — 전주기 클래스·관계, 인과 경로, ISO/IEC 5087-1 대응 후보, 데이터 인벤토리(예시)"""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from urb import ontology as O
from urb import ui

g = O.graph()
ui.page_header("Ontology v0", "도시개발 전주기 온톨로지",
               "사업지·공정·시설·가구·VOC·대안을 한 구조로 묶은 초안입니다. 에이전트는 이 구조로 질문과 민원을 연결하고, "
               "인과 경로를 따라 원인을 설명합니다. v1 확정은 2차년도 과제입니다.",
               [f"클래스 <b>{g.number_of_nodes()}</b>", f"관계 <b>{g.number_of_edges()}</b>", "초안 · 검토용"])

c1, c2 = st.columns([1.6, 1], gap="medium")
with c1:
    with ui.card("graph", "클래스와 관계", "색 = 묶음(공간·공정·공급·수요·인과·평가) · 선에 마우스를 올리면 관계 이름", "Graph"):
        pos = O.LAYOUT
        fig = go.Figure()
        for a, b, d in g.edges(data=True):
            (x0, y0), (x1, y1) = pos[a], pos[b]
            fig.add_annotation(x=x1, y=y1, ax=x0, ay=y0, xref="x", yref="y", axref="x", ayref="y", showarrow=True,
                               arrowhead=2, arrowsize=1, arrowwidth=1.1, arrowcolor="rgba(148,163,184,.35)", standoff=11, startstandoff=9, text="")
            fig.add_scatter(x=[(x0 + x1) / 2], y=[(y0 + y1) / 2], mode="markers", marker=dict(size=6, color="rgba(148,163,184,.0)"),
                            hovertemplate=f"{g.nodes[a]['ko']} —{d['rel']}→ {g.nodes[b]['ko']}<extra></extra>", showlegend=False)
        for grp, col in O.GROUP_COLORS.items():
            ns = [n for n in g if g.nodes[n]["group"] == grp]
            fig.add_scatter(x=[pos[n][0] for n in ns], y=[pos[n][1] for n in ns], mode="markers+text", name=grp,
                            text=[g.nodes[n]["ko"] for n in ns], textposition="top center", textfont=dict(size=11, color="#e2e8f0"),
                            marker=dict(size=[12 + 2.2 * g.degree(n) for n in ns], color=col, line=dict(color="#0b1222", width=2)),
                            customdata=[[n, g.nodes[n]["desc"]] for n in ns],
                            hovertemplate="%{text} (%{customdata[0]})<br>%{customdata[1]}<extra></extra>")
        ui.style(fig, 470, margin=dict(l=4, r=4, t=30, b=4))
        fig.update_layout(xaxis_range=[-.5, 5.7], yaxis_range=[-1.5, 3.8])
        fig.update_xaxes(visible=False)
        fig.update_yaxes(visible=False)
        ui.plot(fig, "on_graph")
with c2:
    with ui.card("node", "클래스 들여다보기", "", "Class"):
        n = st.selectbox("클래스", list(O.CLASSES), index=list(O.CLASSES).index("VOC"), format_func=lambda k: f"{O.CLASSES[k][0]} ({k})", key="on_node")
        ko, grp, desc = O.CLASSES[n]
        ui.h(f'<div class="fx"><div><span>묶음</span><b style="color:{O.GROUP_COLORS[grp]}">{grp}</b></div><div><span>연결</span><b>{g.degree(n)}<small>개</small></b></div></div>')
        ui.note(desc)
        rel = [f"<div><b>{O.CLASSES[a][0]}</b> —{d['rel']}→ <b>{ko}</b></div>" for a, _, d in g.in_edges(n, data=True)]
        rel += [f"<div><b>{ko}</b> —{d['rel']}→ <b>{O.CLASSES[b][0]}</b></div>" for _, b, d in g.out_edges(n, data=True)]
        ui.h('<div class="disc">' + "".join(rel) + "</div>")
    with ui.card("paths", "인과 경로", "연구 핵심 질문 ② — 에이전트가 원인을 설명할 때 따라가는 길", "Causal"):
        ui.h("".join('<div class="path">' + "<i>→</i>".join(f"<span>{s}</span>" for s in p) + "</div>" for p in O.CAUSAL_PATHS))

c1, c2 = st.columns(2, gap="medium")
with c1:
    with ui.card("iso", "ISO/IEC 5087-1 대응 후보", "도시 공통 데이터 모델 표준 — 대응 여부는 2차년도 정합 검토 대상", "Standard"):
        st.dataframe(pd.DataFrame(O.ISO5087, columns=["이 온톨로지", "5087-1 대응 후보", "메모"]), hide_index=True)
        ui.note("표준 분류명은 검토 전 가안입니다. 갭·생활불편·VOC는 표준에 직접 대응이 없어 확장 클래스로 둡니다.")
with c2:
    with ui.card("inv", "데이터 인벤토리 (예시)", "연구 핵심 질문 ③ — 확보 가능한 데이터와 새로 만들어야 할 데이터", "Inventory"):
        inv = pd.DataFrame([
            ("VOC 원장", "사업단 민원 관리", "보유", "VOC"), ("공정·준공 실적", "사업관리 시스템", "보유", "Phase"),
            ("분양·입주 실적", "분양 관리", "보유", "Household"), ("학교 개교 계획", "교육청 협의 자료", "일부", "Facility"),
            ("버스 노선·배차", "지자체 교통", "일부", "Service"), ("상가 입점 현황", "상업용지 관리", "일부", "Facility"),
            ("가구 구성(유형)", "설문 · 통계 추정", "구축 필요", "Persona"), ("VOC 정답 라벨", "담당자 검토(HITL) 누적", "구축 필요", "VOC"),
            ("공사 강도(장비·시간)", "현장 일보", "구축 필요", "Phase"),
        ], columns=["데이터", "예상 출처", "상태", "연결 클래스"])
        st.dataframe(inv, hide_index=True,
                     column_config={"상태": st.column_config.TextColumn(help="보유 / 일부 / 구축 필요 — 시연용 가정")})
