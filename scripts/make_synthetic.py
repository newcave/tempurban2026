# -*- coding: utf-8 -*-
"""가상 데이터 생성기 — data/ 폴더를 다시 만든다.
    python scripts/make_synthetic.py [--seed 2026]

만드는 것
  data/voc.csv      가상 VOC 민원 (입주 시작 ~ 2026-10, 기준계획 시뮬레이션의 기대건수에서 포아송 추출)
  data/monthly.csv  생활권별 기준계획 월별 시계열 (입주·공급·갭·생활불편·VOC 기대값)
  data/meta.json    생성 조건
※ 모든 값은 가상입니다. 실제 민원·사업 수치가 아닙니다."""
import argparse
import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from urb import catalog as C  # noqa: E402
from urb import sim  # noqa: E402
from urb.voc import SIDE, TEMPLATES  # noqa: E402

CHANNELS = ["홈페이지", "전화", "국민신문고", "방문", "현장 간담회"]


def main(seed: int = 2026):
    rng = np.random.default_rng(seed)
    out = ROOT / "data"
    out.mkdir(exist_ok=True)
    pids = list(C.PERSONAS)
    W = np.array([C.PERSONAS[p]["w"] + [.1] for p in pids])          # 마지막 열 = 하자(공통)
    share = np.array([C.PERSONAS[p]["share"] for p in pids])

    rows, mon = [], []
    for zid, z in C.ZONES.items():
        df = sim.simulate(zid)
        keep = ["t", "ym", "H", "dH", "seats", "transit_cap", "stores", "inconv", "voc", "per1000", "commute_min", "school_min", "grade"]
        keep += [c for c in df.columns if c.startswith(("g_", "voc_", "H_"))]
        m = df[keep].copy()
        m.insert(0, "zone", zid)
        mon.append(m)
        blocks = [b for b, _, _ in z["blocks"]]
        for t in range(0, C.NOW_T):
            r = df.iloc[t]
            if r["H"] < 50:
                continue
            noise = rng.lognormal(0, .18)
            for ci, k in enumerate(C.CAT_KEYS):
                n = rng.poisson(r[f"voc_{k}"] * noise)
                if not n:
                    continue
                bw = np.array([r[f"H_{b}"] for b in blocks]) + 1e-9
                pw = share * W[:, ci]
                for _ in range(n):
                    blk = blocks[rng.choice(len(blocks), p=bw / bw.sum())]
                    pi = rng.choice(len(pids), p=pw / pw.sum())
                    ch = C.PERSONAS[pids[pi]]["channel"] if rng.random() < .55 else CHANNELS[rng.integers(len(CHANNELS))]
                    y, mth = map(int, r["ym"].split("-"))
                    d = date(y, mth, int(rng.integers(1, 29)))
                    txt = TEMPLATES[k][rng.integers(len(TEMPLATES[k]))].format(blk=f"{blk}블록")
                    if rng.random() < .3:                                   # 다른 불편이 섞인 민원
                        o = C.CAT_KEYS[rng.integers(len(C.CAT_KEYS))]
                        if o != k:
                            txt += " " + SIDE[o][rng.integers(len(SIDE[o]))]
                    age = (date(2026, 11, 2) - d).days
                    resp = int(np.clip(rng.gamma(2.2, {"housing": 9, "school": 8, "traffic": 7}.get(k, 5)), 1, 90))
                    status = ("처리완료" if age > resp else "처리중") if rng.random() > .03 else "이관"
                    rows.append({"zone": zid, "site": z["site"], "block": blk, "date": d.isoformat(), "ym": r["ym"], "t": t,
                                 "channel": ch, "persona": pids[pi], "cat_true": k, "text": txt, "status": status,
                                 "resp_days": resp if status == "처리완료" else None})
    voc = pd.DataFrame(rows).sort_values(["date", "zone"]).reset_index(drop=True)
    voc.insert(0, "voc_id", [f"V{i + 1:05d}" for i in range(len(voc))])
    voc.to_csv(out / "voc.csv", index=False, encoding="utf-8-sig")
    pd.concat(mon).round(4).to_csv(out / "monthly.csv", index=False, encoding="utf-8-sig")
    meta = {"generated": date.today().isoformat(), "seed": seed, "now": C.ym(C.NOW_T), "voc_rows": len(voc),
            "note": "모든 값은 가상(synthetic) — 실제 민원·사업 수치 아님"}
    (out / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(meta)
    print(voc.groupby(["site", voc.ym.str[:4]]).size().unstack(fill_value=0))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=2026)
    main(ap.parse_args().seed)
