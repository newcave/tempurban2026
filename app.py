# -*- coding: utf-8 -*-
"""Urban AI · tempurban2026 — VOC 기반 도시개발 전주기 AI 시뮬레이션 (기획연구 시연판)
가상 데이터 + '에이전트인 척' 하는 구조로 화면 뼈대를 먼저 세운다. 디자인은 water-tech-agent2를 따른다.
실행: streamlit run app.py"""
import streamlit as st

from urb import agents as A
from urb import catalog as C
from urb import data as D
from urb import llm as L
from urb import ontology as O
from urb import sim as S
from urb import ui
from urb import voc as V


def _fresh(*mods):
    """Streamlit Cloud가 예전 보조 모듈을 쥐고 있는 일이 있어, 파일이 바뀌면 다시 읽는다 (water-tech-agent2와 같은 방식)."""
    import importlib
    import os
    for m in mods:
        try:
            mt = os.path.getmtime(m.__file__)
            if getattr(m, "_mt", None) is None or mt > m._mt:
                importlib.reload(m)
                m._mt = mt
        except Exception:
            pass


_fresh(C, L, V, O, S, A, D, ui)          # 의존 순서대로

APP_VERSION = "v0.1 · 2026-11-02"

st.set_page_config(page_title="Urban AI · tempurban2026", page_icon="🏙️", layout="wide", initial_sidebar_state="collapsed")
ui.inject()

PAGES = [
    st.Page("app_pages/overview.py", title="개요", icon=":material/space_dashboard:", default=True),
    st.Page("app_pages/sites.py", title="사업지 · 공정", icon=":material/apartment:", url_path="sites"),
    st.Page("app_pages/voc.py", title="VOC 분석", icon=":material/forum:", url_path="voc"),
    st.Page("app_pages/residents.py", title="주민 Agent · ABM", icon=":material/groups:", url_path="residents"),
    st.Page("app_pages/whatif.py", title="What-if", icon=":material/alt_route:", url_path="whatif"),
    st.Page("app_pages/agents.py", title="에이전트 관제", icon=":material/hub:", url_path="agents"),
    st.Page("app_pages/ontology.py", title="온톨로지", icon=":material/account_tree:", url_path="ontology"),
]
current = st.navigation(PAGES, position="hidden")
ui.topbar(PAGES, current)
current.run()
ui.footer(f"{D.meta().get('generated', '-')} · {APP_VERSION}")
