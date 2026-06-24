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

# ───── 정밀 통계 함수 (외부 의존성 없이 exact) ─────
def _gammln(x):
    cof = [76.18009172947146, -86.50532032941677, 24.01409824083091,
           -1.231739572450155, 0.1208650973866179e-2, -0.5395239384953e-5]
    y = x; tmp = x + 5.5; tmp -= (x + 0.5) * math.log(tmp); ser = 1.000000000190015
    for c in cof:
        y += 1; ser += c / y
    return -tmp + math.log(2.5066282746310005 * ser / x)

def _gammq(a, x):
    """정칙 상측 불완전감마 Q(a,x) — Numerical Recipes (series/continued fraction)"""
    if x < 0 or a <= 0: return float("nan")
    if x < a + 1.0:                     # 급수 전개
        ap = a; s = 1.0 / a; dl = s
        for _ in range(500):
            ap += 1; dl *= x / ap; s += dl
            if abs(dl) < abs(s) * 1e-14: break
        return 1.0 - s * math.exp(-x + a * math.log(x) - _gammln(a))
    # 연분수 전개
    b = x + 1.0 - a; c = 1e308; d = 1.0 / b; h = d
    for i in range(1, 500):
        an = -i * (i - a); b += 2.0
        d = an * d + b
        if abs(d) < 1e-300: d = 1e-300
        c = b + an / c
        if abs(c) < 1e-300: c = 1e-300
        d = 1.0 / d; de = d * c; h *= de
        if abs(de - 1.0) < 1e-14: break
    return math.exp(-x + a * math.log(x) - _gammln(a)) * h

def chi2_sf(x, k):                       # χ² 생존함수 = Q(k/2, x/2) — exact
    if x <= 0: return 1.0
    return _gammq(k / 2.0, x / 2.0)

def norm_sf2(z):                         # 표준정규 양측 p값
    return math.erfc(abs(z) / math.sqrt(2))

# ───── 검정 A: 번호 빈도 균일성 (카이제곱 적합도) ─────
# H0: 45개 번호가 균일분포. 기대도수 = 6N/45
exp = 6 * N / 45
chi2_uniform = sum((freq.get(n, 0) - exp) ** 2 / exp for n in range(1, 46))
df_uniform = 44
p_uniform = chi2_sf(chi2_uniform, df_uniform)  # 정밀(exact) p값

# ───── 검정 B: '핫/콜드(나올 때 됐다)' 자기상관 검정 + 다중비교 보정 ─────
# 번호 n이 회차 t에 나오는 사건을 0/1로 보고, lag-1 자기상관 ϕ를 번호별로 검정.
# H0: 각 번호는 독립(무기억) → ϕ ≈ 0.  45개 동시검정이므로 BH(FDR) 보정.
appear = {n: [1 if n in d["nums"] else 0 for d in draws] for n in range(1, 46)}
per_num = []   # (번호, phi, z, p)
for n in range(1, 46):
    x = appear[n]; m = sum(x) / N
    num = sum((x[t] - m) * (x[t+1] - m) for t in range(N - 1))
    den = sum((v - m) ** 2 for v in x)
    phi = num / den if den > 0 else 0.0
    z = phi * math.sqrt(N)                 # SE(ϕ) ≈ 1/√N
    per_num.append((n, phi, z, norm_sf2(z)))
phis = [p[1] for p in per_num]
mean_phi = statistics.mean(phis)
z_phi = mean_phi / (1 / math.sqrt(N))      # 전체 평균 ϕ의 z
p_phi = norm_sf2(z_phi)

# Benjamini–Hochberg (FDR=0.05): 보정 후 유의한 번호 개수
def benjamini_hochberg(pvals, q=0.05):
    m = len(pvals)
    order = sorted(range(m), key=lambda i: pvals[i])
    thresh = 0; crit = []
    for rank, idx in enumerate(order, 1):
        c = rank / m * q; crit.append((idx, pvals[idx], c))
        if pvals[idx] <= c: thresh = rank
    rejected = set(order[i] for i in range(thresh))
    # 보정 p값 (q-value)
    adj = [0.0] * m; prev = 1.0
    for rank in range(m, 0, -1):
        idx = order[rank - 1]
        prev = min(prev, pvals[idx] * m / rank); adj[idx] = min(prev, 1.0)
    return rejected, adj
bh_p = [p[3] for p in per_num]
bh_reject, bh_adj = benjamini_hochberg(bh_p, 0.05)
n_significant_bh = len(bh_reject)
min_raw_p = min(bh_p)
min_adj_p = min(bh_adj)

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
p_bt = norm_sf2(z_bt)

