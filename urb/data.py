# -*- coding: utf-8 -*-
"""데이터 읽기 — data/ 의 가상 데이터를 읽고, VOC에는 분류 에이전트 결과를 붙인다.
data/가 없으면 scripts/make_synthetic.py로 그 자리에서 만든다."""
import importlib.util
import json
from pathlib import Path

import pandas as pd
import streamlit as st

from . import catalog as C
from . import sim
from . import voc as V

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def _ensure():
    if not (DATA / "voc.csv").exists():
        spec = importlib.util.spec_from_file_location("mk", ROOT / "scripts" / "make_synthetic.py")
        mk = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mk)
        mk.main()


@st.cache_data(show_spinner=False)
def voc() -> pd.DataFrame:
    _ensure()
    v = pd.read_csv(DATA / "voc.csv", encoding="utf-8-sig")
    c = v["text"].map(V.classify)
    v["pred_cat"] = c.map(lambda d: d["cat"])
    v["conf"] = c.map(lambda d: d["conf"])
    v["severity"] = c.map(lambda d: d["severity"])
    v["entities"] = c.map(lambda d: ", ".join(d["entities"]))
    v["owner"] = c.map(lambda d: d["owner"])
    v["label"] = v["pred_cat"].map(lambda k: C.VOC_CATS[k]["label"])
    return v


@st.cache_data(show_spinner=False)
def meta() -> dict:
    _ensure()
    try:
        return json.loads((DATA / "meta.json").read_text(encoding="utf-8"))
    except Exception:
        return {}


@st.cache_data(show_spinner=False)
def simulate(zone_id: str, levers_key: tuple = (), params_key: tuple = ()):
    return sim.simulate(zone_id, dict(levers_key), dict(params_key))


@st.cache_data(show_spinner=False)
def compare(zone_id: str):
    return sim.compare(zone_id)


@st.cache_data(show_spinner=False)
def search(zone_id: str):
    return sim.search(zone_id)


@st.cache_data(show_spinner=False)
def sensitivity(zone_id: str, levers_key: tuple = ()):
    return sim.sensitivity(zone_id, dict(levers_key))


@st.cache_data(show_spinner=False)
def abm(zone_id: str, levers_key: tuple = (), contagion: float = 0.8):
    r = sim.abm(zone_id, dict(levers_key), contagion=contagion)
    return {"monthly": r["monthly"], "block": r["block"], "agents": r["agents"]}


def key(d: dict | None) -> tuple:
    return tuple(sorted((d or {}).items()))
