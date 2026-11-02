# Urban AI · tempurban2026

**VOC 기반 도시개발 전주기 AI 시뮬레이션** 기획연구의 화면 뼈대(시연판).
가상 데이터와 '에이전트인 척' 하는 구조로 먼저 돌려 보며, 실제 연구에서 필요한 화면·데이터·모형 요구를 구체화한다.
디자인 시스템은 [water-tech-agent2](https://github.com/newcave/water-tech-agent2)를 따른다 (고정 상단바 · 카드 그리드 · 지표 타일 · 다크 Plotly).

> ⚠️ **모든 수치는 가상 데이터**입니다. 실제 사업 계획·민원 통계·내부 문서 내용이 아닙니다. 모형 계수와 대안 비용도 예시값입니다.

## 화면

| 화면 | 내용 |
|---|---|
| 개요 | 과제 한 장 요약 · PoC 생활권 현황 지표 · 5단 처리 흐름 · 대상지 4곳 · 핵심 질문 → 화면 |
| 사업지 · 공정 | 생애주기 단계 · 블록 공정표와 개교·교통·공원 공급 시점 · 입주 대비 공급 · 공급-수요 갭 · 단계별 프로파일 비교 |
| VOC 분석 | 가상 VOC 3,600여 건 · 유형/블록/채널 · **VOC 분류 에이전트 체험**(유형·심각도·관련 시설·담당·안내문 초안) · 분류 품질 · HITL 대기열 |
| 주민 Agent · ABM | 주민 유형 6종 · 가구 Agent 민원 발생과 블록 내 확산 · 유형별 목소리(LLM 자리) · 집계모형과 교차 확인 |
| What-if | 표준 시나리오 5건 상대비교 · 레버 직접 조절 · ±20% 민감도 · 54개 조합 다목적(VOC·비용·공정) 파레토 · 레버 주체(K-water/협의/외부) |
| 에이전트 관제 | 에이전트 9개 구성 · **에이전트에게 묻기**(오케스트레이터 트레이스) · 자동 실행 기록 |
| 온톨로지 | 전주기 클래스 16·관계 23 · 인과 경로 · ISO/IEC 5087-1 대응 후보 · 데이터 인벤토리(예시) |

## 에이전트 구조 (시연판)

```
오케스트레이터 ── 질문 해석 → 작업 계획 → 호출 → 종합
 ├ 데이터   : VOC 수집·정제 · VOC 분류 · 온톨로지 관리
 ├ 예측     : 생활영향 예측 · 주민 페르소나 · Agent-ABM
 └ 의사결정 : What-if·최적화 · 보고서 작성
```
LLM 없이 규칙·시뮬레이션으로 동작한다. 실제 LLM은 `urb/llm.py` 한 곳(`classify_voc`, `persona_voice`)만 채우면 붙는다.

## 폴더

```
app.py                 진입점 (상단 내비 · 7개 화면)
app_pages/             화면별 스크립트
urb/catalog.py         사업지·생활권·블록·공급 계획·VOC 유형·주민 유형·레버·시나리오 (가상값)
urb/sim.py             입주 곡선 → 공급-수요 갭 → 생활불편지수 → VOC 기대건수, What-if·민감도·다목적, Agent-ABM
urb/voc.py             VOC 문장 템플릿 + 규칙 기반 분류기
urb/agents.py          에이전트 정의 · 오케스트레이터 · 실행 기록
urb/ontology.py        온톨로지 v0 · 인과 경로 · ISO/IEC 5087-1 대응 후보
urb/ui.py              화면 부품 (water-tech-agent2 디자인)
scripts/make_synthetic.py   가상 데이터 다시 만들기
data/                  voc.csv · monthly.csv · meta.json (가상)
```

## 실행 · 배포

```bash
pip install -r requirements.txt
streamlit run app.py
python scripts/make_synthetic.py --seed 2026   # 가상 데이터 재생성 (선택)
```
Streamlit Community Cloud: share.streamlit.io → Create app → `newcave/tempurban2026`, branch `main`, file `app.py`.
