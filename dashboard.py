"""
경제지표 대시보드 자동 생성기

사용법
  python dashboard.py          # 실제 데이터 수집 -> docs/index.html 생성
  python dashboard.py --demo   # 인터넷 없이 가상 데이터로 화면만 확인

결과물
  docs/index.html      브라우저로 열면 되는 대시보드
  data/history.csv     엑셀로 열어볼 수 있는 전체 시계열 (date, name, value)
"""
import argparse
import datetime as dt
import io
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import requests

import config

BASE = Path(__file__).parent
OUT_HTML = BASE / "docs" / "index.html"
OUT_CSV = BASE / "data" / "history.csv"
KST = dt.timezone(dt.timedelta(hours=9))


# ---------------------------------------------------------------- 데이터 수집
def fetch_yf(ticker: str, start: str) -> pd.Series:
    import yfinance as yf  # 데모 모드에서는 필요 없으므로 여기서 import

    df = yf.Ticker(ticker).history(start=start, auto_adjust=True)
    if df.empty:
        raise ValueError("데이터가 비어 있음")
    s = df["Close"].copy()
    s.index = pd.to_datetime(s.index).tz_localize(None).normalize()
    return s[~s.index.duplicated(keep="last")]


def fetch_fred(series_id: str, start: str) -> pd.Series:
    # FRED가 공개하는 CSV 주소 (API 키 불필요)
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}&cosd={start}"
    r = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text))
    dates = pd.to_datetime(df.iloc[:, 0])
    values = pd.to_numeric(df.iloc[:, 1], errors="coerce")  # 결측은 '.' 로 오므로 NaN 처리
    s = pd.Series(values.values, index=dates).dropna()
    if s.empty:
        raise ValueError("데이터가 비어 있음")
    return s


def fake_series(item: dict, start: str) -> pd.Series:
    """--demo 용 가상 데이터 (실제 값이 아닙니다)."""
    rng = np.random.default_rng(abs(hash(item["name"])) % (2**32))
    end = pd.Timestamp.today().normalize()
    idx = pd.date_range(start, end, freq="B" if item["freq"] == "D" else "MS")
    n = len(idx)
    if item["unit"] == "%":
        walk = 3.0 + np.cumsum(rng.normal(0, 0.05, n))
        return pd.Series(np.clip(walk, 0.1, None), index=idx)
    base = {"원": 1400, "$": 100, "지수": 110}.get(item["unit"], 3000)
    return pd.Series(base * np.exp(np.cumsum(rng.normal(0.0003, 0.012, n))), index=idx)


def collect(demo: bool):
    start = (pd.Timestamp.today() - pd.DateOffset(years=config.HISTORY_YEARS)).strftime("%Y-%m-%d")
    data, errors = {}, []
    for section in config.SECTIONS:
        for item in section["items"]:
            name = item["name"]
            try:
                if demo:
                    s = fake_series(item, start)
                elif item["source"] == "yf":
                    s = fetch_yf(item["id"], start)
                else:
                    s = fetch_fred(item["id"], start)
                data[name] = s.dropna().sort_index()
                print(f"  OK   {name}")
            except Exception as e:  # 하나가 실패해도 나머지는 계속 진행
                errors.append(f"{name} ({item['id']}): {e}")
                print(f"  FAIL {name}: {e}")
    return data, errors


# ---------------------------------------------------------------- 요약 계산
def fmt_value(v: float) -> str:
    a = abs(v)
    if a >= 10000:
        return f"{v:,.0f}"
    if a >= 1000:
        return f"{v:,.1f}"
    return f"{v:,.2f}"


def summarize(s: pd.Series, item: dict) -> dict:
    last, prev = float(s.iloc[-1]), float(s.iloc[-2]) if len(s) > 1 else float(s.iloc[-1])
    if item["unit"] in ("%", "%p"):
        chg = last - prev
        chg_txt = f"{chg:+.2f}%p"
    else:
        chg = (last / prev - 1) * 100 if prev else 0.0
        chg_txt = f"{chg:+.2f}%"
    extra = ""
    if item["freq"] == "M" and item["unit"] == "지수" and len(s) > 12:
        yoy = (last / float(s.iloc[-13]) - 1) * 100
        extra = f"전년 대비 {yoy:+.1f}%"
    return {
        "value": fmt_value(last),
        "unit": item["unit"],
        "chg_txt": chg_txt,
        "chg_sign": 1 if chg > 0 else (-1 if chg < 0 else 0),
        "chg_label": "전월 대비" if item["freq"] == "M" else "전일 대비",
        "extra": extra,
        "asof": s.index[-1].strftime("%Y-%m-%d"),
    }


