#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
구매 비교 실험 — '예측 20게임(서로 다른 시드)' vs '실제 구매 20게임' vs 실제 당첨번호.

목적: 책 기법으로 만든 예측 세트가 무작위 구매 세트와 통계적으로 다르지 않음을
      2만원(20게임) 실거래로 직접 비교해 보인다.

사용법
  python3 analysis/buy_set.py generate [회차] [게임수]     # 예측 세트 생성·잠금 (기본 20게임)
  python3 analysis/buy_set.py user <회차> "1 2 3 4 5 6, 7 8 ..."  # 실제 구매번호 입력(쉼표로 게임 구분)
  python3 analysis/buy_set.py score <회차> <n1..n6> <보너스>      # 둘 다 채점
  python3 analysis/buy_set.py score <회차> --auto                # data/draws.json에서 자동 채점

저장: analysis/compare_ledger.json   (compare.html 이 동적 로드)
"""
import json, random, sys
from datetime import datetime, timedelta
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DRAWS = ROOT / "data" / "draws.json"
CMP = ROOT / "analysis" / "compare_ledger.json"
BASE_SEED = 20260624

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

def one_line(history, rnd):
    cnt = Counter()
    for d in history: cnt.update(d["nums"])
    prev = history[-1]["nums"] if history else None
    weights = {n: cnt.get(n, 0) + 1 for n in range(1, 46)}
    wmax = max(weights.values())
    for _ in range(200000):
        pick = tuple(sorted(rnd.sample(range(1, 46), 6)))
        w = sum(weights[n] for n in pick)
        if rnd.random() > w / (6 * wmax): continue
        if passes(pick, prev): return list(pick)
    return sorted(rnd.sample(range(1, 46), 6))

def grade(match, has_bonus):
    if match == 6: return "1등"
    if match == 5 and has_bonus: return "2등"
    if match == 5: return "3등"
    if match == 4: return "4등"
    if match == 3: return "5등"
    return "꽝"

def next_saturday(date_str):
    return (datetime.strptime(date_str, "%Y%m%d") + timedelta(days=7)).strftime("%Y-%m-%d")

def load():
    return json.load(open(CMP, encoding="utf-8")) if CMP.exists() else {}
def save(d):
    json.dump(d, open(CMP, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

def cmd_generate(rnd_arg=None, count=20):
    draws = json.load(open(DRAWS, encoding="utf-8"))
    nxt = int(rnd_arg) if rnd_arg else draws[-1]["r"] + 1
    draw_date = next_saturday(draws[-1]["date"]) if nxt == draws[-1]["r"]+1 else "?"
    predicted = []
    for i in range(count):
        # 게임마다 '서로 다른 시드' — 같은 기법인데 시드만 바꿔도 번호가 전부 달라짐을 보임
        seed = BASE_SEED + nxt * 1000 + i
        r = random.Random(seed)
        predicted.append({"i": i + 1, "seed": seed, "nums": one_line(draws, r)})
    led = load()
    key = str(nxt)
    if key in led and led[key].get("predicted"):
        print(f"{nxt}회 예측 세트가 이미 잠겨 있습니다(보존)."); return
    led[key] = {
        "round": nxt, "draw_date": draw_date, "budget": count * 1000, "games": count,
        "locked_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "predicted": predicted, "user": None, "actual": None,
        "result": None, "status": "pending",
    }
    save(led)
    print(f"[locked] {nxt}회 예측 {count}게임 ({count*1000:,}원) — 추첨 {draw_date}")
    for p in predicted:
        print(f"  {p['i']:2d}) " + " ".join(f"{n:02d}" for n in p["nums"]) + f"   (seed {p['seed']})")
    print("\n→ 실제 판매점에서 20게임 구매 후: python3 analysis/buy_set.py user", nxt, '"...번호..."')

def cmd_user(rnd_arg, blob):
    led = load(); key = str(rnd_arg)
    if key not in led: print(f"{rnd_arg}회 실험이 없습니다. 먼저 generate."); sys.exit(1)
    games = []
    for g in blob.replace("\n", ",").split(","):
        ns = [int(x) for x in g.replace("-", " ").split()]
        if len(ns) == 6: games.append(sorted(ns))
    led[key]["user"] = [{"i": i+1, "nums": g} for i, g in enumerate(games)]
    save(led)
    print(f"[saved] {rnd_arg}회 실제 구매 {len(games)}게임 기록")
    for i, g in enumerate(games, 1):
        print(f"  {i:2d}) " + " ".join(f"{n:02d}" for n in g))

def score_set(games, nums, bonus):
    aset = set(nums); out = []; counts = Counter()
    for g in games:
        m = len(aset & set(g["nums"])); hb = bonus in set(g["nums"])
        gr = grade(m, hb); counts[gr] += 1
        out.append({**g, "match": m, "bonus": hb, "grade": gr})
    return out, counts

def cmd_score(rnd_arg, rest):
    led = load(); key = str(rnd_arg)
    if key not in led: print(f"{rnd_arg}회 실험이 없습니다."); sys.exit(1)
    e = led[key]
    if rest and rest[0] == "--auto":
        draws = {d["r"]: d for d in json.load(open(DRAWS, encoding="utf-8"))}
        if int(key) not in draws: print("draws.json에 해당 회차 없음."); sys.exit(1)
        d = draws[int(key)]; nums, bonus = d["nums"], d["bonus"]
    else:
        nums = list(map(int, rest[:6])); bonus = int(rest[6])
    pred_scored, pc = score_set(e["predicted"], nums, bonus)
    e["predicted"] = pred_scored
    user_summary = None
    if e.get("user"):
        user_scored, uc = score_set(e["user"], nums, bonus)
        e["user"] = user_scored; user_summary = dict(uc)
    e["actual"] = {"nums": sorted(nums), "bonus": bonus}
    def prize_won(c):
        # 4등 5만, 5등 5천 (고정분만 합산; 1~3등은 변동이라 별도)
        return c.get("4등",0)*50000 + c.get("5등",0)*5000
    e["result"] = {"predicted": dict(pc), "user": user_summary,
                   "pred_fixed_won": prize_won(pc),
                   "user_fixed_won": prize_won(uc) if e.get("user") else None}
    e["status"] = "scored"
    save(led)
    print(f"[scored] {key}회 실제 {sorted(nums)}+{bonus}")
    print("  예측 세트:", dict(pc), f"(고정상금 {prize_won(pc):,}원 / 투자 {e['budget']:,}원)")
    if user_summary:
        print("  실제구매 :", user_summary, f"(고정상금 {prize_won(uc):,}원 / 투자 {e['budget']:,}원)")

def main():
    a = sys.argv[1:]
    if not a: print(__doc__); return
    if a[0] == "generate":
        cmd_generate(a[1] if len(a) > 1 else None, int(a[2]) if len(a) > 2 else 20)
    elif a[0] == "user" and len(a) >= 3:
        cmd_user(a[1], " ".join(a[2:]))
    elif a[0] == "score" and len(a) >= 3:
        cmd_score(a[1], a[2:])
    else:
        print(__doc__)

if __name__ == "__main__":
    main()
