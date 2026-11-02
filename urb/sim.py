# -*- coding: utf-8 -*-
"""시뮬레이션 코어 — 연구계획서의 '수학 코어'를 단순화한 시연판.
  1) 입주 곡선 H(t)        : 블록별 로지스틱
  2) 공급-수요 갭 g_k(t)    : 교통·학교·상권·공원 수용력 대비 부족률, 공사 강도
  3) 생활불편지수 I(t)      : 주민 Agent 유형 가중 합 (0~100)
  4) VOC 기대건수 λ_k(t)    : H/1000 × rate_k × (1 + β_k · g_k)
  5) What-if · ±20% 민감도 · 다목적(비용·공정·VOC) 탐색
  6) Agent-ABM            : 가구 Agent의 민원 확률 + 이웃 확산
※ 계수는 모두 가상값. 실제 보정은 연구 1·2차년도 과제."""
from itertools import product

import numpy as np
import pandas as pd

from . import catalog as C

T = np.arange(C.HORIZON)
BASE_PARAMS = {k: 1.0 for k in C.PARAMS}


def _occ(t, start, speed=1.0):
    """입주율 0→1 (시작월 0, 약 12개월에 90%)."""
    t50, s = 6.0 / speed, 2.5 / speed
    f = 1 / (1 + np.exp(-(t - start - t50) / s))
    f0 = 1 / (1 + np.exp(t50 / s))
    return np.where(t >= start, np.clip((f - f0) / (1 - f0), 0, 1), 0.0)


def _steps(entries, scale=1.0):
    out = np.zeros(C.HORIZON)
    for t0, cap in entries:
        out += np.where(T >= t0, cap * scale, 0.0)
    return out


def _gap(demand, supply):
    with np.errstate(divide="ignore", invalid="ignore"):
        g = np.where(demand > 1e-9, 1 - supply / demand, 0.0)
    return np.clip(g, 0, 1)


def zone_plan(zone_id: str, levers: dict | None = None):
    """레버를 반영한 블록 입주 시작월·시설 개통월 목록."""
    z = C.ZONES[zone_id]
    lv = levers or {}
    vs = int(round(lv.get("volume_shift", 0)))
    blocks = [(b, hh, C.t_of(s) + (vs if i > 0 else 0)) for i, (b, hh, s) in enumerate(z["blocks"])]
    first = min(t for _, _, t in blocks)
    ss = int(round(lv.get("school_shift", 0)))
    school = [(max(first - 6, C.t_of(s) - ss), cap) for s, cap in z["school"]]
    boost = float(lv.get("transit_boost", 0))
    bs = int(round(lv.get("bridge_shift", 0)))
    transit = []
    for s, cap, owner in z["transit"]:
        t0 = C.t_of(s)
        if owner == "외부":
            t0 -= bs
        elif t0 > first:
            t0 -= int(round(6 * boost))
        transit.append((max(first, t0), cap, owner))
    if boost > 0:
        transit.append((first, 2500 * boost, "협의"))
    park = [(C.t_of(s), cap) for s, cap in z["park"]]
    return {"blocks": blocks, "first": first, "school": school, "transit": transit, "park": park,
            "commerce": z["commerce"], "temp": float(lv.get("temp", 0))}


