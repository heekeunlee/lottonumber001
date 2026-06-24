#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
채점기 — 잠긴 예측(predictions_ledger.json)을 실제 당첨번호와 대조해 갱신한다.

사용법
  python3 analysis/score_ledger.py 1230 3 11 18 27 38 42 7
     · 인자: <회차> <n1..n6> <보너스>
  python3 analysis/score_ledger.py --auto
     · data/draws.json 에 이미 들어온 회차를 자동 채점(원장의 pending 중 결과 보유분).

판정
  6일치=1등, 5+보너스=2등, 5일치=3등, 4일치=4등, 3일치=5등, 그 외=꽝
"""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / "analysis" / "predictions_ledger.json"
DRAWS = ROOT / "data" / "draws.json"

def grade(match, has_bonus):
    if match == 6: return "1등"
    if match == 5 and has_bonus: return "2등"
    if match == 5: return "3등"
    if match == 4: return "4등"
    if match == 3: return "5등"
    return "꽝"

def score_round(entry, nums, bonus):
    aset = set(nums)
    res = []
    best_rank, best_idx = "꽝", -1
    order = ["1등","2등","3등","4등","5등","꽝"]
    for i, ln in enumerate(entry["lines"]):
        m = len(aset & set(ln))
        hb = bonus in set(ln)
        g = grade(m, hb)
        res.append({"line": ln, "match": m, "bonus": hb, "grade": g})
        if order.index(g) < order.index(best_rank):
            best_rank, best_idx = g, i
    entry["actual"] = {"nums": sorted(nums), "bonus": bonus}
    entry["matches"] = res
    entry["best"] = best_rank
    entry["status"] = "scored"
    return entry

def main():
    ledger = json.load(open(LEDGER, encoding="utf-8")) if LEDGER.exists() else {}
    args = sys.argv[1:]
    if args and args[0] == "--auto":
        draws = {d["r"]: d for d in json.load(open(DRAWS, encoding="utf-8"))}
        done = 0
        for k, e in ledger.items():
            if e["status"] == "pending" and int(k) in draws:
                d = draws[int(k)]
                score_round(e, d["nums"], d["bonus"]); done += 1
                print(f"[scored] {k}회 → 최고 {e['best']}")
        print(f"자동 채점 {done}건")
    elif len(args) >= 8:
        rnd = args[0]; nums = list(map(int, args[1:7])); bonus = int(args[7])
        if rnd not in ledger:
            print(f"원장에 {rnd}회 예측이 없습니다."); sys.exit(1)
        e = score_round(ledger[rnd], nums, bonus)
        print(f"[scored] {rnd}회 실제 {sorted(nums)}+{bonus} → 최고 {e['best']}")
        for r in e["matches"]:
            print(f"   {r['line']}  {r['match']}일치{'+보너스' if r['bonus'] else ''} → {r['grade']}")
    else:
        print(__doc__); sys.exit(0)
    json.dump(ledger, open(LEDGER, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
