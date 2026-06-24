#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
구매 비교 실험 — '예측 20게임(서로 다른 시드)' vs '실제 구매 20게임' vs 실제 당첨번호.
충실 기법(method.Method): 미출 기간표(핫/콜드) + 고정수 + 통계필터 + 핫수가중.

사용법
  python3 analysis/buy_set.py generate [회차] [게임수] [--force]   # 예측 세트 생성·잠금 (기본 20)
  python3 analysis/buy_set.py weekly                              # 다가오는 회차 자동 생성 + 카톡 알림 출력
  python3 analysis/buy_set.py user <회차> "1 2 3 4 5 6, 7 8 ..."   # 실제 구매번호 입력
  python3 analysis/buy_set.py score <회차> <n1..n6> <보너스>        # 둘 다 채점
  python3 analysis/buy_set.py score <회차> --auto                 # draws.json에서 자동 채점

저장: analysis/compare_ledger.json   (compare.html 이 동적 로드)
공개 대시보드: https://heekeunlee.github.io/lottonumber001/compare.html
"""
import json, random, sys
from datetime import datetime, timedelta
from collections import Counter
from pathlib import Path
import method

ROOT = Path(__file__).resolve().parent.parent
DRAWS = ROOT / "data" / "draws.json"
CMP = ROOT / "analysis" / "compare_ledger.json"
BASE_SEED = 20260624
SITE = "https://heekeunlee.github.io/lottonumber001/compare.html"

def grade(match, has_bonus):
    if match == 6: return "1등"
    if match == 5 and has_bonus: return "2등"
    if match == 5: return "3등"
    if match == 4: return "4등"
    if match == 3: return "5등"
    return "꽝"

def next_saturday(s):
    return (datetime.strptime(s, "%Y%m%d") + timedelta(days=7)).strftime("%Y-%m-%d")

def load(): return json.load(open(CMP, encoding="utf-8")) if CMP.exists() else {}
def save(d): json.dump(d, open(CMP, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

def build_predicted(draws, nxt, count):
    m = method.Method(draws, fixed_k=1)
    predicted = []
    for i in range(count):
        seed = BASE_SEED + nxt * 1000 + i        # 게임마다 다른 시드
        predicted.append({"i": i + 1, "seed": seed, "nums": m.line(random.Random(seed))})
    return predicted, m.meta()

def cmd_generate(rnd_arg=None, count=20, force=False):
    draws = json.load(open(DRAWS, encoding="utf-8"))
    nxt = int(rnd_arg) if rnd_arg else draws[-1]["r"] + 1
    draw_date = next_saturday(draws[-1]["date"]) if nxt == draws[-1]["r"]+1 else "?"
    led = load(); key = str(nxt)
    if key in led and led[key].get("predicted") and not force:
        print(f"{nxt}회 예측 세트가 이미 잠겨 있습니다(보존). 덮어쓰려면 --force."); return led, key
    predicted, meta = build_predicted(draws, nxt, count)
    led[key] = {
        "round": nxt, "draw_date": draw_date, "budget": count*1000, "games": count,
        "locked_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "method": "faithful-v2", "fixed": meta["fixed"], "cold_thr": meta["cold_thr"],
        "predicted": predicted, "user": led.get(key, {}).get("user"),
        "actual": None, "result": None, "status": "pending",
    }
    save(led)
    print(f"[locked] {nxt}회 예측 {count}게임 ({count*1000:,}원) 고정수={meta['fixed']} 콜드임계={meta['cold_thr']} — 추첨 {draw_date}")
    for p in predicted:
        print(f"  {p['i']:2d}) " + " ".join(f"{n:02d}" for n in p["nums"]) + f"   (seed {p['seed']})")
    return led, key

def cmd_weekly():
    led, key = cmd_generate(None, 20, force=False)
    e = led[key]
    games = e["predicted"]
    fixed = e["fixed"][0]
    n_blocks = (len(games) + 4) // 5
    # 5게임씩 끊어 여러 통(각 ≤200자)으로 발송. 마지막 줄에 면책 1회.
    for b in range(n_blocks):
        chunk = games[b*5:(b+1)*5]
        head = f"🎰{e['round']}회({e['draw_date'][5:]}) 비교 {e['games']}게임 [{b+1}/{n_blocks}] 고정수{fixed:02d}"
        lines = [head] + [f"{g['i']:2d}) " + " ".join(f"{n:02d}" for n in g["nums"]) for g in chunk]
        if b == n_blocks - 1:
            lines.append("⚠️예측력0·오락용 각1/814만")
        msg = "\n".join(lines)
        if len(msg) > 200: msg = msg[:197] + "…"
        print("<<<KAKAO>>>")
        print(msg)

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
    pred_scored, pc = score_set(e["predicted"], nums, bonus); e["predicted"] = pred_scored
    uc = Counter()
    if e.get("user"):
        e["user"], uc = score_set(e["user"], nums, bonus)
    e["actual"] = {"nums": sorted(nums), "bonus": bonus}
    fixed_won = lambda c: c.get("4등",0)*50000 + c.get("5등",0)*5000
    e["result"] = {"predicted": dict(pc), "user": dict(uc) if e.get("user") else None,
                   "pred_fixed_won": fixed_won(pc),
                   "user_fixed_won": fixed_won(uc) if e.get("user") else None}
    e["status"] = "scored"; save(led)
    print(f"[scored] {key}회 실제 {sorted(nums)}+{bonus}")
    print("  예측:", dict(pc), f"(고정상금 {fixed_won(pc):,}원/투자 {e['budget']:,}원)")
    if e.get("user"):
        print("  실구매:", dict(uc), f"(고정상금 {fixed_won(uc):,}원/투자 {e['budget']:,}원)")

def main():
    a = sys.argv[1:]
    if not a: print(__doc__); return
    if a[0] == "generate":
        pos = [x for x in a[1:] if x != "--force"]
        cmd_generate(pos[0] if len(pos) > 0 else None,
                     int(pos[1]) if len(pos) > 1 else 20, "--force" in a)
    elif a[0] == "weekly":
        cmd_weekly()
    elif a[0] == "user" and len(a) >= 3:
        cmd_user(a[1], " ".join(a[2:]))
    elif a[0] == "score" and len(a) >= 3:
        cmd_score(a[1], a[2:])
    else:
        print(__doc__)

if __name__ == "__main__":
    main()
