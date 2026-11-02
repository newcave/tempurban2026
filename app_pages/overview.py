# -*- coding: utf-8 -*-
"""개요 — 과제 한 장 요약 + PoC 생활권 현황"""
import streamlit as st

from urb import agents as A
from urb import catalog as C
from urb import data as D
from urb import ui

voc = D.voc()
z = "EDC-A"
df = D.simulate(z)
now = df.iloc[C.NOW_T]
last24 = df.iloc[C.NOW_T - 23:C.NOW_T + 1]

WAVES = """<svg class="waves" viewBox="0 0 1200 300" preserveAspectRatio="none" aria-hidden="true">""" + "".join(
    f'<rect x="{40 + k * 92}" y="{300 - (60 + (k * 37) % 140)}" width="58" height="{60 + (k * 37) % 140}" rx="3" '
    f'fill="none" stroke="rgba(196,181,253,{0.05 + (k % 4) * 0.025:.2f})" stroke-width="1.2"/>' for k in range(13)) + "</svg>"

ui.h(f"""
<div class="hero">{WAVES}<div class="in">
  <div>
    <div class="eb">Urban AI · 기획연구 시연판 · TRL 2</div>
    <h1>VOC로 미리 보는<br><span>도시개발 의사결정</span></h1>
    <p>공정·분양·입주·기반시설 공급이 주민 생활불편과 VOC로 이어지는 경로를 모형으로 만들고,
    대안을 미리 비교(What-if)해 사업 리스크를 줄이는 AI 의사결정체계의 뼈대입니다.
    화면의 모든 숫자는 <b>가상 데이터</b>이며, 에이전트는 규칙·시뮬레이션으로 동작하는 시연판입니다.</p>
  </div>
  <div class="facts">
    <div class="f"><b>{len(C.SITES)} <small style="font-size:.9rem;color:#94a3b8">· {len(C.ZONES)}</small></b><span>사업지 · 생활권 (가상 프로파일)</span></div>
    <div class="f"><b>{len(voc):,}</b><span>가상 VOC 민원 (2022~2026.10)</span></div>
    <div class="f"><b>{len(C.PERSONAS)} <small style="font-size:.9rem;color:#94a3b8">· {len(C.SCENARIOS) - 1}</small></b><span>주민 Agent 유형 · 표준 시나리오</span></div>
    <div class="f"><b>{len(A.AGENTS)}</b><span>에이전트 (오케스트레이터 + 전문 8)</span></div>
  </div>
</div></div>""")

g, gc = C.risk_grade(now["per1000"] if now["per1000"] == now["per1000"] else 0, now["H"])
ui.kpis([
    {"label": f"PoC 생활권 입주 세대 ({C.ym(C.NOW_T)})", "value": f"{now['H']:,.0f}", "unit": "세대",
     "sub": f"계획 {df.attrs['total_hh']:,}세대의 {now['H'] / df.attrs['total_hh'] * 100:.0f}%", "spark": list(last24["H"]), "color": ui.ACCENT},
    {"label": "이번 달 VOC 기대건수", "value": f"{now['voc']:.0f}", "unit": "건", "sub": "기준계획 · 7개 유형 합",
     "spark": list(last24["voc"]), "color": "#22d3ee"},
    {"label": "생활불편지수", "value": f"{now['inconv']:.0f}", "unit": "/100", "sub": "주민 Agent 유형 가중",
     "spark": list(last24["inconv"]), "color": "#f59e0b"},
    {"label": "VOC 위험등급", "value": g, "sub": f"1천 세대당 월 {now['per1000']:.1f}건", "color": gc},
    {"label": "학교 정원 부족률", "value": f"{now['g_school'] * 100:.0f}", "unit": "%", "sub": "개교 전 원거리 통학",
     "spark": list(last24["g_school"]), "color": "#f87171"},
])

with ui.card("pipe", "처리 흐름", "연구계획서의 5단 구조를 화면·에이전트로 옮긴 것", "Pipeline"):
    steps = [("01", "통합 데이터 레이크", "사업·공정·분양·입주·VOC를 한 구조로 (온톨로지) — VOC 수집·분류 에이전트"),
             ("02", "생활영향 예측", "입주 대비 학교·교통·상권·공원 공급 갭 → 생활불편지수·VOC 기대건수"),
             ("03", "주민 페르소나", "주민 Agent 6종의 민감도와 목소리 (LLM 자리, 지금은 템플릿)"),
             ("04", "Agent-ABM", "가구 Agent의 민원 발생과 블록 내 확산"),
             ("05", "What-if · 다목적", "대안 상대비교 · ±20% 민감도 · VOC/비용/공정 파레토")]
    ui.h('<div class="flow">' + "".join(f'<div class="st"><div class="i">{i}</div><b>{t}</b><span>{s}</span></div>' for i, t, s in steps) + "</div>")

with ui.card("sites", "대상지", "주대상지 1곳 + 후속 적용 1곳 + 단계별 비교 2곳", "Sites"):
    ui.h('<div class="sites">' + "".join(
        f'<div class="site" style="--c:{s["color"]}"><b>{s["full"]}</b><div class="r">{s["role"]} · 현재 {s["stage"]}</div><p>{s["desc"]}</p></div>'
        for s in C.SITES.values()) + "</div>")

c1, c2 = st.columns([1.3, 1], gap="medium")
with c1:
    with ui.card("qs", "연구 핵심 질문 → 화면", "계획서의 4개 질문을 어디서 답하는지", "Questions"):
        qs = [("AI가 먼저 도와야 할 의사결정은?", "What-if · 에이전트 관제"),
              ("공정·분양·입주·공급·VOC의 인과경로는?", "온톨로지 · 사업지·공정"),
              ("확보 가능한 데이터와 추가 구축할 데이터는?", "VOC 분석 · 온톨로지(데이터 사전)"),
              ("어떤 대상지·시나리오에서 실증할까?", "What-if (EDC 생활권A · 김포 적용 조건)")]
        ui.h('<div class="qs">' + "".join(f"<div><b>{q}</b><span>→ {a}</span></div>" for q, a in qs) + "</div>")
with c2:
    with ui.card("plan", "일정", "2년 · 자체 + 위탁", "Roadmap"):
        ui.h('<div class="disc">'
             '<div><b>2027 · 개념 정립</b> — 현업 인터뷰·업무 분석, 국내외 사례, 데이터 인벤토리·품질 진단, 전주기 온톨로지, 수학·알고리즘 코어 정식화</div>'
             '<div><b>2028 · 제한적 PoC</b> — EDC 1개 생활권 시나리오 5건 내외 상대비교, 온톨로지 v1, 후속 기술개발계획·RFP 초안</div>'
             '<div><b>이 시연판</b> — 위 구조를 가상 데이터로 먼저 돌려 보며 화면·데이터 요구를 구체화</div></div>')
ui.note("모형 계수·대안 비용·공급 계획은 예시값입니다. 실제 사업 수치, 내부 문서 번호, 개인정보는 넣지 않았습니다.")