def build_cards(data: dict):
    cards_by_section = []
    for section in config.SECTIONS:
        cards = []
        for item in section["items"]:
            s = data.get(item["name"])
            if s is None or s.empty:
                continue
            cards.append((item, s))
        # 파생 지표(스프레드)는 기준이 되는 지표가 있는 섹션에 붙인다
        for sp in getattr(config, "SPREADS", []):
            names_here = [i["name"] for i, _ in cards]
            if sp["a"] in names_here and sp["a"] in data and sp["b"] in data:
                diff = (data[sp["a"]] - data[sp["b"]]).dropna()
                if not diff.empty:
                    data[sp["name"]] = diff
                    cards.append(({"name": sp["name"], "unit": sp["unit"], "freq": "D", "id": "calc"}, diff))
        cards_by_section.append((section["title"], cards))
    return cards_by_section


# ---------------------------------------------------------------- HTML 생성
def build_html(cards_by_section, errors) -> str:
    payload, sections = {}, []
    for si, (title, cards) in enumerate(cards_by_section):
        out = []
        for ci, (item, s) in enumerate(cards):
            cid = f"c{si}_{ci}"
            payload[cid] = {
                "name": item["name"],
                "unit": item["unit"],
                "x": [d.strftime("%Y-%m-%d") for d in s.index],
                "y": [round(float(v), 4) for v in s.values],
            }
            out.append({"id": cid, "name": item["name"], **summarize(s, item)})
        sections.append({"title": title, "cards": out})

    up, down = ("#e5484d", "#3b82f6") if config.UP_DOWN_COLOR == "kr" else ("#16a34a", "#dc2626")
    now = dt.datetime.now(KST).strftime("%Y-%m-%d %H:%M KST")
    html = TEMPLATE
    html = html.replace("__UP__", up).replace("__DOWN__", down)
    html = html.replace("__UPDATED__", now)
    html = html.replace("__SECTIONS__", json.dumps(sections, ensure_ascii=False))
    html = html.replace("__SERIES__", json.dumps(payload, ensure_ascii=False))
    html = html.replace("__ERRORS__", json.dumps(errors, ensure_ascii=False))
    return html


