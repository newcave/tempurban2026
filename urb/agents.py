# -*- coding: utf-8 -*-
"""에이전트 구조 (시연판) — 오케스트레이터가 질문을 해석해 전문 에이전트에 일을 나누고, 결과를 종합한다.
지금은 LLM 없이 규칙·시뮬레이션으로 동작하는 '에이전트인 척' 버전. 각 에이전트의 run 함수가 실제 계산을 하고,
실행 순서·소요 시간·주고받은 값은 트레이스로 남는다(관제 화면의 터미널 로그).
LLM을 붙이면 바뀌는 곳: Orchestrator._intent(질문 해석), PersonaAgent.voice(문장 생성), voc.classify(분류)."""
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

from . import catalog as C
from . import llm
from . import ontology as O
from . import sim

KST = timezone(timedelta(hours=9))

AGENTS = [
    {"id": "orchestrator", "name": "오케스트레이터", "layer": "조정", "color": "#e2e8f0", "cron": "요청 시",
     "role": "질문 해석 → 작업 계획 → 전문 에이전트 호출 → 결과 종합", "tools": ["intent_router", "planner"]},
    {"id": "voc_ingest", "name": "VOC 수집·정제", "layer": "데이터", "color": "#22d3ee", "cron": "매시 05분",
     "role": "채널별 민원 수집, 중복 제거, 개인정보 마스킹", "tools": ["channel_pull", "dedup", "pii_mask"]},
    {"id": "voc_classifier", "name": "VOC 분류", "layer": "데이터", "color": "#22d3ee", "cron": "매시 15분",
     "role": "유형·심각도·관련 시설 태깅 (LLM 자리 — 현재 규칙 기반)", "tools": ["classify", "entity_link"]},
    {"id": "ontology", "name": "온톨로지 관리", "layer": "데이터", "color": "#22d3ee", "cron": "매일 02시",
     "role": "사업지·공정·시설·VOC를 한 구조로 연결, 데이터 사전 유지", "tools": ["resolve", "validate"]},
    {"id": "impact", "name": "생활영향 예측", "layer": "예측", "color": "#a78bfa", "cron": "매일 06시",
     "role": "입주·공급 갭 → 생활불편지수 · VOC 기대건수 · 위험등급", "tools": ["gap_model", "forecast"]},
    {"id": "persona", "name": "주민 페르소나", "layer": "예측", "color": "#a78bfa", "cron": "매주 월 07시",
     "role": "주민 Agent 유형별 민감도와 목소리 (LLM 자리 — 현재 템플릿)", "tools": ["persona_card", "voice"]},
    {"id": "abm", "name": "Agent-ABM", "layer": "예측", "color": "#a78bfa", "cron": "매주 월 08시",
     "role": "가구 Agent의 민원 발생과 블록 내 확산 시뮬레이션", "tools": ["abm_run"]},
    {"id": "whatif", "name": "What-if · 최적화", "layer": "의사결정", "color": "#34d399", "cron": "요청 시",
     "role": "시나리오 상대비교 · ±20% 민감도 · 다목적(VOC·비용·공정) 탐색", "tools": ["compare", "sensitivity", "search"]},
    {"id": "reporter", "name": "보고서 작성", "layer": "의사결정", "color": "#34d399", "cron": "매주 월 09시",
     "role": "결과 요약, 근거 표기, 민원 처리 안내문 초안", "tools": ["summarize", "reply_draft"]},
]
AG = {a["id"]: a for a in AGENTS}

ISSUE = {"traffic": "출퇴근 버스가 부족하고 길이 막히는 것", "school": "아이 학교가 아직 멀다는 것",
         "amenity": "집 근처에 병원·마트가 없는 것", "construction": "옆 공사장 소음과 먼지",
         "safety": "아이들 다니는 길이 위험한 것", "park": "산책하거나 아이가 놀 공간이 없는 것"}
BETTER = {"traffic": "버스가 늘어 출근이 한결 나아졌어요", "school": "학교가 빨리 열려 통학 걱정이 줄었어요",
          "amenity": "임시상가라도 생겨 장보기가 편해졌어요", "construction": "공사 영향이 조금 줄었어요",
          "safety": "임시 보행로가 생겨 마음이 놓여요", "park": "공원이 열려 숨통이 트여요"}


@dataclass
class Step:
    agent: str
    action: str
    detail: str
    ms: float
    ok: bool = True


