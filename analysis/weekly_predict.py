#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
주간 예측 생성기(5게임) — 충실 기법(method.Method) 기반.
다가오는 회차의 예상번호 5게임을 결정론적으로 잠그고 카톡 메시지(≤200자)를 출력한다.

- 사전등록: 회차번호로 시드 고정 → 같은 회차는 언제 돌려도 동일.
- 격리: 독립 RNG 사용(다른 분석 코드와 난수 스트림 분리).
- 잠금: analysis/predictions_ledger.json 에 추첨 전 기록(이미 있으면 보존).
출력: stdout에 '<<<KAKAO>>>' 다음 줄부터 카톡 본문.
"""
import json, random
from datetime import datetime, timedelta
from pathlib import Path
import method

ROOT = Path(__file__).resolve().parent.parent
DRAWS = ROOT / "data" / "draws.json"
LEDGER = ROOT / "analysis" / "predictions_ledger.json"
BASE_SEED = 20260624
CIRC = "①②③④⑤⑥⑦⑧⑨⑩"

def next_saturday(s):
    return (datetime.strptime(s, "%Y%m%d") + timedelta(days=7)).strftime("%Y-%m-%d")

def main():
    draws = json.load(open(DRAWS, encoding="utf-8"))
    nxt = draws[-1]["r"] + 1
    draw_date = next_saturday(draws[-1]["date"])
    rnd = random.Random(BASE_SEED + nxt)
    m = method.Method(draws, fixed_k=1)
    lines = m.distinct(rnd, 5)
    meta = m.meta()

    ledger = json.load(open(LEDGER, encoding="utf-8")) if LEDGER.exists() else {}
    key = str(nxt)
    if key not in ledger:
        ledger[key] = {
            "round": nxt, "draw_date": draw_date,
            "locked_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "method": "faithful-v2", "fixed": meta["fixed"], "cold_thr": meta["cold_thr"],
            "lines": lines, "status": "pending",
            "actual": None, "matches": None, "best": None,
        }
        json.dump(ledger, open(LEDGER, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        locked = lines
    else:
        locked = ledger[key]["lines"]

    body = [f"🎰 {nxt}회({draw_date[5:]}) 예상 고정수{meta['fixed'][0]:02d}"]
    for i, ln in enumerate(locked):
        body.append(f"{CIRC[i]}" + " ".join(f"{n:02d}" for n in ln))
    body.append(method.METHOD_KEYWORDS)
    msg = "\n".join(body)
    if len(msg) > 200: msg = msg[:197] + "…"

    print(f"[locked] {nxt}회 ({draw_date}) 고정수={meta['fixed']} 콜드임계={meta['cold_thr']} / {len(msg)}자")
    print("<<<KAKAO>>>")
    print(msg)

if __name__ == "__main__":
    main()
