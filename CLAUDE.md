# CLAUDE.md — lottonumber001

이 파일은 Claude Code가 이 프로젝트로 돌아올 때 자동 로드되는 프로젝트 메모다.

## 프로젝트 목표 (가장 중요)
**로또 예측이 수학적으로 무의미함을 데이터·실거래로 증명하는 연구/논문 프로젝트.**
사용자(GitHub `heekeunlee`, 이희근)는 당첨이 목적이 아니라, 시중 분석서
『로또9단 1등 분석기법』(이승윤)의 기법을 **충실히 구현해도 무작위와 다르지 않음**을
통계·백테스트·실거래로 보이려 한다. 모든 산출물에는 "예측력 0, 확률 1/8,145,060 불변,
오락·교육용" 면책이 들어가야 한다. 존댓말로 응대한다.

## 배포
- GitHub Pages: https://heekeunlee.github.io/lottonumber001/
- 저장소: https://github.com/heekeunlee/lottonumber001 (기본 브랜치 main)
- 커밋·푸시는 사용자가 요청할 때 진행. 커밋 메시지 끝에 Co-Authored-By 라인.

## 페이지 (정적 HTML, 빌드 없음, 라이트/다크 토글, Chart.js CDN)
- `index.html` — 책 분석 대시보드
- `simulator.html` — 시뮬레이터 + 수학 검증 (`analysis/results.json` 동적 로드)
- `tracker.html` — 사전등록 예측 추적기 (`analysis/predictions_ledger.json`)
- `compare.html` — 2만원 실거래 비교 (`analysis/compare_ledger.json`)

## 분석 코드 (Python 표준 라이브러리만, scipy 없음)
- `analysis/method.py` — **공용 충실 기법 모듈**(미출 기간표 핫/콜드, 고정수=최근10회 최다출현,
  통계필터: 총합100~175·홀짝비극단·끝수합13~38·3연번배제·구간≥3·제외수, 핫수가중)
- `analysis/simulate.py` — 전체 분석·검정 생성 → `results.json`, `data/draws.json`
  · exact χ²(정칙 불완전감마), BH 다중비교 보정, EV/ROI, 백테스트
- `analysis/weekly_predict.py` — 주간 5게임 예측(회차 고정시드, 사전등록·격리) + 카톡 본문
- `analysis/buy_set.py` — 20게임 비교실험: `generate`/`weekly`/`user`/`score`(`--auto`,`--force`)
- `analysis/score_ledger.py` — 5게임 원장 채점
- 데이터: `data/draws.json`(정제), `data/raw_winner_all.json`(원본, 동행복권 1~최신회차)

## 핵심 수치 (현재까지)
- 데이터: 1~1229회 (1229회=2026-06-20 추첨). 다음 회차 1230=2026-06-27.
- 검정: 균일성 χ² p≈0.96 / 자기상관 BH 유의 0개 / 미출간격 CV≈0.94 / 백테스트 p≈0.41 / ROI≈-40%
- 1230회 5게임·20게임(고정수13) 모두 잠금 완료. 5게임은 카톡 발송됨(테스트 포함).

## 주간 자동화 (클라우드 루틴 2개, 매주 월요일, PlayMCP 커넥터)
- 09:07 KST — `lotto-weekly` 5게임: 채점→예측→카톡(번호 직접)→커밋
  · trig_01Twek1UpPijTrZFcPSARi4U
- 09:25 KST — `lotto-weekly-20` 20게임: 채점→예측→카톡(고정수+링크)→커밋
  · trig_0171URkzVPLW6TSAeiUG5xy9
- 루틴 관리: https://claude.ai/code/routines
- 스킬: `.claude/skills/lotto-weekly/`, `.claude/skills/lotto-weekly-20/`
- 카톡: PlayMCP `KakaotalkChat-MemoChat`(나챗방, **최대 200자**), 로또결과: PlayMCP `lotto645-*`

## 주의/관례
- 카톡은 한 번 실행당 1건만 발송(스팸 금지).
- 예상번호는 **회차 고정 시드**로 결정론적 → 같은 회차는 항상 동일(사전등록). 이미 잠긴 회차는 보존.
- "예측 vs 무작위는 동일"이 결론. 기법을 더 충실히 해도 결론 불변(추첨 독립성).
- 알려진 한계(논문 부록 B): 저자의 동적 수작업 100% 미복제, EV는 1인평균 사용으로 법정환급률 50%보다 상향, 검정력 분석·고차 마르코프 검정은 후속 과제.

## 자주 쓰는 명령
```bash
python3 analysis/simulate.py                 # 전체 분석 재생성
python3 analysis/weekly_predict.py           # 다음 회차 5게임 + 카톡본문
python3 analysis/buy_set.py weekly           # 다음 회차 20게임 + 카톡본문
python3 analysis/buy_set.py user <회차> "..." # 실제 구매번호 기록
python3 analysis/buy_set.py score <회차> --auto  # 추첨 후 채점
```