TEMPLATE = r"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>경제지표 대시보드</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
:root{--bg:#f6f7f9;--card:#fff;--text:#1a1d21;--muted:#6b7280;--line:#e5e7eb;--accent:#4f7cff;--up:__UP__;--down:__DOWN__}
@media (prefers-color-scheme:dark){:root{--bg:#0f1115;--card:#181b21;--text:#e8eaed;--muted:#9aa0a6;--line:#2a2e36;--accent:#7aa2ff}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font-family:-apple-system,"Segoe UI","Noto Sans KR","Malgun Gothic",sans-serif}
.wrap{max-width:1280px;margin:0 auto;padding:20px 16px 48px}
header{display:flex;flex-wrap:wrap;gap:12px;align-items:end;justify-content:space-between;margin-bottom:8px}
h1{font-size:22px;margin:0}
.sub{color:var(--muted);font-size:13px;margin-top:4px}
.ranges button{border:1px solid var(--line);background:var(--card);color:var(--text);padding:6px 12px;border-radius:8px;cursor:pointer;font-size:13px;margin-left:6px}
.ranges button.on{background:var(--accent);border-color:var(--accent);color:#fff}
h2{font-size:16px;margin:28px 0 10px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(290px,1fr));gap:12px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 14px 6px}
.name{font-size:13px;color:var(--muted)}
.val{font-size:26px;font-weight:650;margin:4px 0 2px}
.val small{font-size:13px;color:var(--muted);font-weight:400;margin-left:4px}
.chg{font-size:13px;font-weight:600}
.chg.up{color:var(--up)}.chg.down{color:var(--down)}.chg.flat{color:var(--muted)}
.meta{font-size:11px;color:var(--muted);margin-top:2px}
.plot{height:130px;margin:6px -6px 0}
.warn{background:#fff7e6;color:#7a4b00;border:1px solid #ffd591;border-radius:10px;padding:10px 14px;font-size:13px;margin:12px 0}
@media (prefers-color-scheme:dark){.warn{background:#2b2210;color:#f3d79a;border-color:#5b4515}}
footer{color:var(--muted);font-size:12px;margin-top:32px}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div>
      <h1>경제지표 대시보드</h1>
      <div class="sub">마지막 갱신 __UPDATED__ · 출처: Yahoo Finance, FRED</div>
    </div>
    <div class="ranges" id="ranges"></div>
  </header>
  <div id="warn"></div>
  <div id="root"></div>
  <footer>정보 제공용 자료이며 투자 권유가 아닙니다. 데이터는 지연되거나 부정확할 수 있습니다.</footer>
</div>
<script>
const SECTIONS = __SECTIONS__;
const SERIES = __SERIES__;
const ERRORS = __ERRORS__;
const RANGES = [["3개월",92],["1년",365],["3년",1095],["5년",1826]];
let current = 365;

const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();

function build(){
  const root = document.getElementById("root");
  root.innerHTML = "";
  SECTIONS.forEach(sec=>{
    const h = document.createElement("h2"); h.textContent = sec.title; root.appendChild(h);
    const g = document.createElement("div"); g.className = "grid"; root.appendChild(g);
    sec.cards.forEach(c=>{
      const cls = c.chg_sign>0?"up":(c.chg_sign<0?"down":"flat");
      const d = document.createElement("div"); d.className = "card";
      d.innerHTML = `<div class="name">${c.name}</div>
        <div class="val">${c.value}<small>${c.unit}</small></div>
        <div class="chg ${cls}">${c.chg_sign>0?"▲":(c.chg_sign<0?"▼":"–")} ${c.chg_txt} <span style="font-weight:400;color:var(--muted)">${c.chg_label}</span></div>
        <div class="meta">${c.extra?c.extra+" · ":""}기준일 ${c.asof}</div>
        <div class="plot" id="${c.id}"></div>`;
      g.appendChild(d);
    });
  });
  if (ERRORS.length){
    document.getElementById("warn").innerHTML =
      `<div class="warn">일부 지표를 불러오지 못했습니다: ${ERRORS.map(e=>e.split(":")[0]).join(", ")}</div>`;
  }
}

function draw(){
  const lastIso = d => d[d.length-1];
  Object.entries(SERIES).forEach(([id,s])=>{
    const end = new Date(lastIso(s.x));
    const from = new Date(end.getTime() - current*86400000);
    let x=[],y=[];
    for(let i=0;i<s.x.length;i++){ if(new Date(s.x[i])>=from){x.push(s.x[i]);y.push(s.y[i]);} }
    if(x.length<2){ x=s.x; y=s.y; }
    Plotly.react(id,[{x,y,type:"scatter",mode:"lines",line:{color:css("--accent"),width:1.8},
      hovertemplate:"%{x}<br>%{y:,.2f}<extra></extra>"}],
      {margin:{l:40,r:8,t:4,b:20},paper_bgcolor:"rgba(0,0,0,0)",plot_bgcolor:"rgba(0,0,0,0)",
       font:{color:css("--muted"),size:10},showlegend:false,
       xaxis:{showgrid:false,type:"date"},yaxis:{gridcolor:css("--line"),zeroline:false}},
      {displayModeBar:false,responsive:true});
  });
}

function buttons(){
  const box = document.getElementById("ranges"); box.innerHTML="";
  RANGES.forEach(([label,days])=>{
    const b=document.createElement("button"); b.textContent=label;
    if(days===current) b.className="on";
    b.onclick=()=>{current=days;buttons();draw();};
    box.appendChild(b);
  });
}

build(); buttons(); draw();
window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change",draw);
</script>
</body>
</html>
"""


# ---------------------------------------------------------------- 실행
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true", help="가상 데이터로 화면만 확인")
    args = ap.parse_args()

    print("데이터 수집 중..." + (" (데모 모드)" if args.demo else ""))
    data, errors = collect(args.demo)
    if not data:
        print("모든 지표 수집에 실패했습니다. 인터넷 연결을 확인하세요.")
        sys.exit(1)

    cards = build_cards(data)

    OUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    OUT_HTML.write_text(build_html(cards, errors), encoding="utf-8")

    long = pd.concat([s.rename("value").to_frame().assign(name=n) for n, s in data.items()])
    long.index.name = "date"
    long.reset_index()[["date", "name", "value"]].to_csv(OUT_CSV, index=False, encoding="utf-8-sig")

    print(f"\n완료: {OUT_HTML}")
    if errors:
        print(f"실패한 지표 {len(errors)}개:")
        for e in errors:
            print("  -", e)


if __name__ == "__main__":
    main()
