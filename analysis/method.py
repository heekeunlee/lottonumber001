#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
method.py — 책 기법을 충실히 구현한 공용 생성 모듈
weekly_predict.py(5게임)와 buy_set.py(20게임)가 함께 사용한다.

반영 기법
  · 통계 필터: 총합 100~175, 홀짝 비극단, 끝수합 13~38, 3연번 배제, 구간 3개 이상, 제외수(직전 3중복)
  · 미출 기간표(핫/콜드): 각 번호의 미출 주수(gap)로 hot(≤5)/warm(6~10)/cold(≥11) 분류,
    한 게임의 콜드수 개수를 역대 분포(평균+2σ) 이하로 제한 + 핫수 1개 이상 포함
  · 고정수: 최근 10회 최다 출현 번호를 고정수로 선정해 모든 게임에 포함
  · 핫수 가중: 전체 출현 빈도로 가중 추출
"""
import statistics
from collections import Counter

# 카톡 본문에 표기할 적용 기법 키워드
METHOD_KEYWORDS = "📊기법 미출기간표·고정수·홀짝·총합·끝수합·연번·구간·제외수·핫수가중"

def total_sum(ns): return sum(ns)
def odd_even(ns): return sum(1 for n in ns if n % 2)
def end_sum(ns): return sum(n % 10 for n in ns)
def max_consec(ns):
    s = sorted(ns); best = run = 1
    for i in range(1, len(s)):
        run = run + 1 if s[i] == s[i-1]+1 else 1; best = max(best, run)
    return best
def band_spread(ns): return len(set((n-1)//10 for n in ns))

def passes_stat(ns, prev):
    if not (100 <= total_sum(ns) <= 175): return False
    if odd_even(ns) in (0, 6): return False
    if not (13 <= end_sum(ns) <= 38): return False
    if max_consec(ns) >= 3: return False
    if band_spread(ns) < 3: return False
    if prev and len(set(ns) & set(prev)) >= 3: return False
    return True

# ── 미출 기간표 ──
def gaps_now(history):
    """현재 시점 각 번호의 미출 주수(gap). 0=직전 회차 출현."""
    last = {}
    for i, d in enumerate(history):
        for n in d["nums"]:
            last[n] = i
    T = len(history) - 1
    return {n: (T - last[n]) if n in last else len(history) for n in range(1, 46)}

def hotcold_class(gaps):
    return {n: ("hot" if g <= 5 else "warm" if g <= 10 else "cold") for n, g in gaps.items()}

def cold_threshold(history):
    """역대 당첨 게임의 '콜드수(gap≥11) 개수' 분포에서 평균+2σ 임계값을 산출."""
    last = {}; counts = []
    for i, d in enumerate(history):
        cold = 0
        for n in d["nums"]:
            g = (i - last[n]) if n in last else i
            if g >= 11: cold += 1
        counts.append(cold)
        for n in d["nums"]:
            last[n] = i
    m = statistics.mean(counts); sd = statistics.pstdev(counts)
    return max(1, round(m + 2*sd)), round(m, 2), round(sd, 2)

def choose_fixed(history, k=1, window=10):
    """최근 window회 최다 출현 번호를 고정수로 선정(동점은 작은 수 우선, 결정론적)."""
    cnt = Counter()
    for d in history[-window:]:
        cnt.update(d["nums"])
    ranked = sorted(range(1, 46), key=lambda n: (-cnt.get(n, 0), n))
    return sorted(ranked[:k])

def passes_hotcold(ns, cls, cold_thr):
    cold = sum(1 for n in ns if cls[n] == "cold")
    hot = sum(1 for n in ns if cls[n] == "hot")
    return cold <= cold_thr and hot >= 1

class Method:
    """history로 1회 초기화 후, rng를 바꿔 가며 게임을 생성."""
    def __init__(self, history, fixed_k=1):
        self.history = history
        self.prev = history[-1]["nums"] if history else None
        self.gaps = gaps_now(history)
        self.cls = hotcold_class(self.gaps)
        self.cold_thr, self.cold_mean, self.cold_sd = cold_threshold(history)
        self.fixed = choose_fixed(history, k=fixed_k)
        cnt = Counter()
        for d in history: cnt.update(d["nums"])
        self.weights = {n: cnt.get(n, 0) + 1 for n in range(1, 46)}
        self.wmax = max(self.weights.values())

    def line(self, rng):
        need = 6 - len(self.fixed)
        pool = [n for n in range(1, 46) if n not in self.fixed]
        for _ in range(300000):
            pick = sorted(self.fixed + rng.sample(pool, need))
            w = sum(self.weights[n] for n in pick)
            if rng.random() > w / (6 * self.wmax): continue
            if passes_stat(pick, self.prev) and passes_hotcold(pick, self.cls, self.cold_thr):
                return pick
        return sorted(self.fixed + rng.sample(pool, need))  # 안전 fallback

    def distinct(self, rng, k):
        out = []
        guard = 0
        while len(out) < k and guard < k * 5000:
            guard += 1
            ln = self.line(rng)
            if ln not in out: out.append(ln)
        return out

    def meta(self):
        return {"fixed": self.fixed, "cold_thr": self.cold_thr,
                "cold_mean": self.cold_mean, "cold_sd": self.cold_sd,
                "hot": [n for n in range(1, 46) if self.cls[n] == "hot"],
                "cold": [n for n in range(1, 46) if self.cls[n] == "cold"]}