@dataclass
class Reply:
    intent: str
    answer: str
    steps: list = field(default_factory=list)
    chart: dict | None = None          # {"kind": ..., "data": DataFrame, ...}
    evidence: list = field(default_factory=list)


class _Trace:
    def __init__(self):
        self.steps = []

    def run(self, agent, action, fn, detail=lambda r: ""):
        t0 = time.perf_counter()
        try:
            r = fn()
            ok = True
        except Exception as e:  # 시연판: 실패도 트레이스로 남김
            r, ok = None, False
            detail = lambda _r, e=e: f"오류: {e}"  # noqa: E731
        self.steps.append(Step(agent, action, detail(r), (time.perf_counter() - t0) * 1000, ok))
        return r


# ── 개별 에이전트 기능 ────────────────────────────────────────────────
def drivers_at(df: pd.DataFrame, t: int) -> dict:
    r = df.iloc[int(np.clip(t, 0, len(df) - 1))]
    return {k: float(r[f"g_{k}"]) for k in C.GAP_CATS}


def voice(pid: str, d_now: dict, d_alt: dict | None = None) -> dict:
    """주민 Agent 유형의 한마디 (LLM 페르소나 흉내)."""
    P = C.PERSONAS[pid]
    w = np.array(P["w"], float) / sum(P["w"])
    e = {k: w[i] * d_now[k] for i, k in enumerate(C.GAP_CATS)}
    top = max(e, key=e.get)
    level = sum(e.values())
    mood = "대체로 지낼 만해요" if level < .08 else "조금 불편해요" if level < .2 else "많이 불편해요"
    txt = llm.persona_voice(P, {"drivers": d_now, "alt": d_alt})
    if not txt:
        if level < .03:
            txt = f"{P['name']}입니다. 요즘은 큰 불편 없이 지내요."
        elif w[C.GAP_CATS.index(top)] < .1:
            txt = f"{P['name']}입니다. 요즘 {mood}. 제 일은 아니지만 이웃들이 {ISSUE[top]}을 많이 얘기해요."
        else:
            txt = f"{P['name']}입니다. 요즘 {mood}. 가장 힘든 건 {ISSUE[top]}이에요."
        if d_alt is not None:
            gain = {k: d_now[k] - d_alt[k] for k in C.GAP_CATS}
            g = max(gain, key=lambda k: gain[k] * w[C.GAP_CATS.index(k)])
            if gain[g] > .05 and w[C.GAP_CATS.index(g)] > .05:
                txt += f" 대안대로라면 {BETTER[g]}."
            else:
                txt += " 대안이 시행돼도 제 생활은 크게 달라지지 않을 것 같아요."
    return {"pid": pid, "name": P["name"], "level": level, "top": top, "text": txt, "color": P["color"]}


def voc_summary(voc: pd.DataFrame, zone_id: str, months: int = 6) -> dict:
    v = voc[voc.zone == zone_id]
    if v.empty:
        return {"n": 0}
    last_t = int(v.t.max())
    cur = v[v.t > last_t - months]
    prev = v[(v.t <= last_t - months) & (v.t > last_t - 2 * months)]
    top = cur.pred_cat.value_counts()
    return {"n": len(cur), "prev": len(prev), "top": top, "from": C.ym(last_t - months + 1), "to": C.ym(last_t),
            "review": int((cur.conf < .75).sum()), "severe": int((cur.severity == 3).sum()),
            "done": float((cur.status == "처리완료").mean() * 100)}


# ── 오케스트레이터 ───────────────────────────────────────────────────
INTENTS = [
    ("persona", r"주민|페르소나|목소리|반응|입장|ABM|확산"),
    ("sensitivity", r"민감도|불확실|±|20%|흔들|견고"),
    ("optimize", r"최적|추천|가장 좋|어떤 안|우선순위|조합|무엇을 먼저"),
    ("scenario", r"시나리오|비교|대안|what-?if|조기|선투자|임시|물량|만약|앞당기"),
    ("cause", r"왜|원인|이유|때문"),
    ("risk", r"위험|리스크|등급|피크|언제|전망|예측|내년"),
    ("voc", r"민원|VOC|voc|현황|유형|추이|몇 건"),
]
INTENT_KO = {"persona": "주민 반응 · 확산", "sensitivity": "민감도", "optimize": "다목적 최적화", "scenario": "시나리오 비교",
             "cause": "원인 분해", "risk": "위험 전망", "voc": "VOC 현황"}

