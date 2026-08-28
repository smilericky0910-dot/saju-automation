# -*- coding: utf-8 -*-
"""
3단계: report_pipeline.py가 만든 리포트 텍스트(마크다운) + AdvancedSajuAnalyzer.compute_all() JSON을
받아서, saju_report_sample.html에서 확정한 디자인 그대로의 완성된 PDF로 렌더링하는 모듈.

핵심 원칙(지침 1-2와 동일한 이유):
- 사주 스냅샷의 원국 4기둥·오행 분포·대운·용신 같은 "숫자/사실" 데이터는 절대 AI가 쓴 텍스트에서
  가져오지 않고, 매번 saju_data(JSON)에서 직접 읽어서 코드가 그린다. AI가 리포트 본문에서 같은
  숫자를 조금 다르게 표현했더라도 스냅샷 화면에는 절대 반영되지 않는다.
- 각 장의 "글"(성향 해설, 전략, 총평 등)만 AI가 쓴 마크다운을 파싱해서 채워 넣는다.
"""
import datetime
import re

import markdown as md_lib
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

STEM_ELEM = {'甲': '木', '乙': '木', '丙': '火', '丁': '火', '戊': '土',
             '己': '土', '庚': '金', '辛': '金', '壬': '水', '癸': '水'}
ELEM_HANGUL = {'木': '목', '火': '화', '土': '토', '金': '금', '水': '수'}
ELEM_VAR = {'木': 'wood', '火': 'fire', '土': 'earth', '金': 'metal', '水': 'water'}