def simulate(zone_id: str, levers: dict | None = None, params: dict | None = None) -> pd.DataFrame:
    p = {**BASE_PARAMS, **(params or {})}
    plan = zone_plan(zone_id, levers)
    blocks, first = plan["blocks"], plan["first"]
    hb = {b: hh * _occ(T, t0, p["occ_speed"]) for b, hh, t0 in blocks}
    H = sum(hb.values())
    H_prev = sum(hh * _occ(T - 1, t0, p["occ_speed"]) for _, hh, t0 in blocks)
    dH = H - H_prev
    total = sum(hh for _, hh, _ in blocks)

    # 공급과 갭
    seats = _steps(plan["school"], p["school_cap"])
    g_school = _gap(H * 0.30, seats)
    tcap = _steps([(t0, cap) for t0, cap, _ in plan["transit"]], p["transit_cap"])
    g_traffic = _gap(H, tcap)
    cm = plan["commerce"]
    lag = cm["lag"] * p["commerce_lag"]
    stores = cm["max"] / (1 + np.exp(-(T - first - lag) / 4.0)) * (T >= first)
    g_amenity = _gap(H / 55.0, stores)
    g_park = _gap(H, _steps(plan["park"]))
    # 공사 강도: 공사 중인 블록 물량 / 전체 (입주민이 있을 때만)
    cons = np.zeros(C.HORIZON)
    for _, hh, t0 in blocks:
        cons += np.where((T >= t0 - 36) & (T < t0), hh / total, 0.0)
    g_cons = np.clip(cons * 1.4, 0, 1) * (H > 1)
    # 임시대책: 첫 입주 후 18개월
    tw = (T >= first) & (T < first + 18)
    tf = plan["temp"]
    g_traffic = np.where(tw, g_traffic * (1 - .45 * tf), g_traffic)
    g_amenity = np.where(tw, g_amenity * (1 - .35 * tf), g_amenity)
    g_safety = np.clip(.5 * g_cons + .5 * g_school, 0, 1)
    g_safety = np.where(tw, g_safety * (1 - .30 * tf), g_safety)

    drivers = {"traffic": g_traffic, "school": g_school, "amenity": g_amenity,
               "construction": g_cons, "safety": g_safety, "park": g_park}
    W = np.array([P["w"] for P in C.PERSONAS.values()])
    W = W / W.sum(axis=1, keepdims=True)
    share = np.array([P["share"] for P in C.PERSONAS.values()])
    wmix = share @ W                                      # 유형 구성비로 가중한 민감도
    inconv = 100 * sum(wmix[i] * drivers[k] for i, k in enumerate(C.GAP_CATS)) / wmix.max() / len(C.GAP_CATS) * 2.2
    inconv = np.clip(inconv, 0, 100) * (H > 1)

    df = pd.DataFrame({"t": T, "ym": [C.ym(t) for t in T], "H": H, "dH": np.clip(dH, 0, None),
                       "seats": seats, "transit_cap": tcap, "stores": stores, "inconv": inconv})
    for b, arr in hb.items():
        df[f"H_{b}"] = arr
    for k, arr in drivers.items():
        df[f"g_{k}"] = arr
    for k in C.GAP_CATS:
        v = C.VOC_CATS[k]
        df[f"voc_{k}"] = H / 1000 * v["rate"] * p["rate"] * (1 + v["beta"] * p["beta"] * drivers[k])
    df["voc_housing"] = df["dH"] / 1000 * C.VOC_CATS["housing"]["rate"] * p["rate"]
    df["voc"] = df[[f"voc_{k}" for k in C.CAT_KEYS]].sum(axis=1)
    df["per1000"] = np.where(H > 300, df["voc"] / np.maximum(H, 1) * 1000, np.nan)
    df["commute_min"] = np.where(H > 1, 38 + 30 * g_traffic, np.nan)
    df["school_min"] = np.where(H > 1, 12 + 28 * g_school, np.nan)
    df["grade"] = [C.risk_grade(r, h)[0] for r, h in zip(df["per1000"].fillna(0), H)]
    df.attrs.update({"zone": zone_id, "first": first, "total_hh": total, "plan": plan})
    return df


def cost_delay(levers: dict | None):
    lv = levers or {}
    cost = sum(C.LEVERS[k]["cost_per"] * float(v) for k, v in lv.items() if k in C.LEVERS)
    delay = float(lv.get("volume_shift", 0))
    return cost, delay


def kpis(df: pd.DataFrame, levers: dict | None = None, window: int = 48) -> dict:
    first = df.attrs["first"]
    w = df[(df.t >= first) & (df.t < first + window)]
    occ = w[w.H > 300]
    cost, delay = cost_delay(levers)
    bad = int((w["grade"].isin(["D", "E"])).sum())
    return {"voc_total": float(w["voc"].sum()), "voc_peak": float(w["voc"].max() if len(w) else 0),
            "peak_ym": w.loc[w["voc"].idxmax(), "ym"] if len(w) else "-",
            "inconv": float(occ["inconv"].mean()) if len(occ) else 0.0,
            "commute": float(occ["commute_min"].mean()) if len(occ) else 0.0,
            "school": float(occ["school_min"].mean()) if len(occ) else 0.0,
            "bad_months": bad, "cost": cost, "delay": delay}


def compare(zone_id: str, scenario_ids=None, params=None) -> pd.DataFrame:
    rows = []
    for sid in scenario_ids or C.SCENARIOS:
        lv = C.SCENARIOS[sid]["levers"]
        k = kpis(simulate(zone_id, lv, params), lv)
        rows.append({"id": sid, "name": C.SCENARIOS[sid]["name"], **k})
    out = pd.DataFrame(rows)
    base = out.iloc[0]
    out["voc_delta"] = (out["voc_total"] / base["voc_total"] - 1) * 100 if base["voc_total"] else 0
    out["inconv_delta"] = out["inconv"] - base["inconv"]
    return out


def sensitivity(zone_id: str, levers: dict | None = None, pct: float = 0.2) -> pd.DataFrame:
    base = kpis(simulate(zone_id, levers), levers)["voc_total"]
    rows = []
    for k, label in C.PARAMS.items():
        lo = kpis(simulate(zone_id, levers, {k: 1 - pct}), levers)["voc_total"]
        hi = kpis(simulate(zone_id, levers, {k: 1 + pct}), levers)["voc_total"]
        rows.append({"param": k, "label": label, "low": lo - base, "high": hi - base, "span": abs(hi - lo)})
    return pd.DataFrame(rows).sort_values("span"), base