# ───────────────────────── 5b. 기대수익(EV/ROI) 분석 ─────────────────────────
# 등수별 당첨확률 (보너스 고려)
TICKET = 1000  # 1게임 1,000원
P1 = 1 / C45_6
P2 = 6 / C45_6                                  # 5개+보너스
P3 = (math.comb(6, 5) * (39 - 1)) / C45_6       # 5개(보너스 제외)
P4 = (math.comb(6, 4) * math.comb(39, 2)) / C45_6
P5 = (math.comb(6, 3) * math.comb(39, 3)) / C45_6
# 역대 평균 당첨금(당첨자 1인 기준). 1~3등=변동(역대평균), 4·5등=고정
def avg_prize(amt_key, cnt_key):
    v = [r[amt_key] for r in raw if r.get(cnt_key, 0) > 0 and r.get(amt_key, 0) > 0]
    return statistics.mean(v)
PRZ = {
    1: avg_prize("1등 당첨금액", "1등 당첨자수"),
    2: avg_prize("2등 당첨금액", "2등 당첨자수"),
    3: avg_prize("3등 당첨금액", "3등 당첨자수"),
    4: 50000.0, 5: 5000.0,
}
ev_terms = {1: P1*PRZ[1], 2: P2*PRZ[2], 3: P3*PRZ[3], 4: P4*PRZ[4], 5: P5*PRZ[5]}
ev = sum(ev_terms.values())
roi = ev / TICKET - 1                            # 기대수익률
payout_ratio = ev / TICKET                       # 환급률
# 핵심: 이 EV는 책 기법/무작위 모두 동일(티켓별 등수확률이 같음)

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
                    "p": p_uniform, "p_exact": True, "expected_each": round(exp, 1)},
        "autocorr": {"mean_phi": round(mean_phi, 5), "z": round(z_phi, 3), "p": round(p_phi, 4),
                     "bh_significant": n_significant_bh, "n_tests": 45,
                     "min_raw_p": round(min_raw_p, 4), "min_adj_p": round(min_adj_p, 4),
                     "per_num": [{"n": n, "phi": round(ph, 4), "z": round(z, 3),
                                  "p": round(p, 4), "adj": round(bh_adj[i], 4)}
                                 for i, (n, ph, z, p) in enumerate(per_num)]},
        "gap": {"mean": round(mean_gap, 3), "theoretical": theo_gap, "cv": round(cv_gap, 3)},
    },
    "ev": {
        "ticket": TICKET, "ev": round(ev, 2), "roi": round(roi, 4),
        "payout_ratio": round(payout_ratio, 4),
        "probs": {"1": P1, "2": P2, "3": P3, "4": P4, "5": P5},
        "prizes": {str(k): round(v) for k, v in PRZ.items()},
        "terms": {str(k): round(v, 2) for k, v in ev_terms.items()},
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
print(f"   └ BH(FDR0.05) 45개 동시검정: 유의 번호 {n_significant_bh}개 "
      f"(최소 raw p={min_raw_p:.3f}, 보정 p={min_adj_p:.3f})")
print(f"■ [검정C] 미출간격 평균={mean_gap:.2f}(이론 {theo_gap}), CV={cv_gap:.2f}(기하분포≈1)")
print(f"■ [기대값] 1게임 EV={ev:,.0f}원 / {TICKET:,}원 → 환급률 {payout_ratio:.1%}, ROI {roi:+.1%} "
      f"(책 기법·무작위 동일)")
print(f"■ 필터 통과율: 실제당첨 {pass_rate_actual:.1%}, 전체조합 {pass_rate_all:.1%} "
      f"→ 후보풀 {filtered_pool:,} (전체의 {pass_rate_all:.1%})")
print(f"■ 백테스트({book_lc}게임씩): 기법 3등+이상 {book_prizes} vs 무작위 {rand_prizes} "
      f"(기대 {exp_prizes:.1f}), z={z_bt:.2f}, p={p_bt:.3f} "
      f"→ {'차이 유의' if p_bt<0.05 else '차이 없음(통계적 동일)'}")
print(f"■ 다음 주 {next_round}회 예상번호:")
for i, p in enumerate(pred_meta, 1):
    print(f"   {i}게임: {p['nums']}  합{p['sum']} {p['oddeven']} 끝수합{p['endsum']}")
print("\n결과 저장: analysis/results.json, data/draws.json")