EXAMPLES = [
    "생활권A 최근 민원은 어떤 유형이 많아?",
    "지금 생활권A에서 불편이 큰 이유는?",
    "앞으로 VOC 위험이 가장 큰 시기는 언제야?",
    "학교 조기공급, 교통 선투자, 임시대책을 비교해 줘",
    "비용과 공정을 같이 보면 어떤 조합이 가장 좋아?",
    "±20% 민감도에도 결론이 유지돼?",
    "주민 유형별로 대안에 어떻게 반응할까?",
]


class Orchestrator:
    def __init__(self, voc: pd.DataFrame):
        self.voc = voc

    def _intent(self, q: str) -> str:
        for name, pat in INTENTS:
            if re.search(pat, q, flags=re.I):
                return name
        return "voc"

    def ask(self, q: str, zone_id: str) -> Reply:
        tr = _Trace()
        zname = C.ZONES[zone_id]["name"]
        intent = tr.run("orchestrator", "intent_router", lambda: self._intent(q),
                        lambda r: f"질문 유형 = {INTENT_KO.get(r, r)} · 대상 = {zname}")
        nodes = tr.run("ontology", "resolve", lambda: O.resolve(zname, [f"Site:{C.SITES[C.ZONES[zone_id]['site']]['full']}"]),
                       lambda r: " · ".join(r))
        base = tr.run("impact", "gap_model", lambda: sim.simulate(zone_id),
                      lambda r: f"월별 {len(r)}개 시점 · 총 {r.attrs['total_hh']:,}세대 · 첫 입주 {C.ym(r.attrs['first'])}")
        fn = getattr(self, f"_{intent}")
        ans, chart = fn(tr, zone_id, base)
        tr.run("reporter", "summarize", lambda: len(ans), lambda r: f"답변 {r}자 · 근거 {len(tr.steps)}단계 · 가상 데이터 표기")
        return Reply(intent, ans, tr.steps, chart, nodes or [])

    # 의도별 처리 ------------------------------------------------------
    def _voc(self, tr, z, base):
        s = tr.run("voc_ingest", "query", lambda: voc_summary(self.voc, z), lambda r: f"최근 6개월 {r.get('n', 0):,}건")
        if not s or not s.get("n"):
            return "이 생활권은 아직 입주 전이라 쌓인 VOC가 없습니다. 위험 전망을 물어보시면 예측값으로 답하겠습니다.", None
        tr.run("voc_classifier", "classify", lambda: s["top"], lambda r: " · ".join(f"{C.VOC_CATS[k]['label']} {v}" for k, v in r.head(3).items()))
        chg = (s["n"] / s["prev"] - 1) * 100 if s["prev"] else 0
        top = s["top"]
        lines = [f"**{s['from']}~{s['to']}** {C.ZONES[z]['name']} VOC는 **{s['n']:,}건**으로 직전 6개월보다 **{chg:+.0f}%** 입니다.",
                 "유형별로는 " + ", ".join(f"{C.VOC_CATS[k]['label']} {v}건({v / s['n'] * 100:.0f}%)" for k, v in top.head(3).items()) + " 순입니다.",
                 f"안전 관련 등 우선처리(심각도 3) {s['severe']}건, 처리완료율 {s['done']:.0f}% 입니다.",
                 f"분류 신뢰도가 낮아 담당자 확인이 필요한 건은 **{s['review']}건**입니다 (HITL 검토 대기)."]
        data = pd.DataFrame({"cat": [C.VOC_CATS[k]["label"] for k in top.index], "n": top.values,
                             "color": [C.VOC_CATS[k]["color"] for k in top.index]})
        return "\n\n".join(lines), {"kind": "bar", "data": data, "x": "cat", "y": "n", "title": "최근 6개월 유형별 VOC"}

    def _cause(self, tr, z, base):
        t = min(C.NOW_T, int(base.t.max()))
        if base.iloc[t]["H"] < 50:
            t = int(base.attrs["first"]) + 12
        d = tr.run("impact", "decompose", lambda: {k: float(base.iloc[t][f"voc_{k}"]) for k in C.CAT_KEYS},
                   lambda r: f"{C.ym(t)} VOC 기대 {sum(r.values()):.1f}건/월을 7개 원인으로 분해")
        H = base.iloc[t]["H"]
        excess = {k: d[k] - H / 1000 * C.VOC_CATS[k]["rate"] for k in C.GAP_CATS}
        top = sorted(excess, key=excess.get, reverse=True)[:3]
        path = tr.run("ontology", "causal_path", lambda: O.CAUSAL_PATHS[0 if top[0] in ("school", "traffic", "park", "amenity") else 2],
                      lambda r: " → ".join(r))
        g = {k: base.iloc[t][f"g_{k}"] for k in C.GAP_CATS}
        lines = [f"**{C.ym(t)} 기준** 입주 {H:,.0f}세대, 생활불편지수 **{base.iloc[t]['inconv']:.0f}/100** 입니다.",
                 "평상시 수준을 넘는 VOC의 주원인은 " + ", ".join(
                     f"**{C.VOC_CATS[k]['driver']}**({C.VOC_CATS[k]['label']}, 갭 {g[k] * 100:.0f}%, +{excess[k]:.1f}건/월)" for k in top) + " 입니다.",
                 "인과 경로: " + " → ".join(path),
                 "※ 갭 = 해당 시설 수용력 대비 부족률. 계수는 가상값이며 실제 보정은 PoC 과제입니다."]
        data = pd.DataFrame({"cat": [C.VOC_CATS[k]["label"] for k in C.GAP_CATS], "n": [max(0, excess[k]) for k in C.GAP_CATS],
                             "color": [C.VOC_CATS[k]["color"] for k in C.GAP_CATS]}).sort_values("n", ascending=False)
        return "\n\n".join(lines), {"kind": "bar", "data": data, "x": "cat", "y": "n", "title": "평상시 대비 초과 VOC (건/월)"}

    def _risk(self, tr, z, base):
        t0 = max(C.NOW_T, int(base.attrs["first"]))
        fut = tr.run("impact", "forecast", lambda: base[(base.t >= t0) & (base.t < t0 + 24)],
                     lambda r: f"{C.ym(t0)}부터 24개월 · 위험등급 D/E {int(r.grade.isin(['D', 'E']).sum())}개월")
        bad = fut[fut.grade.isin(["D", "E"])]
        pk = fut.loc[fut.voc.idxmax()]
        lines = [f"{C.ym(t0)}부터 24개월 VOC 기대치는 **{fut.voc.sum():,.0f}건**, 월 최대 **{pk.voc:.0f}건({pk.ym})** 입니다.",
                 (f"위험등급 D·E(1천 세대당 월 11건 이상) 구간은 **{bad.ym.iloc[0]}~{bad.ym.iloc[-1]}, {len(bad)}개월** 입니다."
                  if len(bad) else "위험등급 D·E 구간은 예상되지 않습니다."),
                 "피크 시점의 주된 원인은 " + C.VOC_CATS[max(C.GAP_CATS, key=lambda k: pk[f'voc_{k}'])]["label"] + " 입니다. "
                 "시나리오 비교로 이 구간을 줄이는 대안을 볼 수 있습니다."]
        data = fut[["ym", "voc", "per1000", "grade"]].copy()
        return "\n\n".join(lines), {"kind": "line", "data": data, "x": "ym", "y": "voc", "title": "VOC 기대건수 (건/월)"}

    def _scenario(self, tr, z, base):
        cmp_ = tr.run("whatif", "compare", lambda: sim.compare(z), lambda r: f"{len(r)}개 시나리오 × 7개 지표 상대비교")
        alt = cmp_.iloc[1:]
        best = alt.loc[alt.voc_total.idxmin()]
        eff = alt.assign(eff=(-alt.voc_delta) / alt.cost.replace(0, np.nan)).dropna(subset=["eff"])
        e = eff.loc[eff.eff.idxmax()] if len(eff) else best
        lines = ["기준계획 대비 첫 입주 후 48개월 VOC 변화:",
                 *[f"- {r['name']}: **{r['voc_delta']:+.1f}%**, 생활불편 {r['inconv_delta']:+.1f}p, 추가비용 {r['cost']:.0f}억, 공정 +{r['delay']:.0f}개월"
                   for _, r in alt.iterrows()],
                 f"VOC 감소폭은 **{best['name']}**, 비용 대비 효율은 **{e['name']}**이 가장 큽니다.",
                 "주의: 학교·교통 레버는 교육청·지자체 협의가 필요하고, 공급 물량 조정은 공정 지연을 동반합니다."]
        data = cmp_[["name", "voc_delta"]].iloc[1:].rename(columns={"name": "cat", "voc_delta": "n"})
        data["color"] = [C.SCN_COLORS[i] for i in cmp_.id.iloc[1:]]
        return "\n".join(lines), {"kind": "bar", "data": data, "x": "cat", "y": "n", "title": "VOC 변화율 (%)"}

    def _optimize(self, tr, z, base):
        g = tr.run("whatif", "search", lambda: sim.search(z), lambda r: f"레버 조합 {len(r)}안 탐색 · 파레토 {int(r.pareto.sum())}안")
        g = g.assign(score=sim.score(g))
        top = g.sort_values("score", ascending=False).head(3)

        def desc(r):
            parts = []
            if r.school_shift:
                parts.append(f"학교 {int(r.school_shift)}개월 조기")
            if r.transit_boost:
                parts.append(f"교통 선투자 {r.transit_boost:.0%}")
            if r.temp:
                parts.append("임시대책")
            if r.volume_shift:
                parts.append(f"물량 {int(r.volume_shift)}개월 조정")
            return " + ".join(parts) or "기준계획 유지"
        lines = ["가중치 VOC 50 · 비용 30 · 공정 20 으로 54개 조합을 평가했습니다.",
                 *[f"{i + 1}. **{desc(r)}** — VOC {-r.voc_cut:+.1f}%, 비용 {r.cost:.0f}억, 공정 +{r.delay:.0f}개월, 점수 {r.score:.0f}"
                   for i, (_, r) in enumerate(top.iterrows())],
                 f"어느 지표로도 더 나은 안이 없는 파레토 안은 {int(g.pareto.sum())}개입니다. 가중치를 바꾸면 순위가 달라지니 What-if 화면에서 조절해 보세요."]
        data = g[["cost", "voc_cut", "delay", "pareto", "score"]]
        return "\n".join(lines), {"kind": "scatter", "data": data, "title": "비용 × VOC 감소 (54개 조합)"}

    def _sensitivity(self, tr, z, base):
        s, b = tr.run("whatif", "sensitivity", lambda: sim.sensitivity(z), lambda r: "6개 파라미터 × ±20% = 12회 재계산")
        topp = s.iloc[-1]
        rank0 = sim.compare(z).iloc[1:].sort_values("voc_total").id.tolist()
        lo = tr.run("whatif", "robustness", lambda: sim.compare(z, params={topp.param: .8}).iloc[1:].sort_values("voc_total").id.tolist(),
                    lambda r: f"{topp.label} −20%에서 순위 {' > '.join(r)}")
        hi = tr.run("whatif", "robustness", lambda: sim.compare(z, params={topp.param: 1.2}).iloc[1:].sort_values("voc_total").id.tolist(),
                    lambda r: f"{topp.label} +20%에서 순위 {' > '.join(r)}")
        same = rank0[0] == lo[0] == hi[0]
        lines = [f"기준계획 48개월 VOC {b:,.0f}건에 가장 크게 영향을 주는 값은 **{topp.label}**(±20% → {topp.low:+.0f} ~ {topp.high:+.0f}건),"
                 f" 다음은 **{s.iloc[-2].label}** 입니다.",
                 f"가장 영향이 큰 값을 ±20% 바꿔도 1순위 대안은 **{C.SCENARIOS[rank0[0]]['name']}**로 " + ("유지됩니다." if same else "바뀝니다 — 결론이 흔들리니 이 값의 실측 보정이 먼저입니다."),
                 "절대 건수는 계수에 따라 크게 흔들리므로, PoC에서는 대안 간 **상대 순위**를 판단 근거로 씁니다."]
        data = s[["label", "low", "high"]]
        return "\n\n".join(lines), {"kind": "tornado", "data": data, "title": "±20% 민감도 (VOC 건수 변화)"}

    def _persona(self, tr, z, base):
        lv = C.SCENARIOS["S5"]["levers"]
        alt = tr.run("whatif", "simulate", lambda: sim.simulate(z, lv), lambda r: "복합안(⑤) 조건 재계산")
        t = max(C.NOW_T, int(base.attrs["first"]) + 6)
        vs = tr.run("persona", "voice", lambda: [voice(p, drivers_at(base, t), drivers_at(alt, t)) for p in C.PERSONAS],
                    lambda r: f"{len(r)}개 유형 · {C.ym(t)} 시점 · 템플릿 생성(LLM 자리)")
        ab = tr.run("abm", "abm_run", lambda: sim.abm(z), lambda r: f"가구 Agent {r['agents']:,}개 × {C.HORIZON}개월")
        ab2 = tr.run("abm", "abm_run", lambda: sim.abm(z, lv), lambda r: f"복합안 조건 재실행 · Agent {r['agents']:,}개")
        f = int(base.attrs["first"])  # noqa: F841 (아래 query의 @f)
        n0 = ab["monthly"].query("t >= @f and t < @f + 48").n.sum()
        n1 = ab2["monthly"].query("t >= @f and t < @f + 48").n.sum()
        byp = ab["monthly"].query("t >= @f and t < @f + 48").groupby("persona").n.sum().sort_values(ascending=False)
        lines = [f"**{C.ym(t)} 시점 주민 Agent 목소리** (템플릿 생성 — 실제 LLM 연결 전)",
                 *[f"- *{v['name']}*: {v['text']}" for v in sorted(vs, key=lambda x: -x["level"])],
                 "",
                 f"ABM(가구 Agent {ab['agents']:,}개)에서 민원이 가장 많은 유형은 **{C.PERSONAS[byp.index[0]]['name']}**,"
                 f" 복합안 적용 시 48개월 민원은 **{(n1 / n0 - 1) * 100 if n0 else 0:+.0f}%** 입니다 (이웃 확산 효과 포함)."]
        data = byp.rename_axis("pid").reset_index()
        data["cat"] = [C.PERSONAS[p]["name"] for p in data.pid]
        data["color"] = [C.PERSONAS[p]["color"] for p in data.pid]
        return "\n".join(lines), {"kind": "bar", "data": data, "x": "cat", "y": "n", "title": "ABM 유형별 민원 (48개월, 기준)"}