def search(zone_id: str) -> pd.DataFrame:
    """레버 조합 탐색 (3×3×2×3 = 54안) → 다목적 비교용 표."""
    base = kpis(simulate(zone_id), {})
    rows = []
    for ss, tb, tp, vs in product([0, 3, 6], [0, .5, 1.0], [0, 1.0], [0, 3, 6]):
        lv = {"school_shift": ss, "transit_boost": tb, "temp": tp, "volume_shift": vs}
        k = kpis(simulate(zone_id, lv), lv)
        rows.append({**lv, **k, "voc_cut": (1 - k["voc_total"] / base["voc_total"]) * 100 if base["voc_total"] else 0})
    df = pd.DataFrame(rows)
    # 파레토: VOC↓ · 비용↓ · 지연↓ 모두에서 지배당하지 않는 안
    vals = df[["voc_total", "cost", "delay"]].to_numpy()
    df["pareto"] = [not any((o <= v).all() and (o < v).any() for o in vals) for v in vals]
    return df


def score(df: pd.DataFrame, w_voc=.5, w_cost=.3, w_delay=.2) -> pd.Series:
    def n(s):
        r = s.max() - s.min()
        return (s - s.min()) / r if r else s * 0
    return 100 * (1 - (w_voc * n(df["voc_total"]) + w_cost * n(df["cost"]) + w_delay * n(df["delay"])) / max(w_voc + w_cost + w_delay, 1e-9))


# ── Agent-ABM ────────────────────────────────────────────────────────
def abm(zone_id: str, levers: dict | None = None, scale: int = 10, seed: int = 7, contagion: float = 0.8):
    """가구 Agent(1 Agent = scale 세대)의 월별 민원 발생과 블록 내 확산.
    반환: dict(monthly: DataFrame[t, persona, cat, n], block: DataFrame, agents: int)"""
    df = simulate(zone_id, levers)
    plan = df.attrs["plan"]
    rng = np.random.default_rng(seed)
    pids = list(C.PERSONAS)
    shares = np.array([C.PERSONAS[p]["share"] for p in pids])
    W = np.array([C.PERSONAS[p]["w"] for p in pids], dtype=float)
    W = W / W.sum(axis=1, keepdims=True)
    A = np.array([C.PERSONAS[p]["a"] for p in pids])
    G = np.stack([df[f"g_{k}"].to_numpy() for k in C.GAP_CATS], axis=1)       # (T, 6)

    blk, tin = [], []
    for bi, (b, hh, t0) in enumerate(plan["blocks"]):
        n = max(1, int(round(hh / scale)))
        pmf = np.diff(np.concatenate([[0], _occ(T, t0)]))
        pmf = pmf / pmf.sum()
        tin.append(rng.choice(T, size=n, p=pmf))
        blk.append(np.full(n, bi))
    blk, tin = np.concatenate(blk), np.concatenate(tin)
    per = rng.choice(len(pids), size=len(blk), p=shares)
    nb_rate = np.zeros(len(plan["blocks"]))
    sal = np.zeros(len(plan["blocks"]))                                       # 블록 이슈 체감도(이웃 민원의 지수평활)
    rec, brec = [], []
    for t in range(C.HORIZON):
        act = tin <= t
        if not act.any():
            continue
        e = (W[per] * G[t]).sum(axis=1)                                       # 체감 불편
        lift = contagion * np.tanh(sal / 0.02)                               # 확산 효과 상한 = contagion (로짓)
        logit = A[per] - 0.5 + 4.0 * e + lift[blk]
        hit = act & (rng.random(len(blk)) < 1 / (1 + np.exp(-logit)))
        if hit.any():
            mix = W[per[hit]] * (G[t] + .02)
            mix = mix / mix.sum(axis=1, keepdims=True)
            cats = np.array([rng.choice(6, p=m) for m in mix])
            for pi, ci in zip(per[hit], cats):
                rec.append((t, pids[pi], C.GAP_CATS[ci]))
        for bi in range(len(plan["blocks"])):
            m = act & (blk == bi)
            nb_rate[bi] = hit[m].sum() / m.sum() if m.any() else 0
            sal[bi] = .7 * sal[bi] + .3 * nb_rate[bi]
            brec.append((t, plan["blocks"][bi][0], int(hit[m].sum()) * scale, float(nb_rate[bi]), float(np.tanh(sal[bi] / 0.02))))
    monthly = pd.DataFrame(rec, columns=["t", "persona", "cat"])
    monthly = monthly.groupby(["t", "persona", "cat"]).size().mul(scale).rename("n").reset_index()
    return {"monthly": monthly, "block": pd.DataFrame(brec, columns=["t", "block", "n", "rate", "salience"]),
            "agents": int(len(blk)), "df": df}
