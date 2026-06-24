---
name: lotto-weekly-20
description: 다가오는 로또 회차의 '비교 실험용 20게임(2만원)'을 충실 기법으로 생성·잠그고, 카카오톡 나챗방에 알림 1건을 보낸다. 매주 월요일 자동 발송 루틴(5게임 건과 별도)에서 사용.
---

# lotto-weekly-20 — 주간 20게임 비교실험 카톡 알림

매주, 다가오는 회차의 **예측 20게임(2만원)**을 충실 기법(미출 기간표·고정수·통계필터)으로
생성·잠그고, 카톡 나챗방에 **알림 1건**(전체 번호는 대시보드 링크)을 보낸다.
5게임 주간예측(`lotto-weekly`)과는 **별도의 실험·별도의 톡**이다.

## 실행 절차

1. **지난 회차 채점(있으면)**
   - `analysis/compare_ledger.json` 에서 status가 `pending`인 최대 회차의 추첨일이 지났으면,
     PlayMCP `lotto645` 도구로 실제 당첨번호 6개+보너스를 받아온다.
   - `python3 analysis/buy_set.py score <회차> <n1..n6> <보너스>` (또는 draws.json에 있으면 `--auto`).

2. **다가오는 회차 20게임 생성·잠금 + 카톡 메시지(여러 블록)**
   ```bash
   python3 analysis/buy_set.py weekly
   ```
   - 다가오는 회차 20게임을 `compare_ledger.json` 에 잠그고(이미 있으면 보존),
     출력에 `<<<KAKAO>>>` 마커가 **여러 번** 나오며 **각 마커 다음이 한 통의 본문**(5게임씩, 각 ≤200자)이다.
     20게임이면 보통 **4통**(`[1/4]`~`[4/4]`, 마지막 통에 면책)이다.

3. **카카오톡 발송 (블록 수만큼)**
   - 각 `<<<KAKAO>>>` 블록을 `KakaotalkChat-MemoChat` 의 `message` 로 **순서대로 각각 1건씩** 발송한다(20게임=4건).
   - 블록을 빠뜨리거나 합치지 말고, 마커 단위 그대로 보낸다.

4. **커밋·푸시**
   ```bash
   git pull --rebase origin main
   git add analysis/compare_ledger.json data/draws.json && \
   git commit -m "chore: <회차>회 비교실험 20게임 잠금+채점" && git push
   ```

## 주의
- 20게임 전체를 **텍스트로** 5게임씩 끊어 보낸다(200자 제한 때문에 통을 나눔). 전체 대시보드:
  https://heekeunlee.github.io/lottonumber001/compare.html
- 실제 구매번호는 사용자가 알려줄 때 `buy_set.py user <회차> "..."` 로 별도 기록한다.
- 발송 건수는 `weekly` 출력의 `<<<KAKAO>>>` 블록 수와 **정확히 일치**해야 한다(초과·누락 금지).