# ── 자동 실행 기록 (관제 화면용, 가상) ───────────────────────────────
def run_log(hours: int = 24, now: datetime | None = None) -> pd.DataFrame:
    now = now or datetime.now(KST)
    start = (now - timedelta(hours=hours)).replace(minute=0, second=0, microsecond=0)
    sched = [("voc_ingest", 5, None, None), ("voc_classifier", 15, None, None), ("ontology", 0, 2, None),
             ("impact", 0, 6, None), ("persona", 0, 7, 0), ("abm", 0, 8, 0), ("reporter", 0, 9, 0)]
    rows = []
    h = start
    while h <= now:
        rng = np.random.default_rng(int(h.timestamp()) // 3600)
        for aid, mi, hr, wd in sched:
            if hr is not None and h.hour != hr:
                continue
            if wd is not None and h.weekday() != wd:
                continue
            ts = h + timedelta(minutes=mi, seconds=int(rng.integers(0, 50)))
            if ts > now:
                continue
            n = int(rng.poisson(6 if 8 <= h.hour <= 20 else 1.5))
            msg = {"voc_ingest": f"신규 VOC {n}건 수집 · 중복 {int(rng.integers(0, 2))}건 제거 · 개인정보 {n}건 마스킹",
                   "voc_classifier": f"{n}건 분류 · 신뢰도 낮음 {int(rng.binomial(n, .06))}건 → 검토 대기열",
                   "ontology": f"노드 {len(O.CLASSES)}종 · 관계 {len(O.RELATIONS)}종 무결성 확인 · 미연결 VOC {int(rng.integers(0, 4))}건",
                   "impact": f"생활권 {len(C.ZONES)}개 예측 갱신 · 위험등급 변동 {int(rng.integers(0, 3))}건",
                   "persona": f"주민 Agent 6종 민감도 재추정 (설문·VOC {int(rng.integers(80, 160))}건 반영)",
                   "abm": "생활권A 기준·복합안 ABM 2회 실행 · 확산 경보 0건",
                   "reporter": "주간 VOC·위험 요약 보고서 초안 생성"}[aid]
            fail = rng.random() < .015
            rows.append({"ts": ts, "agent": aid, "name": AG[aid]["name"], "msg": "재시도 대기 — 원천 응답 지연" if fail else msg,
                         "sec": float(np.round(rng.gamma(2, {"abm": 9, "impact": 4}.get(aid, 1.2)), 1)), "ok": not fail})
        h += timedelta(hours=1)
    return pd.DataFrame(rows).sort_values("ts", ascending=False).reset_index(drop=True)
