#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
로또9단 1등분석 기법 — 시뮬레이터 & 수학적 타당성 검증
===========================================================
목적: 책의 분석 기법을 충실히 구현해 '다음 주 예상번호'를 생성하되,
      그것이 무작위 대비 통계적으로 우월하지 않음을 검증한다.

입력 : data/raw_winner_all.json  (동행복권 1~최신 회차 전체)
출력 : data/draws.json           (정제 데이터)
        analysis/results.json     (대시보드용 결과)
        analysis/report.md        (수학적 리뷰 리포트)
"""
import json, math, random, statistics
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW  = ROOT / "data" / "raw_winner_all.json"
random.seed(20260624)  # 재현성

C45_6 = math.comb(45, 6)  # 8,145,060

# ───────────────────────── 1. 데이터 로드/정제 ─────────────────────────
raw = json.load(open(RAW, encoding="utf-8"))
draws = []
for d in raw:
    nums = sorted(d[f"당첨번호 {i}"] for i in range(1, 7))
    draws.append({"r": d["회차"], "date": d["추첨일"], "nums": nums, "bonus": d["보너스 번호"]})
draws.sort(key=lambda x: x["r"])
N = len(draws)
LAST = draws[-1]["r"]
json.dump(draws, open(ROOT / "data" / "draws.json", "w", encoding="utf-8"),
          ensure_ascii=False, separators=(",", ":"))

# ───────────────────────── 2. 헬퍼: 기법 지표 ─────────────────────────
def odd_even(nums):           # 홀짝 (홀 개수)
    return sum(1 for n in nums if n % 2)
def total_sum(nums):          # 총합
    return sum(nums)
def end_sum(nums):            # 끝수합 (일의 자리 합)
    return sum(n % 10 for n in nums)
def max_consec(nums):         # 최대 연속 길이
    s = sorted(nums); best = run = 1
    for i in range(1, len(s)):
        run = run + 1 if s[i] == s[i-1] + 1 else 1
        best = max(best, run)
    return best
def consec_pairs(nums):       # 연번 쌍 개수
    s = sorted(nums); return sum(1 for i in range(1, len(s)) if s[i] == s[i-1] + 1)
def band_spread(nums):        # 구간(10단위) 분포 — 사용된 구간 수
    return len(set((n - 1) // 10 for n in nums))

# ───────────────────────── 3. 역대 통계 ─────────────────────────
freq = Counter()
oe_dist = Counter(); sum_list = []; endsum_list = []; consec_dist = Counter()
for d in draws:
    freq.update(d["nums"])
    oe_dist[odd_even(d["nums"])] += 1
    sum_list.append(total_sum(d["nums"]))
    endsum_list.append(end_sum(d["nums"]))
    consec_dist[consec_pairs(d["nums"])] += 1

sum_mean, sum_sd = statistics.mean(sum_list), statistics.pstdev(sum_list)
freq_table = [{"n": n, "c": freq.get(n, 0)} for n in range(1, 46)]
hot  = sorted(range(1, 46), key=lambda n: -freq.get(n, 0))[:6]
cold = sorted(range(1, 46), key=lambda n:  freq.get(n, 0))[:6]

# ───── 검정 A: 번호 빈도 균일성 (카이제곱 적합도) ─────
# H0: 45개 번호가 균일분포. 기대도수 = 6N/45
exp = 6 * N / 45
chi2_uniform = sum((freq.get(n, 0) - exp) ** 2 / exp for n in range(1, 46))
df_uniform = 44
# 카이제곱 p-value (자유도 44) — 생존함수 근사(Wilson–Hilferty)
def chi2_sf(x, k):
    if x <= 0: return 1.0
    t = (x / k) ** (1/3)
    z = (t - (1 - 2/(9*k))) / math.sqrt(2/(9*k))
    # 표준정규 생존함수
    return 0.5 * math.erfc(z / math.sqrt(2))
p_uniform = chi2_sf(chi2_uniform, df_uniform)

# ───── 검정 B: '핫/콜드(나올 때 됐다)' 자기상관 검정 ─────
# 번호 n이 회차 t에 나오는 사건을 0/1로 보고, lag-1 자기상관 ϕ 평균.
# H0: 독립(무기억) → ϕ ≈ 0
phis = []
appear = {n: [1 if n in d["nums"] else 0 for d in draws] for n in range(1, 46)}
for n in range(1, 46):
    x = appear[n]; m = sum(x) / N
    num = sum((x[t] - m) * (x[t+1] - m) for t in range(N - 1))
    den = sum((v - m) ** 2 for v in x)
    if den > 0:
        phis.append(num / den)
mean_phi = statistics.mean(phis)
# 표준오차 ≈ 1/sqrt(N); z-점수
z_phi = mean_phi / (1 / math.sqrt(N))
p_phi = math.erfc(abs(z_phi) / math.sqrt(2))

# ───── 검정 C: '미출 간격(gap)' 무기억성 ─────
# 각 번호의 출현 간격이 기하분포(무기억)인지 — 평균 간격 vs 이론값 45/6=7.5
gaps = []
for n in range(1, 46):
    idx = [t for t, v in enumerate(appear[n]) if v]
    gaps += [idx[i] - idx[i-1] for i in range(1, len(idx))]
mean_gap = statistics.mean(gaps)
theo_gap = 45 / 6
cv_gap = statistics.pstdev(gaps) / mean_gap  # 기하분포면 CV≈1

# ───────────────────────── 4. 책의 기법을 구현한 생성기 ─────────────────────────
# 역대 데이터에서 도출한 '정상(正常) 패턴' 필터 (책의 PART4 '1등이 어려운 패턴' 제외)
def passes_filters(nums, prev=None):
    if not (100 <= total_sum(nums) <= 175):          # 총합 중심구간
        return False
    if odd_even(nums) in (0, 6):                      # 전부 홀/짝 제외
        return False
    if not (13 <= end_sum(nums) <= 38):               # 끝수합 구간
        return False
    if max_consec(nums) >= 3:                         # 3연번 이상 제외
        return False
    if band_spread(nums) < 3:                         # 한두 구간 몰림 제외
        return False
    if prev and len(set(nums) & set(prev)) >= 3:      # 제외수: 직전 회차 3개 이상 중복 제외
        return False
    return True

def book_generate(history, k=5):
    """history까지의 데이터만 사용해 책 기법으로 k게임 생성"""
    cnt = Counter()
    for d in history: cnt.update(d["nums"])
    prev = history[-1]["nums"] if history else None
    # 핫수 가중 (최근 흐름 반영) — 책의 '핫/콜드' 정신
    weights = {n: cnt.get(n, 0) + 1 for n in range(1, 46)}
    pool = list(range(1, 46))
    lines = []
    tries = 0
    while len(lines) < k and tries < 200000:
        tries += 1
        pick = tuple(sorted(random.sample(
            pool, 6)))  # 후보 추출
        # 가중 재추출: 핫수 선호 (수용/거절)
        w = sum(weights[n] for n in pick)
        if random.random() > (w / (6 * max(weights.values()))):
            continue
        if passes_filters(pick, prev) and pick not in lines:
            lines.append(pick)
    return [list(x) for x in lines]

def random_generate(k=5):
    return [sorted(random.sample(range(1, 46), 6)) for _ in range(k)]

# 필터 통과율: 역대 실제 당첨조합 중 몇 %가 필터를 통과하나?
pass_actual = sum(1 for i, d in enumerate(draws)
                  if passes_filters(d["nums"], draws[i-1]["nums"] if i else None))
pass_rate_actual = pass_actual / N
# 전체 조합 중 필터 통과 비율 (몬테카를로 추정)
mc = 200000
pass_mc = sum(1 for _ in range(mc)
              if passes_filters(sorted(random.sample(range(1, 46), 6))))
pass_rate_all = pass_mc / mc
filtered_pool = round(C45_6 * pass_rate_all)

# ───────────────────────── 5. 백테스트: 기법 vs 무작위 ─────────────────────────
# 각 회차 t에서 (t-1까지 데이터로) 5게임 생성 → 실제 t와 매칭 등수 집계.
PRIZE = {6: "1등", 5: "3등(보너스 무시 단순)", 4: "4등", 3: "5등"}
def grade(match): return match  # 단순 일치 개수
def backtest(strategy, start=200):
    tally = Counter(); total_match = 0; lines_cnt = 0
    for t in range(start, N):
        hist = draws[:t]
        actual = set(draws[t]["nums"])
        lines = strategy(hist) if strategy is book_generate else strategy()
        for ln in lines:
            m = len(actual & set(ln))
            tally[m] += 1; total_match += m; lines_cnt += 1
    return tally, total_match, lines_cnt

bt_book, book_tm, book_lc = backtest(book_generate)
bt_rand, rand_tm, rand_lc = backtest(lambda: random_generate())

def prize_count(tally): return sum(v for m, v in tally.items() if m >= 3)
book_prizes, rand_prizes = prize_count(bt_book), prize_count(bt_rand)
# 이론적 기대 3등이상(3,4,5,6 일치) 확률 per line
p_3plus = sum(math.comb(6, m) * math.comb(39, 6 - m) for m in (3, 4, 5, 6)) / C45_6
exp_prizes = p_3plus * book_lc

# 두 전략 당첨수 차이의 유의성 (포아송 근사 z-검정)
diff = book_prizes - rand_prizes
se_diff = math.sqrt(book_prizes + rand_prizes) if (book_prizes + rand_prizes) else 1
z_bt = diff / se_diff
p_bt = math.erfc(abs(z_bt) / math.sqrt(2))

# ───────────────────────── 6. 다음 주(LAST+1) 예상번호 ─────────────────────────
next_round = LAST + 1
predictions = book_generate(draws, k=5)
pred_meta = [{
    "nums": ln, "sum": total_sum(ln), "oddeven": f"{odd_even(ln)}:{6-odd_even(ln)}",
    "endsum": end_sum(ln), "consec": consec_pairs(ln), "bands": band_spread(ln)
} for ln in predictions]

# ───────────────────────── 7. 결과 저장 ─────────────────────────
results = {
    "meta": {"rounds": N, "last_round": LAST, "next_round": next_round,
             "C45_6": C45_6, "generated": "2026-06-24"},
    "freq": freq_table, "hot": hot, "cold": cold,
    "oe_dist": {str(k): v for k, v in sorted(oe_dist.items())},
    "sum_stats": {"mean": round(sum_mean, 2), "sd": round(sum_sd, 2),
                  "min": min(sum_list), "max": max(sum_list)},
    "sum_hist": dict(Counter((s // 10) * 10 for s in sum_list)),
    "endsum_stats": {"mean": round(statistics.mean(endsum_list), 2)},
    "consec_dist": {str(k): v for k, v in sorted(consec_dist.items())},
    "tests": {
        "uniform": {"chi2": round(chi2_uniform, 2), "df": df_uniform,
                    "p": p_uniform, "expected_each": round(exp, 1)},
        "autocorr": {"mean_phi": round(mean_phi, 5), "z": round(z_phi, 3), "p": round(p_phi, 4)},
        "gap": {"mean": round(mean_gap, 3), "theoretical": theo_gap, "cv": round(cv_gap, 3)},
    },
    "filters": {"pass_rate_actual": round(pass_rate_actual, 4),
                "pass_rate_all": round(pass_rate_all, 4),
                "filtered_pool": filtered_pool},
    "backtest": {
        "lines_each": book_lc, "start_round": 200,
        "book_prizes": book_prizes, "rand_prizes": rand_prizes,
        "expected_prizes": round(exp_prizes, 1),
        "book_total_match": book_tm, "rand_total_match": rand_tm,
        "book_dist": {str(k): v for k, v in sorted(bt_book.items())},
        "rand_dist": {str(k): v for k, v in sorted(bt_rand.items())},
        "z": round(z_bt, 3), "p": round(p_bt, 4),
        "p_3plus_per_line": p_3plus,
    },
    "predictions": pred_meta,
}
json.dump(results, open(ROOT / "analysis" / "results.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)

# ───────────────────────── 8. 콘솔 요약 ─────────────────────────
print(f"■ 데이터: {N}회차 (1~{LAST}), 다음 회차 = {next_round}")
print(f"■ [검정A] 번호 균일성 χ²({df_uniform})={chi2_uniform:.2f}, p={p_uniform:.3f}  "
      f"→ {'균일분포와 불일치(편향有)' if p_uniform<0.05 else '균일분포와 일치(편향 없음)'}")
print(f"■ [검정B] 핫/콜드 자기상관 평균ϕ={mean_phi:.5f}, z={z_phi:.2f}, p={p_phi:.3f}  "
      f"→ {'유의' if p_phi<0.05 else '독립(나올 때 됐다 = 근거없음)'}")
print(f"■ [검정C] 미출간격 평균={mean_gap:.2f}(이론 {theo_gap}), CV={cv_gap:.2f}(기하분포≈1)")
print(f"■ 필터 통과율: 실제당첨 {pass_rate_actual:.1%}, 전체조합 {pass_rate_all:.1%} "
      f"→ 후보풀 {filtered_pool:,} (전체의 {pass_rate_all:.1%})")
print(f"■ 백테스트({book_lc}게임씩): 기법 3등+이상 {book_prizes} vs 무작위 {rand_prizes} "
      f"(기대 {exp_prizes:.1f}), z={z_bt:.2f}, p={p_bt:.3f} "
      f"→ {'차이 유의' if p_bt<0.05 else '차이 없음(통계적 동일)'}")
print(f"■ 다음 주 {next_round}회 예상번호:")
for i, p in enumerate(pred_meta, 1):
    print(f"   {i}게임: {p['nums']}  합{p['sum']} {p['oddeven']} 끝수합{p['endsum']}")
print("\n결과 저장: analysis/results.json, data/draws.json")
