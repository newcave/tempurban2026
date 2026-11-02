# -*- coding: utf-8 -*-
"""VOC 분석 — 가상 민원 + VOC 분류 에이전트 결과 (유형·심각도·관련 시설·담당)"""
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from urb import catalog as C
from urb import data as D
from urb import voc as V
from urb import ui

voc = D.voc()
ui.page_header("Voice of Customer", "VOC 분석",
               "입주 이후 쌓인 민원을 분류 에이전트가 유형·심각도·관련 시설로 태깅한 결과입니다. "
               "신뢰도가 낮은 건은 담당자 검토(HITL) 대기열로 보냅니다.",
               [f"가상 VOC <b>{len(voc):,}건</b>", f"~ <b>{voc.ym.max()}</b>", "분류 = 규칙 기반 (LLM 자리)"])

sites = [s for s in C.SITES if (voc.site == s).any()]
c0, c1, c2 = st.columns([1.6, 1.2, 1], gap="medium")
with c0:
    site = st.segmented_control("사업지", ["ALL"] + sites, default="EDC",
                                format_func=lambda k: "전체" if k == "ALL" else C.SITES[k]["name"], key="voc_site") or "ALL"
with c1:
    zopts = ["ALL"] + [z for z in C.ZONES if (voc.zone == z).any() and (site == "ALL" or C.ZONES[z]["site"] == site)]
    zone = st.selectbox("생활권", zopts, format_func=lambda k: "전체" if k == "ALL" else C.ZONES[k]["name"], key="voc_zone")
with c2:
    yrs = sorted(voc.ym.str[:4].unique())
    yr = st.select_slider("기간", options=yrs, value=(yrs[0], yrs[-1]), key="voc_years")

v = voc[(voc.ym.str[:4] >= yr[0]) & (voc.ym.str[:4] <= yr[1])]
if site != "ALL":
    v = v[v.site == site]
if zone != "ALL":
    v = v[v.zone == zone]
if v.empty:
    st.info("선택한 조건에 VOC가 없습니다.")
    st.stop()

last12 = v[v.t > v.t.max() - 12]
done = v[v.status == "처리완료"]
top = v.pred_cat.value_counts()
mon = v.groupby("ym").size()
ui.kpis([
    {"label": "VOC 건수", "value": f"{len(v):,}", "unit": "건", "sub": f"{yr[0]}~{yr[1]}", "spark": list(mon.values[-18:]), "color": ui.ACCENT},
    {"label": "최근 12개월", "value": f"{len(last12):,}", "unit": "건", "sub": f"월평균 {len(last12) / 12:.0f}건", "color": "#22d3ee"},
    {"label": "1위 유형", "value": C.VOC_CATS[top.index[0]]["label"], "sub": f"{top.iloc[0] / len(v) * 100:.0f}% · {top.iloc[0]:,}건",
     "color": C.VOC_CATS[top.index[0]]["color"]},
    {"label": "처리완료율", "value": f"{len(done) / len(v) * 100:.0f}", "unit": "%", "sub": f"평균 {done.resp_days.mean():.0f}일", "color": "#34d399"},
    {"label": "우선처리 (심각도 3)", "value": f"{(v.severity == 3).sum():,}", "unit": "건", "sub": "안전·장시간 불편 표현", "color": "#f87171"},
    {"label": "검토 대기 (HITL)", "value": f"{(v.conf < .75).sum():,}", "unit": "건", "sub": "분류 신뢰도 0.75 미만", "color": "#f59e0b"},
])

with ui.card("trend", "월별 VOC와 입주 세대", "막대 = 분류 에이전트 유형별 건수 · 선 = 입주 세대(기준계획 모형)", "Trend"):
    piv = v.pivot_table(index="ym", columns="pred_cat", values="voc_id", aggfunc="count", fill_value=0).sort_index()
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    for k in C.CAT_KEYS:
        if k in piv:
            fig.add_bar(x=piv.index, y=piv[k], name=C.VOC_CATS[k]["label"], marker_color=C.VOC_CATS[k]["color"],
                        hovertemplate=C.VOC_CATS[k]["label"] + " · %{x} · %{y}건<extra></extra>")
    zs = [zone] if zone != "ALL" else sorted(v.zone.unique())
    H = sum(D.simulate(zz).set_index("ym")["H"] for zz in zs).reindex(piv.index)
    fig.add_scatter(x=piv.index, y=H, name="입주 세대", line=dict(color="#e2e8f0", width=2, dash="dot"), secondary_y=True,
                    hovertemplate="입주 %{y:,.0f}세대<extra></extra>")
    ui.style(fig, 340)
    fig.update_layout(barmode="stack", bargap=.15)
    fig.update_xaxes(type="category", nticks=12)
    fig.update_yaxes(title="건", secondary_y=False)
    fig.update_yaxes(title="세대", secondary_y=True, showgrid=False, rangemode="tozero")
    fig.update_yaxes(rangemode="tozero", secondary_y=False)
    ui.plot(fig, "voc_trend")

c1, c2, c3 = st.columns([1, 1.3, 1], gap="medium")
with c1:
    with ui.card("mix", "유형 구성", "분류 에이전트 결과", "Mix"):
        ui.ranked([{"label": C.VOC_CATS[k]["label"], "value": n / len(v) * 100, "color": C.VOC_CATS[k]["color"], "sub": f"{n:,}건"}
                   for k, n in top.items()])
