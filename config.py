"""
지표 설정 파일
- 새 지표를 추가하려면 아래 리스트에 한 줄만 추가하면 됩니다.
- source: "yf"   -> Yahoo Finance 티커 (주가, 환율, 원자재, 암호화폐)
          "fred" -> FRED 시리즈 ID (금리, 물가, 고용 등. API 키 불필요)
- unit:   화면에 표시할 단위
- freq:   "D"(일간) / "M"(월간)  -> 월간 지표는 변화율을 전월 대비로 표시
"""

HISTORY_YEARS = 5  # 차트에 보여줄 과거 기간(년)

# 상승/하락 색상: "kr" = 상승 빨강·하락 파랑(한국식), "us" = 상승 초록·하락 빨강(미국식)
UP_DOWN_COLOR = "kr"

SECTIONS = [
    {
        "title": "🇰🇷 한국",
        "items": [
            {"name": "KOSPI",        "source": "yf",   "id": "^KS11",             "unit": "pt",  "freq": "D"},
            {"name": "KOSDAQ",       "source": "yf",   "id": "^KQ11",             "unit": "pt",  "freq": "D"},
            {"name": "원/달러 환율",  "source": "yf",   "id": "KRW=X",             "unit": "원",  "freq": "D"},
            {"name": "한국 장기금리(10Y)", "source": "fred", "id": "IRLTLT01KRM156N", "unit": "%",  "freq": "M"},
            {"name": "한국 CPI(지수)", "source": "fred", "id": "KORCPIALLMINMEI",   "unit": "지수", "freq": "M"},
        ],
    },
    {
        "title": "🇺🇸 미국",
        "items": [
            {"name": "S&P 500",      "source": "yf",   "id": "^GSPC",   "unit": "pt", "freq": "D"},
            {"name": "나스닥",        "source": "yf",   "id": "^IXIC",   "unit": "pt", "freq": "D"},
            {"name": "VIX(공포지수)", "source": "yf",   "id": "^VIX",    "unit": "pt", "freq": "D"},
            {"name": "미국 10년 국채금리", "source": "fred", "id": "DGS10",   "unit": "%",  "freq": "D"},
            {"name": "미국 2년 국채금리",  "source": "fred", "id": "DGS2",    "unit": "%",  "freq": "D"},
            {"name": "연준 기준금리(EFFR)", "source": "fred", "id": "DFF",     "unit": "%",  "freq": "D"},
            {"name": "미국 CPI(지수)",    "source": "fred", "id": "CPIAUCSL", "unit": "지수", "freq": "M"},
            {"name": "미국 실업률",        "source": "fred", "id": "UNRATE",   "unit": "%",  "freq": "M"},
        ],
    },
    {
        "title": "🌍 글로벌 매크로",
        "items": [
            {"name": "달러인덱스(DXY)", "source": "yf", "id": "DX-Y.NYB", "unit": "pt", "freq": "D"},
            {"name": "WTI 원유",        "source": "yf", "id": "CL=F",     "unit": "$",  "freq": "D"},
            {"name": "금",              "source": "yf", "id": "GC=F",     "unit": "$",  "freq": "D"},
            {"name": "구리",            "source": "yf", "id": "HG=F",     "unit": "$",  "freq": "D"},
            {"name": "닛케이225",       "source": "yf", "id": "^N225",    "unit": "pt", "freq": "D"},
            {"name": "상하이종합",      "source": "yf", "id": "000001.SS", "unit": "pt", "freq": "D"},
        ],
    },
    {
        "title": "₿ 암호화폐",
        "items": [
            {"name": "비트코인", "source": "yf", "id": "BTC-USD", "unit": "$", "freq": "D"},
            {"name": "이더리움", "source": "yf", "id": "ETH-USD", "unit": "$", "freq": "D"},
        ],
    },
]

# 파생 지표: 두 시리즈의 차이 등. (a - b)
SPREADS = [
    {"name": "미국 장단기 금리차(10Y-2Y)", "a": "미국 10년 국채금리", "b": "미국 2년 국채금리", "unit": "%p"},
]
