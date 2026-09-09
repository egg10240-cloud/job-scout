# -*- coding: utf-8 -*-
"""
은지의 채용 레이더 — 매일 자동 스크랩 스크립트
원티드 공개 검색 API에서 공고를 수집해 docs/index.html 대시보드를 생성합니다.
GitHub Actions가 매일 아침 8시(KST)에 자동 실행합니다.
"""
import json
import re
import html
from datetime import datetime, timezone, timedelta
from urllib.request import Request, urlopen
from urllib.parse import quote

KST = timezone(timedelta(hours=9))
NOW = datetime.now(KST)

KEYWORDS = ["legal operations", "compliance", "법무"]
WANTED_API = (
    "https://www.wanted.co.kr/api/v4/jobs"
    "?country=kr&job_sort=job.latest_order&locations=all&years=-1&limit=20&query={q}"
)

QUICK_LINKS = [
    ("LinkedIn — Legal Operations 서울",
     "https://www.linkedin.com/jobs/search/?keywords=legal%20operations&location=Seoul"),
    ("LinkedIn — Compliance Program Manager 서울",
     "https://www.linkedin.com/jobs/search/?keywords=compliance%20program%20manager&location=Seoul"),
    ("잡코리아 — Legal PM", "https://www.jobkorea.co.kr/Search/?stext=legal%20pm"),
    ("원티드 — legal operations", "https://www.wanted.co.kr/search?query=legal%20operations"),
]

EXCLUDE = re.compile(r"변호사|attorney|counsel\b|인턴|intern", re.I)


def fetch(url):
    req = Request(url, headers={
        "User-Agent": ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                       "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"),
        "Accept": "application/json",
        "Referer": "https://www.wanted.co.kr/",
        "Accept-Language": "ko-KR,ko;q=0.9",
    })
    with urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def score(title):
    t = title.lower()
    if "legal operations" in t or "legal ops" in t:
        return "상"
    if "compliance" in t and re.search(r"manager|program|pm|매니저", t):
        return "상"
    if re.search(r"legal|법무", t) and re.search(r"pm|manager|매니저|operations|운영|기획", t):
        return "중"
    if "compliance" in t or "컴플라이언스" in t or "법무" in t:
        return "중"
    return "하"


def collect():
    jobs, seen = [], set()
    for kw in KEYWORDS:
        try:
            data = fetch(WANTED_API.format(q=quote(kw)))
        except Exception as e:
            print(f"[warn] '{kw}' 수집 실패: {e}")
            continue
        for item in data.get("data", []):
            jid = item.get("id")
            title = (item.get("position") or "").strip()
            company = ((item.get("company") or {}).get("name") or "").strip()
            if not jid or not title or jid in seen:
                continue
            if EXCLUDE.search(title):
                continue
            lv = score(title)
            if lv == "하":
                continue
            seen.add(jid)
            jobs.append({
                "title": title,
                "company": company,
                "url": f"https://www.wanted.co.kr/wd/{jid}",
                "match": lv,
                "keyword": kw,
            })
    order = {"상": 0, "중": 1}
    jobs.sort(key=lambda j: order.get(j["match"], 2))
    return jobs


def render(jobs):
    date_str = NOW.strftime("%Y년 %m월 %d일 %H:%M")
    cards = ""
    if jobs:
        for j in jobs:
            badge = "#C4392F" if j["match"] == "상" else "#1A2233"
            cards += f"""
      <article class="card">
        <div class="row">
          <span class="match" style="background:{badge}">매칭 {j['match']}</span>
          <span class="kw">'{html.escape(j['keyword'])}' 검색</span>
        </div>
        <h2>{html.escape(j['title'])}</h2>
        <div class="company">{html.escape(j['company'])}</div>
        <a class="open" href="{html.escape(j['url'])}" target="_blank" rel="noreferrer">공고 열기 (원티드)</a>
      </article>"""
    else:
        cards = '<p class="empty">오늘 수집된 공고가 없어요. 아래 바로가기에서 직접 확인해보세요.</p>'

    links = "".join(
        f'<a class="qlink" href="{u}" target="_blank" rel="noreferrer">{n}</a>'
        for n, u in QUICK_LINKS
    )

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>은지의 채용 레이더</title>
<style>
  * {{ box-sizing: border-box; margin: 0; }}
  body {{ background:#F5F4F0; color:#1A2233; max-width:560px; margin:0 auto;
         font-family:'Apple SD Gothic Neo','Malgun Gothic',sans-serif; }}
  header {{ background:#1A2233; color:#F5F4F0; padding:24px 20px 18px; position:relative; }}
  .kicker {{ font-size:12px; letter-spacing:.08em; color:#9AA3B2; margin-bottom:4px; }}
  h1 {{ font-size:24px; }}
  .seal {{ position:absolute; top:20px; right:18px; border:2px solid #C4392F; color:#C4392F;
          font-size:11px; line-height:1.25; padding:5px 6px; border-radius:3px; font-weight:700;
          transform:rotate(4deg); }}
  .meta {{ margin-top:14px; font-size:13px; color:#B8BFCB; }}
  main {{ padding:14px; }}
  .card {{ background:#fff; border:1px solid #E2E1DB; border-radius:6px; padding:14px; margin-bottom:12px; }}
  .row {{ display:flex; align-items:center; gap:8px; margin-bottom:8px; }}
  .match {{ color:#fff; font-size:12px; font-weight:700; padding:2px 8px; border-radius:3px; }}
  .kw {{ margin-left:auto; font-size:12px; color:#8A8F98; }}
  h2 {{ font-size:17px; line-height:1.35; margin-bottom:2px; }}
  .company {{ font-size:14px; color:#4A5160; margin-bottom:10px; }}
  .open {{ display:inline-block; background:#1A2233; color:#fff; text-decoration:none;
          font-size:13px; font-weight:600; padding:7px 12px; border-radius:4px; }}
  .empty {{ text-align:center; color:#8A8F98; padding:40px 20px; font-size:14px; line-height:1.6; }}
  .quick {{ background:#fff; border:1px solid #E2E1DB; border-radius:6px; padding:12px 14px; margin-top:4px; }}
  .quick h3 {{ font-size:14px; margin-bottom:10px; }}
  .qlink {{ display:block; padding:10px 12px; margin-bottom:8px; border:1px solid #C9CDD4;
           border-radius:4px; color:#1A2233; text-decoration:none; font-size:14px; }}
  footer {{ padding:12px 16px 24px; font-size:12px; color:#8A8F98; text-align:center; line-height:1.5; }}
</style>
</head>
<body>
  <header>
    <div class="kicker">매일의 스카우트</div>
    <h1>은지의 채용 레이더</h1>
    <div class="seal">採用<br>探索</div>
    <div class="meta">마지막 스크랩 · {date_str} (매일 아침 8시 자동 업데이트)</div>
  </header>
  <main>
    {cards}
    <div class="quick">
      <h3>직접 검색 바로가기</h3>
      {links}
    </div>
  </main>
  <footer>키워드: legal operations · compliance · 법무 — 매칭도는 제목 기반 자동 평가라 참고용이에요. 지원 전 공고 원문을 꼭 확인하세요.</footer>
</body>
</html>"""


if __name__ == "__main__":
    import os
    os.makedirs("docs", exist_ok=True)
    jobs = collect()
    print(f"수집된 공고: {len(jobs)}건")
    with open("docs/index.html", "w", encoding="utf-8") as f:
        f.write(render(jobs))
    print("docs/index.html 생성 완료")