with c2:
    with ui.card("blk", "블록 × 유형", "같은 생활권에서도 블록마다 불편이 다릅니다", "Block"):
        hb = v.pivot_table(index="block", columns="pred_cat", values="voc_id", aggfunc="count", fill_value=0)
        hb = hb[[k for k in C.CAT_KEYS if k in hb]]
        fig = go.Figure(go.Heatmap(z=hb.values, x=[C.VOC_CATS[k]["label"] for k in hb.columns], y=hb.index,
                                   colorscale=[[0, "#0f172a"], [.5, "#6d28d9"], [1, "#e9d5ff"]], showscale=False,
                                   text=hb.values, texttemplate="%{text}", textfont=dict(size=10),
                                   hovertemplate="%{y} · %{x} · %{z}건<extra></extra>"))
        ui.style(fig, 280, legend=False)
        ui.plot(fig, "voc_blk")
with c3:
    with ui.card("ch", "접수 채널", "", "Channel"):
        ch = v.channel.value_counts()
        ui.ranked([{"label": k, "value": n / len(v) * 100, "sub": f"{n:,}건"} for k, n in ch.items()])

c1, c2 = st.columns([1.2, 1], gap="medium")
with c1:
    with ui.card("cls", "VOC 분류 에이전트 체험", "문장을 넣으면 유형·심각도·관련 시설·담당·처리 안내문 초안을 돌려줍니다", "Agent"):
        txt = st.text_area("민원 문장", "통학로 보도가 끊겨서 아이들이 공사 차량 옆 차도로 걸어 다녀요. 버스도 너무 늦게 옵니다.",
                           height=90, key="voc_txt", label_visibility="collapsed")
        r = V.classify(txt)
        sev = {1: "1 · 일반", 2: "2 · 요청", 3: "3 · 우선처리"}[r["severity"]]
        ui.h(f'<div class="cls"><div><span>유형</span><b style="color:{C.VOC_CATS[r["cat"]]["color"]}">{r["label"]}</b></div>'
             f'<div><span>신뢰도</span><b>{r["conf"]:.2f}{" · 검토 필요" if r["conf"] < .75 else ""}</b></div>'
             f'<div><span>심각도</span><b>{sev}</b></div><div><span>담당</span><b style="font-size:.8rem">{r["owner"]}</b></div></div>')
        ui.h('<div class="tps">' + "".join(f"<span>{ui.esc(e)}</span>" for e in r["entities"]) + "</div>")
        sc = sorted(((k, s) for k, s in r["scores"].items() if s > 0), key=lambda x: -x[1])
        ui.note("유형별 점수: " + " · ".join(f"{C.VOC_CATS[k]['label']} {s:.1f}" for k, s in sc) + f" · 엔진 = {r['engine']}")
        ui.h(f'<div class="answer"><span class="layer">처리 안내문 초안 · 보고서 작성 에이전트</span>'
             f'<p style="margin:6px 0 0;color:#e2e8f0;font-size:.85rem;line-height:1.6">{ui.esc(V.reply_draft(r, ""))}</p></div>')
with c2:
    with ui.card("acc", "분류 품질 (가상 정답 대비)", "가상 데이터에는 생성 시 정답 유형이 있어 분류기를 채점할 수 있습니다", "Quality"):
        acc = (v.pred_cat == v.cat_true).mean() * 100
        per = (v.pred_cat == v.cat_true).groupby(v.cat_true).mean().mul(100).sort_values()
        ui.h(f'<div class="fx"><div><span>정확도</span><b>{acc:.1f}<small>%</small></b></div>'
             f'<div><span>검토 대기열</span><b>{(v.conf < .75).sum():,}<small>건</small></b></div></div>')
        ui.ranked([{"label": C.VOC_CATS[k]["label"], "value": p, "color": C.VOC_CATS[k]["color"]} for k, p in per.items()], max_val=100)
        ui.note("실데이터에서는 정답이 없으므로, 담당자 검토(HITL) 결과를 쌓아 정답셋을 만드는 것이 1차년도 과제입니다.")

with ui.card("list", "최근 VOC", "분류 에이전트 태그가 붙은 원장 (가상)", "Ledger"):
    show = v.sort_values("date", ascending=False).head(300)
    st.dataframe(show[["voc_id", "date", "zone", "block", "channel", "text", "label", "conf", "severity", "entities", "owner", "status"]]
                 .rename(columns={"voc_id": "ID", "date": "접수일", "zone": "생활권", "block": "블록", "channel": "채널", "text": "내용",
                                  "label": "유형", "conf": "신뢰도", "severity": "심각도", "entities": "관련 개체", "owner": "담당", "status": "상태"}),
                 hide_index=True, height=330,
                 column_config={"신뢰도": st.column_config.ProgressColumn(min_value=0, max_value=1, format="%.2f"),
                                "내용": st.column_config.TextColumn(width="large")})
    st.download_button("CSV 내려받기 (가상)", show.to_csv(index=False).encode("utf-8-sig"), "voc_sample.csv", "text/csv", key="voc_dl")