CSS = """
:root {
  --paper: #f4f2ea;
  --paper-band: #ece8dc;
  --ink: #24221c;
  --ink-soft: #6b6656;
  --ink-faint: #9c9683;
  --accent: #2c5c58;
  --accent-strong: #1e4441;
  --accent-soft: #dde7e3;
  --rule: #d9d3c1;

  --wood: #4c7a52;
  --fire: #ad4a3a;
  --earth: #ad8a3f;
  --metal: #8a8579;
  --water: #2c5c58;

  --font-display: "Gowun Batang", "Noto Serif KR", serif;
  --font-body: "Noto Sans KR", -apple-system, "Malgun Gothic", sans-serif;
}

@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --paper: #1b1913; --paper-band: #232019; --ink: #ece7d9; --ink-soft: #a8a08b;
    --ink-faint: #736c58; --accent: #6fada4; --accent-strong: #8fc4bb;
    --accent-soft: #253431; --rule: #38342a;
    --wood: #7fae83; --fire: #d1786a; --earth: #cdaa63; --metal: #a9a496; --water: #6fada4;
  }
}
:root[data-theme="dark"] {
  --paper: #1b1913; --paper-band: #232019; --ink: #ece7d9; --ink-soft: #a8a08b;
  --ink-faint: #736c58; --accent: #6fada4; --accent-strong: #8fc4bb;
  --accent-soft: #253431; --rule: #38342a;
  --wood: #7fae83; --fire: #d1786a; --earth: #cdaa63; --metal: #a9a496; --water: #6fada4;
}

* { box-sizing: border-box; }
html { font-size: 18px; }
body {
  background: var(--paper); color: var(--ink); font-family: var(--font-body);
  font-size: 1rem; line-height: 1.75; -webkit-font-smoothing: antialiased; text-wrap: pretty;
  margin: 0;
}
.page { max-width: 660px; margin: 0 auto; padding: 3.5rem 1.5rem 5rem; }

.eyebrow { font-size: 0.75rem; font-weight: 600; letter-spacing: 0.16em; color: var(--accent); text-transform: uppercase; }
h1.title { font-family: var(--font-display); font-weight: 700; font-size: 2.05rem; line-height: 1.4; margin: 0.6rem 0 0.9rem; text-wrap: balance; color: var(--ink); }
.subtitle { font-size: 0.98rem; color: var(--ink-soft); margin-bottom: 1.4rem; }
.meta { display: flex; flex-wrap: wrap; gap: 0.4rem 1rem; font-size: 0.82rem; color: var(--ink-faint); font-variant-numeric: tabular-nums; }
.meta b { color: var(--ink-soft); font-weight: 600; }
hr.rule { border: none; border-top: 1px solid var(--rule); margin: 2.6rem 0; }

.toc { display: grid; grid-template-columns: 1fr 1fr; gap: 0.55rem 1.5rem; font-size: 0.88rem; color: var(--ink-soft); }
.toc span.n { font-variant-numeric: tabular-nums; color: var(--accent); font-weight: 600; margin-right: 0.5em; }
.toc .closing { grid-column: 1 / -1; color: var(--ink-faint); }
@media (max-width: 480px) { .toc { grid-template-columns: 1fr; } }

.snapshot { background: var(--paper-band); border-radius: 4px; padding: 1.9rem 1.7rem 2.1rem; margin: 0 -1.5rem; }
@media (min-width: 560px) { .snapshot { margin: 0; padding: 2.1rem 2.2rem 2.3rem; } }
.snapshot h2 { font-family: var(--font-display); font-size: 1.15rem; font-weight: 700; margin: 0 0 1.2rem; }
.pillars { display: flex; gap: 0.6rem; flex-wrap: wrap; margin-bottom: 1.6rem; }
.pillar { flex: 1 1 120px; background: var(--paper); border: 1px solid var(--rule); border-radius: 3px; padding: 0.55rem 0.7rem; text-align: center; }
.pillar .label { font-size: 0.7rem; color: var(--ink-faint); letter-spacing: 0.04em; }
.pillar .ganji { font-family: var(--font-display); font-size: 1.1rem; font-weight: 700; margin-top: 0.15rem; }
.chart-caption { font-size: 0.8rem; color: var(--ink-faint); margin: 0.2rem 0 1.6rem; }

.oheng { display: grid; gap: 0.6rem; margin-bottom: 0.3rem; }
.oheng-row { display: grid; grid-template-columns: 44px 1fr auto; align-items: center; gap: 0.7rem; }
.oheng-label { font-size: 0.82rem; color: var(--ink-soft); white-space: nowrap; }
.oheng-track { position: relative; height: 12px; border-radius: 6px; background: var(--rule); }
.oheng-track.empty { background: transparent; border: 1.5px dashed var(--water); opacity: 0.55; }
.oheng-fill { position: absolute; inset: 0; width: 0; border-radius: 6px; }
.oheng-value { font-size: 0.85rem; font-weight: 700; font-variant-numeric: tabular-nums; white-space: nowrap; color: var(--ink); }
.oheng-value.faint { color: var(--ink-faint); font-weight: 500; }

.snap-facts { display: grid; gap: 0.5rem; font-size: 0.9rem; color: var(--ink-soft); border-top: 1px solid var(--rule); padding-top: 1.1rem; margin-top: 1.8rem; }
.snap-facts b { color: var(--ink); font-weight: 600; }

.chapter { margin-top: 3.1rem; }
.chapter-head { display: flex; align-items: baseline; gap: 0.75rem; margin-bottom: 1.1rem; }
.chapter-num { font-variant-numeric: tabular-nums; font-size: 0.85rem; font-weight: 600; color: var(--accent); letter-spacing: 0.02em; }
h2.chapter-title { font-family: var(--font-display); font-weight: 700; font-size: 1.4rem; line-height: 1.4; margin: 0; text-wrap: balance; }
h3.sub { font-size: 0.98rem; font-weight: 700; color: var(--accent-strong); margin: 1.5rem 0 0.55rem; }
p { margin: 0 0 1rem; }
.chapter p:last-child { margin-bottom: 0; }
strong { font-weight: 700; background: linear-gradient(to bottom, transparent 62%, var(--accent-soft) 62%); padding: 0 0.05em; }
ul.actions { list-style: none; margin: 0.9rem 0 1.1rem; padding: 0; display: grid; gap: 0.55rem; }
ul.actions li { padding-left: 1.1rem; position: relative; font-size: 0.96rem; color: var(--ink); }
ul.actions li::before { content: "—"; position: absolute; left: 0; color: var(--accent); }

.verdict { margin-top: 3.4rem; padding-top: 2.2rem; border-top: 2px solid var(--ink); }
.verdict h2 { font-family: var(--font-display); font-size: 1.55rem; margin: 0 0 1.3rem; }
.verdict .thesis { font-family: var(--font-display); font-size: 1.2rem; line-height: 1.65; color: var(--accent-strong); margin-bottom: 2rem; text-wrap: balance; }
.dodont { display: grid; gap: 1.6rem; }
@media (min-width: 560px) { .dodont { grid-template-columns: 1fr 1fr; } }
.dodont h3 { font-size: 0.78rem; letter-spacing: 0.1em; text-transform: uppercase; font-weight: 700; margin: 0 0 0.7rem; }
.dont h3 { color: var(--fire); }
.do h3 { color: var(--accent); }
.dodont ul { list-style: none; margin: 0; padding: 0; display: grid; gap: 0.6rem; font-size: 0.92rem; }
.dodont li { padding-left: 1.1rem; position: relative; }
.dont li::before { content: "×"; position: absolute; left: 0; color: var(--fire); font-weight: 700; }
.do li::before { content: "✓"; position: absolute; left: 0; color: var(--accent); font-weight: 700; }

.closing { margin: 4rem -1.5rem 0; background: var(--accent-strong); color: #f2efe4; padding: 3rem 1.8rem 3.4rem; text-align: center; }
@media (min-width: 560px) { .closing { margin: 4rem 0 0; border-radius: 4px; } }
.closing .eyebrow2 { font-size: 0.72rem; letter-spacing: 0.18em; text-transform: uppercase; color: #b9d4cd; margin-bottom: 1rem; }
.closing p { font-size: 1rem; line-height: 1.85; color: #ece7d9; max-width: 46ch; margin: 0 auto 1rem; }
.closing .sign { font-family: var(--font-display); font-size: 1.1rem; font-weight: 700; margin-top: 1.4rem; color: #fff; }

@media print {
  @page { size: A4; margin: 16mm 14mm 20mm; }
  * { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  body { background: #fff; }
  .page { max-width: none; padding: 0; }
  .snapshot, .chapter, .verdict, .closing { break-before: page; break-inside: avoid-page; }
  .chapter-head, .verdict h2, .closing .eyebrow2 { break-after: avoid-page; }
  h3.sub { break-after: avoid-page; }
  /* the TOC gets its own full page. Chromium's print engine does not reliably
     honor break-inside:avoid-page on a CSS grid (a row can still fragment
     onto the next page on its own), so print falls back to a plain stacked
     list, which fragments predictably. */
  .toc { break-before: page; display: block; font-size: 0.82rem; }
  .toc > div { margin-bottom: 0.4rem; }
  .toc .closing { margin-top: 0.5rem; }
}
"""

