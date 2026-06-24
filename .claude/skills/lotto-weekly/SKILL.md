---
name: lotto-weekly
description: 다가오는 로또 회차의 5게임 예측 + 20게임 비교실험을 생성·잠그고, 카카오톡 나챗방에 2통(5게임 번호 / 20게임 요약·링크)을 보낸다. 매주 월요일 1회 실행 자동 루틴에서 사용.
---

# lotto-weekly — 주간 로또 예측 카톡 발송 (월 1회, 2통)

매주 월요일 1회 실행으로 다가오는 회차를 처리한다. 카톡은 **2통만** 보낸다:
① 5게임 예측(번호 직접), ② 20게임 비교실험 요약(고정수+대시보드 링크).
예측 당첨 확률은 무작위와 동일(1/8,145,060). 목적은 예측 무의미성의 **사전등록 시연**.

## 실행 절차

1. **지난 회차 채점 (내부 반영, 카톡 발송 안 함)**
   - 5게임: `analysis/predictions_ledger.json` 의 pending 최대 회차가 추첨됐으면
     실제 당첨번호로 `python3 analysis/score_ledger.py <회차> <n1..n6> <보너스>` (또는 `--auto`).
   - 20게임: `python3 analysis/buy_set.py score <회차> <n1..n6> <보너스>` (또는 `--auto`).
   - 채점 결과는 **카톡으로 보내지 않는다.** 대시보드(tracker/compare)에만 반영한다.

2. **5게임 예측 생성·잠금 + 발송**
   ```bash
   python3 analysis/weekly_predict.py
   ```
   - `<<<KAKAO>>>` 이후 본문(≤200자)을 `KakaotalkChat-MemoChat` 으로 **1통** 발송.

3. **20게임 비교실험 생성·잠금 + 요약 발송**
   ```bash
   python3 analysis/buy_set.py weekly
   ```
   - `<<<KAKAO>>>` 이후 본문(고정수+대시보드 링크, ≤200자)을 `KakaotalkChat-MemoChat` 으로 **1통** 발송.

4. **커밋·푸시**
   ```bash
   git pull --rebase origin main
   git add analysis/predictions_ledger.json analysis/compare_ledger.json data/draws.json
   git commit -m "chore: 주간 예측 잠금+채점" && git push
   ```

## 주의
- 카톡은 **정확히 2통**(5게임 1 + 20게임 요약 1). 그 이상 보내지 않는다.
- 채점은 내부 반영만. 결과 통보는 카톡으로 보내지 않는다(대시보드 확인).
- 예측은 회차 고정 시드로 결정론적이며 이미 잠긴 회차는 보존.
- 추첨일은 토요일이므로 월요일 발송은 그 주 토요일 회차 예측이다.
