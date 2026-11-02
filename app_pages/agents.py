# -*- coding: utf-8 -*-
"""에이전트 관제 — 에이전트 구성 · 질문하기(오케스트레이터 트레이스) · 자동 실행 기록"""
import streamlit as st

from urb import agents as A
from urb import catalog as C
from urb import data as D
from urb import ui

voc = D.voc()
log = A.run_log(24)
ui.page_header("Agent operations", "에이전트 관제",
               "오케스트레이터가 질문을 해석해 전문 에이전트에게 일을 나누고 결과를 모읍니다. "
               "지금은 LLM 없이 규칙·시뮬레이션으로 움직이는 시연판이며, 실행 순서·소요 시간·주고받은 값은 그대로 기록됩니다.",
               [f"에이전트 <b>{len(A.AGENTS)}</b>", "LLM 연결 <b>꺼짐</b>", "실행 기록 = 가상"])

ui.kpis([
    {"label": "최근 24시간 실행", "value": f"{len(log):,}", "unit": "회", "sub": "예약 실행 기준 (가상)", "color": ui.ACCENT},
    {"label": "실패·재시도", "value": f"{(~log.ok).sum()}", "unit": "건", "sub": "원천 응답 지연 등", "color": "#f87171"},
    {"label": "분류 검토 대기", "value": f"{(voc[voc.t >= voc.t.max() - 2].conf < .75).sum()}", "unit": "건", "sub": "최근 3개월 · HITL", "color": "#f59e0b"},
    {"label": "평균 소요", "value": f"{log.sec.mean():.1f}" if len(log) else "-", "unit": "초", "sub": "에이전트 1회 실행", "color": "#22d3ee"},
])

with ui.card("arch", "에이전트 구성", "조정 1 + 데이터 3 + 예측 3 + 의사결정 2 · 판단은 사람(HITL)", "Fleet"):
    layers = ["조정", "데이터", "예측", "의사결정"]
    html = ""
    for L in layers:
        ags = [a for a in A.AGENTS if a["layer"] == L]
        html += f'<div class="layer" style="margin:8px 0 6px">{L}</div><div class="agents">' + "".join(
            f'<div class="ag" style="border-left:3px solid {a["color"]}"><div class="top"><b>{a["name"]}</b>'
            f'<span class="st" style="color:{a["color"]};background:{a["color"]}1f;border:1px solid {a["color"]}55">{a["cron"]}</span></div>'
            f'<p>{a["role"]}</p><p style="color:#64748b;margin-top:4px">tools · {" · ".join(a["tools"])}</p></div>' for a in ags) + "</div>"
    ui.h(html)
    ui.note("LLM을 붙이면 바뀌는 곳: 질문 해석(오케스트레이터) · VOC 분류 · 주민 페르소나 목소리 → urb/llm.py 한 곳. "
            "대안의 최종 선택과 민원 회신은 담당자가 확인한 뒤 나갑니다.")

with ui.card("ask", "에이전트에게 묻기", "예시를 누르거나 직접 입력 · 답변 아래에 어떤 에이전트가 무엇을 했는지 기록이 남습니다", "Ask"):
    c1, c2 = st.columns([1, 2.2], gap="medium")
    with c1:
        z = ui.zone_select("대상 생활권", key="zone_ask", zones=[k for k in C.ZONES if k != "MTV-R"])
    def _pick():                                   # 예시를 누르면 입력칸을 채우고 바로 보낸다
        v = st.session_state.get("ask_ex")
        if v:
            st.session_state["ask_q"] = v
            st.session_state["ask_auto"] = True

    with c2:
        st.pills("예시 질문", A.EXAMPLES, key="ask_ex", on_change=_pick)
    q = st.text_input("질문", placeholder="예: 생활권A에서 내년 상반기 VOC 위험은?", key="ask_q")
    go_ = st.button("질문 보내기", type="primary", key="ask_go")
    if (go_ or st.session_state.pop("ask_auto", False)) and q:
        st.session_state["ask_last"] = (q, z, A.Orchestrator(voc).ask(q, z))
    last = st.session_state.get("ask_last")
    if last:
        q0, z0, r = last
        st.caption(f"Q · {q0}  —  {C.ZONES[z0]['name']} · 의도: {A.INTENT_KO.get(r.intent, r.intent)}")
        a1, a2 = st.columns([1.4, 1], gap="medium")
        with a1:
            with st.container(key="answer_box", border=True):
                st.markdown(r.answer)
        with a2:
            ui.bar_answer(r.chart, "ask_chart", 280)
        t_acc = 0.0
        lines = []
        for s in r.steps:
            t_acc += s.ms
            lines.append(f'<div class="ln"><span class="t">+{t_acc:7.1f}ms</span><span class="wf">{ui.esc(A.AG[s.agent]["name"])}</span>'
                         f'<span class="lb">{ui.esc(s.action)}</span><span class="{"ok" if s.ok else "bad"}">{"✓" if s.ok else "✗"}</span>'
                         f'<span class="msg">{ui.esc(s.detail)}</span><span class="du">{s.ms:.1f}ms</span></div>')
        ui.h(f'<div class="term"><div class="bar"><i></i><i></i><i></i><span>orchestrator trace · {len(r.steps)} steps</span></div>'
             f'<div class="body">{"".join(lines)}<div class="ln"><span class="cur">▌</span></div></div></div>')

with ui.card("log", "자동 실행 기록 (최근 24시간)", "예약된 에이전트 작업의 실행 로그 — 화면 시연용 가상 기록", "Log"):
    rows = []
    for r_ in log.head(80).itertuples():
        rows.append(f'<div class="ln"><span class="t">{r_.ts:%m-%d %H:%M:%S}</span><span class="wf">{ui.esc(r_.name)}</span>'
                    f'<span class="{"ok" if r_.ok else "bad"}">{"OK  " if r_.ok else "WAIT"}</span>'
                    f'<span class="msg">{ui.esc(r_.msg)}</span><span class="du">{r_.sec:.1f}s</span></div>')
    ui.h(f'<div class="term"><div class="bar"><i></i><i></i><i></i><span>urban-agents · scheduler</span></div>'
         f'<div class="body">{"".join(rows)}</div></div>')