DOC_SKELETON = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>{title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Gowun+Batang:wght@400;700&family=Noto+Sans+KR:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>{css}</style>
</head>
<body>
<div class="page">
{body}
</div>
</body>
</html>
"""


def _md_to_html_fragment(text: str) -> str:
    """마크다운 조각을 HTML로 변환한 뒤, 우리 디자인 규칙 두 가지를 적용한다:
    1) '**소제목만 있는 한 줄**' 문단 -> <h3 class="sub"> 소제목
    2) 모든 <ul> -> class="actions" (지침 2장의 '실행형 내용은 불릿'과 대응)
    """
    html = md_lib.markdown(text.strip(), extensions=["extra", "sane_lists"])
    soup = BeautifulSoup(html, "html.parser")

    for p in soup.find_all("p"):
        contents = [c for c in p.contents if not (isinstance(c, str) and not c.strip())]
        if len(contents) == 1 and getattr(contents[0], "name", None) == "strong":
            h3 = soup.new_tag("h3")
            h3["class"] = "sub"
            h3.string = contents[0].get_text()
            p.replace_with(h3)

    for ul in soup.find_all("ul"):
        classes = ul.get("class") or []
        if "actions" not in classes:
            ul["class"] = classes + ["actions"]

    return str(soup)


def _split_top_sections(markdown_text: str):
    """'## ' 로 시작하는 줄 기준으로 전체 리포트를 (제목, 본문) 리스트로 쪼갠다."""
    parts = re.split(r'(?m)^##\s+', markdown_text)
    sections = []
    for chunk in parts[1:]:  # parts[0]은 첫 '##' 이전(있다면 표지 h1 등 불필요한 부분)이라 버림
        lines = chunk.split("\n", 1)
        heading = lines[0].strip()
        body = lines[1] if len(lines) > 1 else ""
        sections.append((heading, body.strip()))
    return sections


def _parse_verdict(body: str):
    """'## [최종 총평]' 섹션 본문에서 한 줄 메시지 / DON'T / DO를 뽑아낸다.
    예상 패턴을 못 찾으면 None들을 반환하고, 호출부가 일반 문단으로 대체 렌더링한다."""
    thesis_m = re.search(r"\*\*인생\s*한\s*줄\s*관통\s*메시지\*\*\s*[:：]\s*(.+)", body)
    thesis = thesis_m.group(1).strip() if thesis_m else None

    do_split = re.split(r"\*\*\s*3대\s*do\s*\*\*", body, maxsplit=1, flags=re.IGNORECASE)
    if len(do_split) != 2:
        return thesis, [], []

    dont_block, do_block = do_split
    dont_block = re.split(r"\*\*\s*3대\s*don'?t\s*\*\*", dont_block, flags=re.IGNORECASE)[-1]

    item_re = re.compile(r"(?m)^(?:[-•]|\d+[.)])\s+(.+)$")
    dont_items = [m.strip() for m in item_re.findall(dont_block)]
    do_items = [m.strip() for m in item_re.findall(do_block)]
    return thesis, dont_items, do_items


def _oheng_rows_html(adj_scores: dict) -> str:
    total = sum(adj_scores.values()) or 1
    pcts = {e: v / total * 100 for e, v in adj_scores.items()}
    scale_max = max(30.0, max(pcts.values())) * 1.05
    order = sorted(pcts.items(), key=lambda kv: -kv[1])

    rows = []
    for elem, pct in order:
        hangul = ELEM_HANGUL[elem]
        var = ELEM_VAR[elem]
        if pct < 0.05:
            rows.append(f'''
      <div class="oheng-row">
        <span class="oheng-label">{elem} {hangul}</span>
        <span class="oheng-track empty"></span>
        <span class="oheng-value faint">0.0%</span>
      </div>''')
        else:
            width = min(100.0, pct / scale_max * 100)
            rows.append(f'''
      <div class="oheng-row">
        <span class="oheng-label">{elem} {hangul}</span>
        <span class="oheng-track"><span class="oheng-fill" style="width:{width:.0f}%; background:var(--{var});"></span></span>
        <span class="oheng-value">{pct:.1f}%</span>
      </div>''')
    return "".join(rows)


def _yongshin_line(d: dict) -> str:
    parts = [f"억부용신 {d['eokbu_elem']}({ELEM_HANGUL[d['eokbu_elem']]})"]
    johu = d.get("johu_info") or {}
    if johu.get("needed"):
        urgent = ", 시급" if johu.get("urgent") else ""
        parts.append(f"조후용신 {johu['element']}({ELEM_HANGUL[johu['element']]}{urgent})")
    tonggwan = d.get("tonggwan_info") or {}
    if tonggwan.get("needed"):
        parts.append(f"통관용신 {tonggwan['element']}({ELEM_HANGUL[tonggwan['element']]})")
    return " · ".join(parts)


def _daewoon_line(d: dict) -> str:
    num = d["daewoon"]["num"]
    saeyun = d.get("saeyun")
    if saeyun and not saeyun.get("before_first_daewoon") and saeyun.get("current_daewoon"):
        age, stem, branch = saeyun["current_daewoon"]
        return f"대운수 {num} · 현재 대운 {stem}{branch}({age}~{age + 9}세, 세는나이 {saeyun['current_age']}세)"
    return f"대운수 {num}"


def _snapshot_html(d: dict) -> str:
    pillars_raw = d["pillars_raw"]
    labels = [("년주", pillars_raw["year"]), ("월주", pillars_raw["month"]),
              ("일주", pillars_raw["day"]), ("시주", pillars_raw["hour"])]
    pillar_cards = []
    for label, pillar in labels:
        if pillar is None:
            pillar_cards.append(f'<div class="pillar"><div class="label">{label}</div><div class="ganji">미상</div></div>')
        else:
            pillar_cards.append(f'<div class="pillar"><div class="label">{label}</div><div class="ganji">{pillar[0]}{pillar[1]}</div></div>')

    return f'''
  <section class="snapshot">
    <h2>사주 스냅샷 — 한눈에 보기</h2>
    <div class="pillars">{"".join(pillar_cards)}</div>
    <div class="oheng">{_oheng_rows_html(d["adj_scores"])}</div>
    <div class="chart-caption">오행 최종 점수(합화 시프트 반영) 기준</div>
    <div class="snap-facts">
      <div><b>대운</b> {_daewoon_line(d)}</div>
      <div><b>용신</b> {_yongshin_line(d)}</div>
    </div>
  </section>'''


def render_html(report_markdown: str, saju_data: dict) -> str:
    """report_pipeline.stream_report()가 만든 리포트 텍스트 + compute_all() JSON으로
    완성된 리포트 HTML(문서 전체)을 만든다. render_pdf()에 그대로 넘기면 PDF가 된다."""
    meta = saju_data["meta"]
    name = meta["name"]
    sex_label = "여성" if meta["sex"] == "여성" else "남성"
    today = datetime.date.today()
    analysis_date = f"{today.year}년 {today.month}월 {today.day}일"

    sections = _split_top_sections(report_markdown)
    if sections:
        sections = sections[1:]  # 첫 '##' 섹션은 항상 표지 메인 타이틀 — 브랜드/이름은 코드가 직접 채우므로 버린다

    # 목차/스냅샷처럼 프로그램이 직접 그리는 장은 AI 텍스트를 신뢰하지 않고 건너뛴다.
    content_sections = [(h, b) for h, b in sections if "목차" not in h and "스냅샷" not in h]

    verdict_idx = next((i for i, (h, _) in enumerate(content_sections) if "총평" in h), None)

    if verdict_idx is None:
        chapters = content_sections
        verdict = None
        after_verdict = []
    else:
        chapters = content_sections[:verdict_idx]
        verdict = content_sections[verdict_idx]
        after_verdict = content_sections[verdict_idx + 1:]

    closing = after_verdict[-1] if after_verdict else None
    extra_after_verdict = after_verdict[:-1] if len(after_verdict) > 1 else []

    # ---- TOC + 챕터 HTML ----
    toc_rows = []
    chapter_html_blocks = []
    for i, (heading, body) in enumerate(chapters, start=1):
        num = f"{i:02d}"
        toc_rows.append(f'<div><span class="n">{num}</span>{heading}</div>')
        chapter_html_blocks.append(f'''
  <div class="chapter">
    <div class="chapter-head"><span class="chapter-num">{num}</span><h2 class="chapter-title">{heading}</h2></div>
    {_md_to_html_fragment(body)}
  </div>''')

    for heading, body in extra_after_verdict:
        chapter_html_blocks.append(f'''
  <div class="chapter">
    <div class="chapter-head"><h2 class="chapter-title">{heading}</h2></div>
    {_md_to_html_fragment(body)}
  </div>''')

    # 마지막 요약 줄은 일부러 넣지 않는다 — 챕터 수가 많아지면(심층질문/궁합 등) 목차가
    # 한 페이지를 거의 다 채워서, 이 한 줄 때문에 페이지가 하나 더 늘어나는 경우가 잦았음.

    # ---- 총평 HTML ----
    verdict_html = ""
    if verdict:
        v_heading, v_body = verdict
        thesis, dont_items, do_items = _parse_verdict(v_body)
        if thesis or dont_items or do_items:
            dodont_html = ""
            if dont_items or do_items:
                dont_lis = "".join(f"<li>{x}</li>" for x in dont_items)
                do_lis = "".join(f"<li>{x}</li>" for x in do_items)
                dodont_html = f'''
    <div class="dodont">
      <div class="dont"><h3>3대 Don't</h3><ul>{dont_lis}</ul></div>
      <div class="do"><h3>3대 Do</h3><ul>{do_lis}</ul></div>
    </div>'''
            thesis_html = f'<div class="thesis">{thesis}</div>' if thesis else ""
            verdict_html = f'''
  <div class="verdict">
    <h2>{v_heading}</h2>
    {thesis_html}{dodont_html}
  </div>'''
        else:
            verdict_html = f'''
  <div class="verdict">
    <h2>{v_heading}</h2>
    {_md_to_html_fragment(v_body)}
  </div>'''

    # ---- 마무리 페이지 HTML ----
    # 이 섹션은 소제목 승격(**볼드 한 줄** -> h3.sub) 규칙을 적용하지 않는다 — 마지막 문단이
    # 통째로 볼드인 '브랜드 마무리 문구'(예: "답답명쾌 사주해답소가, OOO 님의 다음 10년을
    # 응원합니다.")가 h3로 바뀌어 유실되는 걸 막기 위함.
    closing_html = ""
    if closing:
        c_heading, c_body = closing
        c_soup = BeautifulSoup(md_lib.markdown(c_body.strip(), extensions=["extra"]), "html.parser")
        paragraphs = c_soup.find_all("p")
        sign = paragraphs[-1].get_text() if paragraphs else ""
        body_ps = "".join(str(p) for p in paragraphs[:-1]) if len(paragraphs) > 1 else ""
        closing_html = f'''
  <div class="closing">
    <div class="eyebrow2">{c_heading}</div>
    {body_ps}
    <div class="sign">{sign}</div>
  </div>'''

    body_html = f'''
  <div class="eyebrow">답답명쾌 사주해답소</div>
  <h1 class="title">{name} 님을 위한<br>프리미엄 종합사주 해답지</h1>
  <div class="subtitle">전통 명리학의 정밀 연산 알고리즘과 현대적 라이프 솔루션의 결합</div>
  <div class="meta">
    <span><b>분석 대상</b> {name} 님 ({sex_label} 명식)</span>
    <span><b>분석 기준일</b> {analysis_date}</span>
  </div>

  <hr class="rule">

  <div class="toc">{"".join(toc_rows)}</div>

  <hr class="rule">
{_snapshot_html(saju_data)}
{"".join(chapter_html_blocks)}
{verdict_html}
{closing_html}
'''

    return DOC_SKELETON.format(title=f"{name} 님 프리미엄 종합사주 해답지", css=CSS, body=body_html)


def render_pdf(html: str) -> bytes:
    """완성된 HTML 문서를 PDF 바이트로 렌더링한다 (headless Chromium, @media print 규칙 적용)."""
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page()
            page.emulate_media(media="print")
            page.set_content(html, wait_until="networkidle")
            pdf_bytes = page.pdf(format="A4", print_background=True)
        finally:
            browser.close()
    return pdf_bytes


def build_pdf(report_markdown: str, saju_data: dict) -> bytes:
    """report_pipeline이 만든 리포트 텍스트 + saju_data JSON으로 바로 PDF 바이트를 만든다."""
    html = render_html(report_markdown, saju_data)
    return render_pdf(html)
