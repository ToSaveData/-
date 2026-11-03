# 경제지표 대시보드 (자동 갱신)

한국·미국·글로벌 매크로·암호화폐 지표를 자동으로 수집해서 브라우저로 볼 수 있는 대시보드(`docs/index.html`)를 만들어 줍니다.
API 키가 필요 없습니다. (Yahoo Finance + FRED 공개 CSV 사용)

## 1. 설치 (처음 1번)

Python 3.9 이상이 필요합니다.

```bash
pip install -r requirements.txt
```

## 2. 실행

```bash
python dashboard.py          # 실제 데이터 수집 → docs/index.html 생성
python dashboard.py --demo   # 인터넷 없이 가상 데이터로 화면만 확인
```

실행이 끝나면 `docs/index.html`을 더블클릭해서 브라우저로 여세요.
엑셀로 보고 싶다면 `data/history.csv`(date, name, value)를 열면 됩니다.

일부 지표가 실패해도 나머지는 정상 생성되고, 화면 상단에 실패한 지표 이름이 표시됩니다.

## 3. 지표 추가/삭제

`config.py`의 `SECTIONS`에 한 줄만 추가하면 됩니다.

```python
{"name": "삼성전자", "source": "yf", "id": "005930.KS", "unit": "원", "freq": "D"},
```

- `source: "yf"` → Yahoo Finance 티커 (예: 코스피 종목은 `종목코드.KS`, 코스닥은 `.KQ`)
- `source: "fred"` → [FRED](https://fred.stlouisfed.org) 시리즈 ID
- 상승/하락 색상은 `UP_DOWN_COLOR`로 바꿉니다 (`"kr"` 빨강↑ 파랑↓ / `"us"` 초록↑ 빨강↓)

## 4. 자동화 (3가지 중 하나 선택)

### A. 내 PC에서 매일 실행

**Windows (작업 스케줄러)**: 작업 만들기 → 트리거 "매일 오전 7:30" → 동작 "프로그램 시작"
- 프로그램: `python`
- 인수: `dashboard.py`
- 시작 위치: 이 폴더 경로

**Mac/Linux (cron)**: `crontab -e` 후 아래 한 줄 추가 (평일 오전 7시 30분)

```
30 7 * * 1-5 cd /경로/econ-dashboard && /usr/bin/python3 dashboard.py
```

### B. GitHub Actions로 PC를 꺼도 자동 갱신 (추천)

1. 이 폴더를 GitHub 저장소에 올립니다.
2. 저장소 Settings → Pages → Source를 "Deploy from a branch", 브랜치 `main`, 폴더 `/docs`로 설정합니다.
3. `.github/workflows/update.yml`이 이미 들어 있으므로 매일 한국시간 오전 7시에 자동 실행되어 `docs/index.html`을 갱신합니다.
4. 대시보드 주소: `https://<내계정>.github.io/<저장소명>/` (휴대폰에서도 열람 가능)

저장소를 공개(public)로 두면 대시보드도 공개됩니다. 비공개로 쓰려면 방식 A를 사용하세요.

## 5. 알아둘 점

- 데이터 출처 특성상 값이 지연되거나 일시적으로 비어 있을 수 있습니다. (Yahoo Finance는 비공식 경로이며, 간헐적으로 실패할 수 있습니다.)
- 월간 지표(CPI, 실업률, 한국 장기금리)는 발표 시차가 있어 최신 값이 1~2개월 전 기준입니다. 카드의 "기준일"을 확인하세요.
- 한국 CPI·금리는 FRED(OECD 재가공)를 쓰므로 한국은행 ECOS·통계청 원자료보다 늦을 수 있습니다. 더 정확한 한국 지표가 필요하면 ECOS API(무료 키 발급)를 다음 단계로 붙이는 것을 추천합니다.
- 정보 제공용이며 투자 권유가 아닙니다.

## 6. 다음 단계 아이디어

1. **AI 시황 코멘트**: 수집한 최신 값을 Claude API에 보내 "오늘의 한 줄 요약"을 대시보드 상단에 자동 삽입
2. **알림**: VIX 30 초과, 장단기 금리차 역전 등 조건 충족 시 이메일/텔레그램 발송
3. **종목·ETF 분석 탭**: 관심 종목의 이동평균, 변동성, 수익률 비교 추가
4. **ECOS 연동**: 한국 기준금리, 소비자물가, 수출입 통계
