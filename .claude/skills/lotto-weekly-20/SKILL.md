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

2. **다가오는 회차 20게임 생성·잠금 + 카톡 메시지**
   ```bash
   python3 analysis/buy_set.py weekly
   ```
   - 다가오는 회차 20게임을 `compare_ledger.json` 에 잠그고(이미 있으면 보존),
     `<<<KAKAO>>>` 다음 줄부터 **카톡 알림 본문**(≤200자, 고정수+대시보드 링크)을 출력한다.

3. **카카오톡 발송**
   - `<<<KAKAO>>>` 이후 본문을 `KakaotalkChat-MemoChat` 의 `message` 로 **단 1건** 발송.

4. **커밋·푸시**
   ```bash
   git pull --rebase origin main
   git add analysis/compare_ledger.json data/draws.json && \
   git commit -m "chore: <회차>회 비교실험 20게임 잠금+채점" && git push
   ```

## 주의
- 200자 제한 때문에 20게임 전체는 카톡에 넣지 않고 **고정수 + 대시보드 링크**로 안내한다.
  (전체 20게임: https://heekeunlee.github.io/lottonumber001/compare.html)
- 실제 구매번호는 사용자가 알려줄 때 `buy_set.py user <회차> "..."` 로 별도 기록한다.
- 카톡은 절대 2건 이상 보내지 않는다.
