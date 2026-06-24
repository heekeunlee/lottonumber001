#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
주간 예측 생성기 — 다가오는 회차의 '예상번호' 5게임을 결정론적으로 잠그고
카카오톡 나챗방 발송용 메시지(≤200자)를 출력한다.

설계 원칙
- 사전등록(pre-registration): 회차번호로 시드를 고정 → 같은 회차는 언제 돌려도 동일.
- 격리(insulation): 본 생성기는 독립 RNG만 사용(다른 분석 코드와 난수 스트림 분리).
- 잠금(lock): analysis/predictions_ledger.json 에 추첨 전 기록(이미 있으면 보존).

출력: stdout 마지막 줄에 '<<<KAKAO>>>' 다음 줄부터 카톡 메시지 본문.
"""
import json, random, sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DRAWS = ROOT / "data" / "draws.json"
LEDGER = ROOT / "analysis" / "predictions_ledger.json"
BASE_SEED = 20260624

CIRC = "①②③④⑤⑥⑦⑧⑨⑩"

def total_sum(ns): return sum(ns)
def odd_even(ns): return sum(1 for n in ns if n % 2)
def end_sum(ns): return sum(n % 10 for n in ns)
def max_consec(ns):
    s = sorted(ns); best = run = 1
    for i in range(1, len(s)):
        run = run + 1 if s[i] == s[i-1]+1 else 1; best = max(best, run)
    return best
def band_spread(ns): return len(set((n-1)//10 for n in ns))

def passes(ns, prev):
    if not (100 <= total_sum(ns) <= 175): return False
    if odd_even(ns) in (0, 6): return False
    if not (13 <= end_sum(ns) <= 38): return False
    if max_consec(ns) >= 3: return False
    if band_spread(ns) < 3: return False
    if prev and len(set(ns) & set(prev)) >= 3: return False
    return True

def generate(history, rnd, k=5):
    from collections import Counter
    cnt = Counter()
    for d in history: cnt.update(d["nums"])
    prev = history[-1]["nums"] if history else None
    weights = {n: cnt.get(n, 0) + 1 for n in range(1, 46)}
    wmax = max(weights.values())
    lines, tries = [], 0
    while len(lines) < k and tries < 300000:
        tries += 1
        pick = tuple(sorted(rnd.sample(range(1, 46), 6)))
        w = sum(weights[n] for n in pick)
        if rnd.random() > w / (6 * wmax): continue
        if passes(pick, prev) and pick not in lines:
            lines.append(pick)
    return [list(x) for x in lines]

def next_saturday(date_str):
    d = datetime.strptime(date_str, "%Y%m%d")
    return (d + timedelta(days=7)).strftime("%Y-%m-%d")

def main():
    draws = json.load(open(DRAWS, encoding="utf-8"))
    last = draws[-1]
    nxt = last["r"] + 1
    draw_date = next_saturday(last["date"])

    # 회차 고정 시드 → 사전등록·재현 가능, 다른 코드와 격리
    rnd = random.Random(BASE_SEED + nxt)
    lines = generate(draws, rnd, k=5)

    # 원장 잠금 (이미 있으면 기존 보존)
    ledger = {}
    if LEDGER.exists():
        ledger = json.load(open(LEDGER, encoding="utf-8"))
    key = str(nxt)
    if key not in ledger:
        ledger[key] = {
            "round": nxt, "draw_date": draw_date,
            "locked_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "lines": lines, "status": "pending",
            "actual": None, "matches": None, "best": None,
        }
        json.dump(ledger, open(LEDGER, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
        locked_lines = lines
    else:
        locked_lines = ledger[key]["lines"]   # 이미 잠긴 예측 사용

    # 카톡 메시지(≤200자)
    body = [f"🎰 {nxt}회({draw_date[5:]}) 예상번호"]
    for i, ln in enumerate(locked_lines):
        body.append(f"{CIRC[i]}" + " ".join(f"{n:02d}" for n in ln))
    body.append("⚠️예측력0·오락용 각1/814만")
    msg = "\n".join(body)
    if len(msg) > 200:  # 안전장치
        msg = msg[:197] + "…"

    print(f"[locked] {nxt}회 ({draw_date}) / 메시지 {len(msg)}자")
    print("<<<KAKAO>>>")
    print(msg)

if __name__ == "__main__":
    main()
