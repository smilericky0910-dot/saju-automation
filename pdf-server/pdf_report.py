# -*- coding: utf-8 -*-
"""
n8n이 생성·검증까지 마친 리포트 텍스트(마크다운) + AdvancedSajuAnalyzer.compute_all() JSON을
받아서, "사주 리포트 PDF 자동 조립 및 렌더링 엔진 규칙서" (v5.0)에 정의된 디자인 그대로
완성된 PDF로 렌더링하는 모듈.

핵심 원칙(지침 1-1과 동일한 이유):
- 사주 원국표(8칸 스냅샷)·오행 분포·대운·용신 같은 "숫자/사실" 데이터는 절대 AI가 쓴 텍스트에서
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
BRANCH_ELEM = {'子': '水', '丑': '土', '寅': '木', '卯': '木', '辰': '土', '巳': '火',
               '午': '火', '未': '土', '申': '金', '酉': '金', '戌': '土', '亥': '水'}
ELEM_HANGUL = {'木': '목', '火': '화', '土': '토', '金': '금', '水': '수'}
ELEM_VAR = {'木': 'wood', '火': 'fire', '土': 'earth', '金': 'metal', '水': 'water'}

# 십성(십신) 이름 -> 계열. 챕터별 포커스 규칙에서 "관성/식상/재성 셀"을 찾을 때 쓴다.
SIPSIN_GROUP = {
    '정관': 'gwan', '편관': 'gwan',
    '식신': 'siksang', '상관': 'siksang',
    '정재': 'jae', '편재': 'jae',
}

CSS = """
:root {
  --paper: #F9F8F3;
  --ink: #2B2B2B;
  --ink-soft: #5C5247;
  --ink-faint: #9c9683;
  --accent: #A3344B;
  --accent-strong: #7d2839;
  --accent-soft: #f1dbe0;
  --rule: #ddd6c4;
  --cover-ink: #1D2D44;

  --wood: #4E788B;
  --fire: #D26E6E;
  --earth: #C89B54;
  --metal: #8F8E8C;
  --water: #384B66;

  --font-display: "Song Myung", "Nanum Myeongjo", "Noto Serif KR", serif;
  --font-body: "Gowun Dodum", "Noto Sans KR", -apple-system, "Malgun Gothic", sans-serif;
}

* { box-sizing: border-box; }
html { font-size: 16px; }
body {
  background: var(--paper); color: var(--ink); font-family: var(--font-body);
  font-size: 1rem; line-height: 1.75; -webkit-font-smoothing: antialiased;
  margin: 0;
}

/* ---- 공통 페이지 프레임 (표지 제외) ---- */
.page { position: relative; max-width: 700px; margin: 0 auto; padding: 2.2rem 0.5rem 3rem; }

/* ---- 표지 ---- */
.cover {
  position: relative; height: 100vh; display: flex; align-items: center; justify-content: center;
  text-align: center; overflow: hidden;
  background:
    radial-gradient(ellipse at 30% 20%, rgba(78,120,139,0.16), transparent 55%),
    radial-gradient(ellipse at 75% 80%, rgba(163,52,75,0.14), transparent 55%),
    linear-gradient(180deg, #f4f0e4 0%, #efe9da 55%, #e9e2d0 100%);
}
.cover::before {
  content: ""; position: absolute; inset: 0;
  background-image: repeating-linear-gradient(115deg, rgba(0,0,0,0.015) 0 2px, transparent 2px 6px);
}
.cover-inner { position: relative; z-index: 1; padding: 0 2.4rem; }
.cover-eyebrow {
  font-family: var(--font-display); font-size: 16pt; color: var(--ink-soft);
  letter-spacing: 0.15em; margin-bottom: 1.6rem;
}
.cover-title {
  font-family: var(--font-display); font-size: 38pt; font-weight: 700; color: var(--cover-ink);
  letter-spacing: -0.02em; line-height: 1.35; margin: 0 0 2.2rem;
}
.cover-meta {
  display: inline-block; font-size: 11pt; color: var(--ink-soft);
  background: rgba(255,255,255,0.55); border: 1px solid rgba(255,255,255,0.8);
  border-radius: 999px; padding: 0.6rem 1.6rem;
}

/* ---- 목차 / 서두 텍스트 ---- */
.eyebrow { font-size: 0.75rem; font-weight: 600; letter-spacing: 0.16em; color: var(--accent); text-transform: uppercase; }
h1.title { font-family: var(--font-display); font-weight: 700; font-size: 1.9rem; line-height: 1.4; margin: 0.6rem 0 0.9rem; color: var(--ink); }
.subtitle { font-size: 0.98rem; color: var(--ink-soft); margin-bottom: 1.4rem; }
.meta { display: flex; flex-wrap: wrap; gap: 0.4rem 1rem; font-size: 0.82rem; color: var(--ink-faint); }
.meta b { color: var(--ink-soft); font-weight: 600; }
hr.rule { border: none; border-top: 1px solid var(--rule); margin: 2.4rem 0; }

.toc { display: grid; grid-template-columns: 1fr 1fr; gap: 0.55rem 1.5rem; font-size: 0.88rem; color: var(--ink-soft); }
.toc span.n { color: var(--accent); font-weight: 600; margin-right: 0.5em; }
.toc .closing { grid-column: 1 / -1; color: var(--ink-faint); }

/* ---- 원국표(스냅샷) 8칸: 4열(시/일/월/년) x 4행(십성/천간/지지/운성·신살) ----
   규칙서 3장: 스냅샷 블록 전체 높이는 페이지의 약 1/3 이내로 제한 (기존 대비 폭·여백·폰트 축소) */
.snapshot { background: rgba(255,255,255,0.55); border: 1px solid var(--rule); border-radius: 6px; padding: 0.85rem 0.9rem; margin: 0 0 0.9rem; }
.snapshot h2 { font-family: var(--font-display); font-size: 0.85rem; font-weight: 700; margin: 0 0 0.6rem; color: var(--ink); }
.snap-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.3rem; margin-bottom: 0.7rem; }
.snap-col { display: grid; grid-template-rows: auto auto auto auto; gap: 0.2rem; border-radius: 5px; transition: opacity 0.2s; }
.snap-col.dim { opacity: 0.3; filter: grayscale(40%); }
.snap-col-label { text-align: center; font-size: 0.56rem; color: var(--ink-faint); letter-spacing: 0.05em; margin-bottom: 0.05rem; }
.snap-cell { border-radius: 5px; padding: 0.22rem 0.15rem; text-align: center; font-size: 0.58rem; border: 1px solid var(--rule); background: #fff; }
.snap-cell.stem, .snap-cell.branch { font-family: var(--font-display); font-size: 0.78rem; font-weight: 700; color: #fff; border: none; padding: 0.28rem 0.15rem; }
.snap-cell.sipsin { color: var(--ink-soft); font-size: 0.54rem; }
.snap-cell.extra { color: var(--ink-faint); font-size: 0.5rem; }
.snap-cell.focus { border: 2px solid var(--accent); opacity: 1; transform: scale(1.04); box-shadow: 0 1px 4px rgba(163,52,75,0.18); }

.oheng { display: grid; gap: 0.25rem; margin-bottom: 0.1rem; }
.oheng-row { display: grid; grid-template-columns: 34px 1fr auto; align-items: center; gap: 0.35rem; }
.oheng-label { font-size: 0.6rem; color: var(--ink-soft); white-space: nowrap; }
.oheng-track { position: relative; height: 6px; border-radius: 4px; background: var(--rule); }
.oheng-fill { position: absolute; inset: 0; width: 0; border-radius: 4px; }
.oheng-value { font-size: 0.6rem; font-weight: 700; white-space: nowrap; color: var(--ink); }

.snap-facts { display: grid; gap: 0.2rem; font-size: 0.62rem; color: var(--ink-soft); border-top: 1px solid var(--rule); padding-top: 0.45rem; margin-top: 0.7rem; }
.snap-facts b { color: var(--ink); font-weight: 600; }

/* ---- 챕터 구분 페이지: 제목만 크게 표시되는 독립된 한 페이지 ---- */
.chapter-divider {
  min-height: 247mm; display: flex; flex-direction: column; align-items: center; justify-content: center;
  text-align: center; padding: 2rem 1.5rem;
}
.chapter-divider .chapter-num { font-size: 0.85rem; font-weight: 600; color: var(--accent); letter-spacing: 0.22em; text-transform: uppercase; margin-bottom: 1.4rem; }
.chapter-divider h2.chapter-title { font-family: var(--font-display); font-weight: 700; font-size: 2.6rem; line-height: 1.5; margin: 0 auto; max-width: 20ch; color: var(--ink); }
.chapter-divider .rule { width: 56px; height: 2px; background: var(--accent); border: none; margin: 1.6rem auto 0; }

/* ---- 챕터 본문 (구분 페이지 다음 장부터 시작) ---- */
.chapter { margin-top: 0; }
h3.sub { font-size: 0.98rem; font-weight: 700; color: var(--accent-strong); margin: 1.4rem 0 0.55rem; }
p { margin: 0 0 1rem; }
.chapter p:last-child { margin-bottom: 0; }
strong { font-weight: 700; background: linear-gradient(to bottom, transparent 62%, var(--accent-soft) 62%); padding: 0 0.05em; }
ul.actions { list-style: none; margin: 0.9rem 0 1.1rem; padding: 0; display: grid; gap: 0.55rem; }
ul.actions li { padding-left: 1.1rem; position: relative; font-size: 0.96rem; color: var(--ink); }
ul.actions li::before { content: "—"; position: absolute; left: 0; color: var(--accent); }

/* ---- 패턴 A: 직장에서의 모습 / 갈등 상황 / 일상의 욕망 -> 카드 그리드 ---- */
.scene-grid { display: grid; grid-template-columns: repeat(var(--n, 3), 1fr); gap: 0.7rem; margin: 1.1rem 0 1.3rem; }
.scene-card { background: rgba(255,255,255,0.85); border-radius: 10px; padding: 14px; font-size: 0.86rem; color: var(--ink); }
.scene-card .scene-label { display: block; font-size: 0.72rem; font-weight: 700; color: var(--accent); margin-bottom: 0.4rem; }

/* ---- 패턴 C: [특징] / [실생활 영향] -> 특징 박스 + 인용 박스 ---- */
.trait-box { background: rgba(255,255,255,0.85); border-radius: 10px; padding: 14px; margin: 1rem 0 0.6rem; font-size: 0.92rem; }
.trait-box .trait-label { display: block; font-size: 0.72rem; font-weight: 700; color: var(--accent); margin-bottom: 0.4rem; }
.impact-box { border-left: 3px solid var(--accent); padding: 0.2rem 0 0.2rem 1rem; margin: 0 0 1.3rem; font-size: 0.9rem; color: var(--ink-soft); }
.impact-box .impact-label { display: block; font-size: 0.72rem; font-weight: 700; color: var(--accent); margin-bottom: 0.3rem; }

/* ---- 총평: DO / DON'T 대조 카드 ---- */
.verdict { margin-top: 3.2rem; padding-top: 2rem; border-top: 2px solid var(--ink); }
.verdict h2 { font-family: var(--font-display); font-size: 1.5rem; margin: 0 0 1.2rem; }
.verdict .thesis { font-family: var(--font-display); font-size: 1.15rem; line-height: 1.65; color: var(--accent-strong); margin-bottom: 1.8rem; }
.dodont { display: grid; grid-template-columns: 1fr 1fr; gap: 0.9rem; }
.dodont-card { border-radius: 8px; overflow: hidden; }
.dodont-card .badge { font-size: 0.78rem; letter-spacing: 0.08em; font-weight: 700; color: #fff; background: var(--accent); padding: 0.5rem 0.9rem; }
.dodont-card.do .badge { background: var(--wood); }
.dodont-card ul { list-style: none; margin: 0; padding: 0.8rem 0.9rem; display: grid; gap: 0.55rem; font-size: 0.88rem; background: rgba(255,255,255,0.7); }
.dodont-card li { padding-left: 1.1rem; position: relative; }
.dodont-card.dont li::before { content: "×"; position: absolute; left: 0; color: var(--accent); font-weight: 700; }
.dodont-card.do li::before { content: "✓"; position: absolute; left: 0; color: var(--wood); font-weight: 700; }

/* ---- 마무리 페이지 ---- */
.closing { margin: 3.6rem 0 0; background: var(--cover-ink); color: #f2efe4; padding: 2.6rem 1.8rem 3rem; text-align: center; border-radius: 6px; }
.closing .eyebrow2 { font-size: 0.72rem; letter-spacing: 0.18em; text-transform: uppercase; color: #b9c4d4; margin-bottom: 1rem; }
.closing p { font-size: 1rem; line-height: 1.85; color: #ece7d9; max-width: 46ch; margin: 0 auto 1rem; }
.closing .sign { font-family: var(--font-display); font-size: 1.1rem; font-weight: 700; margin-top: 1.2rem; color: #fff; }

@media print {
  @page { size: A4; margin: 25mm 20mm; }
  * { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  .cover { height: auto; min-height: 247mm; break-after: page; }
  .page { max-width: none; padding: 0; }
  .snapshot, .chapter, .verdict, .closing { break-inside: avoid-page; }
  .chapter-divider { height: auto; break-before: page; break-after: page; }
  .verdict h2, .closing .eyebrow2, h3.sub { break-after: avoid-page; }
  .scene-grid, .dodont, .trait-box, .snapshot { break-inside: avoid-page; }
  .toc { break-before: page; }
}
"""

DOC_SKELETON = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>{title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Song+Myung&family=Gowun+Dodum&family=Noto+Serif+KR:wght@400;700&family=Noto+Sans+KR:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>{css}</style>
</head>
<body>
{body}
</body>
</html>
"""

# 규칙서 1장의 "족자 프레임"(상단/하단 12mm 가로 족자 봉 바). PDF 인쇄에서 `position: fixed`는
# 페이지마다 안정적으로 반복되지 않으므로, Playwright의 header/footer 템플릿으로 모든 페이지에
# 고정 렌더링한다(표지 페이지도 이 템플릿을 함께 쓰지만, 얇고 옅은 바라 표지 배경과 크게
# 부딪히지 않는다).
_SCROLL_BAR_CSS = (
    "width:100%; height:12mm; margin:0; "
    "background:linear-gradient(180deg, #A3344B 0%, #A3344B 22%, transparent 22%, transparent 78%, #A3344B 78%, #A3344B 100%); "
    "opacity:0.35;"
)

HEADER_TEMPLATE = f'<div style="{_SCROLL_BAR_CSS}"></div>'

FOOTER_TEMPLATE = f"""
<div style="width:100%; position:relative;">
  <div style="{_SCROLL_BAR_CSS}"></div>
  <div style="position:absolute; left:0; right:0; top:0; height:12mm; display:flex; align-items:center; justify-content:center;
              font-size:8px; color:#fff; font-family:'Noto Sans KR',sans-serif;">
    — <span class="pageNumber"></span> —
  </div>
</div>
"""


def _md_to_html_fragment(text: str) -> str:
    """마크다운 조각을 HTML로 변환한 뒤, 우리 디자인 규칙을 적용한다:
    1) '**소제목만 있는 한 줄**' 문단 -> <h3 class="sub"> 소제목
    2) 모든 <ul> -> class="actions"
    3) 패턴 A/B/C 텍스트 마커를 카드 UI로 변환 (규칙서 5장)
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

    return _apply_card_patterns(str(soup))


# 패턴 A: "직장에서의 모습:", "갈등 상황:", "일상의 욕망:" 로 시작하는 문단들을 묶어서
# 화이트 카드 그리드로 변환한다.
_SCENE_LABELS = ["직장에서의 모습", "갈등 상황", "일상의 욕망"]
_SCENE_RE = re.compile(
    r'<p>\s*(?:<strong>)?\s*(' + "|".join(_SCENE_LABELS) + r')\s*[:：](?:</strong>)?\s*(.*?)</p>',
    re.DOTALL,
)

# 패턴 C: "[특징]" 문단 바로 뒤에 "[실생활 영향]" 문단이 오는 조합을 특징 박스 + 인용 박스로 변환.
_TRAIT_RE = re.compile(
    r'<p>\s*\[\s*특징\s*\]\s*[:：]?\s*(.*?)</p>\s*<p>\s*\[\s*실생활\s*영향\s*\]\s*[:：]?\s*(.*?)</p>',
    re.DOTALL,
)


def _apply_card_patterns(html: str) -> str:
    def replace_scene_blocks(text: str) -> str:
        out = []
        pos = 0
        for mo in re.finditer(
            r'(?:<p>\s*(?:<strong>)?\s*(?:' + "|".join(_SCENE_LABELS) + r')\s*[:：](?:</strong>)?\s*.*?</p>\s*){2,}',
            text, re.DOTALL,
        ):
            out.append(text[pos:mo.start()])
            block = mo.group(0)
            items = _SCENE_RE.findall(block)
            cards = "".join(
                f'<div class="scene-card"><span class="scene-label">{label}</span>{body.strip()}</div>'
                for label, body in items
            )
            out.append(f'<div class="scene-grid" style="--n:{len(items)};">{cards}</div>')
            pos = mo.end()
        out.append(text[pos:])
        return "".join(out)

    def replace_trait_blocks(text: str) -> str:
        def repl(mo):
            trait, impact = mo.group(1).strip(), mo.group(2).strip()
            return (
                f'<div class="trait-box"><span class="trait-label">특징</span>{trait}</div>'
                f'<div class="impact-box"><span class="impact-label">실생활 영향</span>{impact}</div>'
            )
        return _TRAIT_RE.sub(repl, text)

    html = replace_scene_blocks(html)
    html = replace_trait_blocks(html)
    return html


def _split_top_sections(markdown_text: str):
    """'## ' 로 시작하는 줄 기준으로 전체 리포트를 (제목, 본문) 리스트로 쪼갠다."""
    parts = re.split(r'(?m)^##\s+', markdown_text)
    sections = []
    for chunk in parts[1:]:
        lines = chunk.split("\n", 1)
        heading = lines[0].strip()
        body = lines[1] if len(lines) > 1 else ""
        sections.append((heading, body.strip()))
    return sections


def _parse_verdict(body: str):
    """'## [최종 총평]' 섹션 본문에서 한 줄 메시지 / DON'T / DO를 뽑아낸다."""
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


def _parse_deity_string(s: str):
    """deities dict의 값("甲(비견)" 또는 "일간(乙)")에서 (글자, 십성라벨) 을 뽑는다."""
    m = re.match(r'(.+?)\((.+?)\)', s or "")
    if not m:
        return s, ""
    a, b = m.group(1), m.group(2)
    # "일간(乙)" 형태는 글자가 괄호 안에 있으므로 뒤집는다.
    if a in ("일간",):
        return b, "본인(일간)"
    return a, b


def _snap_columns(d: dict):
    """positions/deities/unseong_list/sinsal_list 를 년·월·일·시 4개 열로 재구성한다.
    반환: [{'key':'year','label':'년주','stem':..,'stem_deity':..,'branch':..,'branch_deity':..,'unseong':..,'sinsal':..}, ...]
    시주 정보가 없으면(has_hour=False) 해당 열은 생략한다.
    """
    positions = d['positions']
    deities = d['deities']
    unseong_list = d['unseong_list']
    sinsal_list = d['sinsal_list']
    idx = {p: i for i, p in enumerate(positions)}

    def col(key, label, stem_pos, branch_pos):
        if stem_pos not in idx or branch_pos not in idx:
            return None
        stem_char, stem_deity = _parse_deity_string(deities[stem_pos])
        branch_char, branch_deity = _parse_deity_string(deities[branch_pos])
        i = idx[branch_pos]
        return {
            'key': key, 'label': label,
            'stem': stem_char, 'stem_deity': stem_deity,
            'branch': branch_char, 'branch_deity': branch_deity,
            'unseong': unseong_list[i], 'sinsal': sinsal_list[i],
        }

    cols = [
        col('hour', '시주', '시간', '시지'),
        col('day', '일주', '일간(본인)', '일지'),
        col('month', '월주', '월간', '월지'),
        col('year', '년주', '년간', '년지'),
    ]
    return [c for c in cols if c]


# 규칙서 3장의 챕터 매핑 기준. 챕터 제목(heading)에 포함된 키워드로 판별한다.
_FOCUS_RULES = [
    (re.compile(r'명식|오행'), {'cols': 'all'}),
    (re.compile(r'본질적\s*자아|일주론'), {'cols': ['day']}),
    (re.compile(r'생애\s*4주기|시간\s*흐름'), {'cols': 'all'}),
    (re.compile(r'격국'), {'cols': [], 'branch_only': ['month']}),
    (re.compile(r'진로|직업'), {'cols': ['month'], 'sipsin_group': 'gwan'}),
    (re.compile(r'재물|재정|자산'), {'cols': ['day'], 'sipsin_group': 'jae'}),
    (re.compile(r'인간관계|애정|가족'), {'cols': [], 'branch_only': ['day']}),
    (re.compile(r'건강'), {'cols': 'all'}),
]


def _focus_rule_for(heading: str):
    for pattern, rule in _FOCUS_RULES:
        if pattern.search(heading):
            return rule
    return None


def _snapshot_html(d: dict, heading: str = "") -> str:
    cols = _snap_columns(d)
    rule = _focus_rule_for(heading)
    focus_cols = set(rule['cols']) if rule and rule['cols'] != 'all' else (set(c['key'] for c in cols) if rule else set())
    branch_only = set(rule.get('branch_only', [])) if rule else set()
    sipsin_group = rule.get('sipsin_group') if rule else None

    col_blocks = []
    for c in cols:
        dim = bool(rule) and c['key'] not in focus_cols and c['key'] not in branch_only
        stem_elem = STEM_ELEM.get(c['stem'], '木')
        branch_elem = BRANCH_ELEM.get(c['branch'], '木')

        def focus_class(part, deity_label):
            classes = []
            if c['key'] in branch_only and part == 'branch':
                classes.append('focus')
            if sipsin_group and SIPSIN_GROUP.get(deity_label) == sipsin_group:
                classes.append('focus')
            return " " + " ".join(classes) if classes else ""

        col_blocks.append(f'''
      <div class="snap-col{" dim" if dim else ""}">
        <div class="snap-col-label">{c['label']}</div>
        <div class="snap-cell sipsin{focus_class('stem', c['stem_deity'])}">{c['stem_deity']}</div>
        <div class="snap-cell stem{focus_class('stem', c['stem_deity'])}" style="background:var(--{ELEM_VAR[stem_elem]});">{c['stem']}</div>
        <div class="snap-cell branch{focus_class('branch', c['branch_deity'])}" style="background:var(--{ELEM_VAR[branch_elem]});">{c['branch']}</div>
        <div class="snap-cell extra{focus_class('branch', c['branch_deity'])}">{c['unseong']}{(' · ' + c['sinsal']) if c['sinsal'] and c['sinsal'] != '-' else ''}</div>
      </div>''')

    return f'''
  <section class="snapshot">
    <h2>사주 원국 스냅샷</h2>
    <div class="snap-grid">{"".join(col_blocks)}</div>
    <div class="oheng">{_oheng_rows_html(d["adj_scores"])}</div>
    <div class="snap-facts">
      <div><b>대운</b> {_daewoon_line(d)}</div>
      <div><b>용신</b> {_yongshin_line(d)}</div>
    </div>
  </section>'''


def render_html(report_markdown: str, saju_data: dict) -> str:
    """n8n이 만든 리포트 텍스트 + compute_all() JSON으로 완성된 리포트 HTML(문서 전체)을
    만든다. render_pdf()에 그대로 넘기면 PDF가 된다."""
    meta = saju_data["meta"]
    name = meta["name"]
    sex_label = "여성" if meta["sex"] == "여성" else "남성"
    pr = saju_data["pillars_raw"]
    myeongsik = "".join(f"{s}{b}" for s, b in [pr['year'], pr['month'], pr['day']] if s and b)
    if pr.get('hour'):
        myeongsik += "".join(pr['hour'])

    sections = _split_top_sections(report_markdown)
    if sections:
        sections = sections[1:]  # 첫 '##' 섹션은 항상 표지 메인 타이틀 — 코드가 직접 채우므로 버린다

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

    # ---- 표지 ----
    cover_html = f'''
  <section class="cover">
    <div class="cover-inner">
      <div class="cover-eyebrow">답답명쾌 사주 해답소</div>
      <h1 class="cover-title">{name} 님을 위한<br>프리미엄 사주 해답지</h1>
      <div class="cover-meta">분석 대상: {name} 님 ({sex_label}) &nbsp;|&nbsp; 기준 명식: {myeongsik}</div>
    </div>
  </section>'''

    # ---- TOC ----
    toc_rows = []
    chapter_html_blocks = []
    for i, (heading, body) in enumerate(chapters, start=1):
        num = f"{i:02d}"
        toc_rows.append(f'<div><span class="n">{num}</span>{heading}</div>')
        chapter_html_blocks.append(f'''
  <div class="chapter-divider">
    <span class="chapter-num">CHAPTER {num}</span>
    <h2 class="chapter-title">{heading}</h2>
    <hr class="rule">
  </div>
  <div class="chapter">
    {_snapshot_html(saju_data, heading) if _focus_rule_for(heading) else ""}
    {_md_to_html_fragment(body)}
  </div>''')

    for heading, body in extra_after_verdict:
        chapter_html_blocks.append(f'''
  <div class="chapter-divider">
    <h2 class="chapter-title">{heading}</h2>
    <hr class="rule">
  </div>
  <div class="chapter">
    {_md_to_html_fragment(body)}
  </div>''')

    # ---- 총평 ----
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
      <div class="dodont-card dont"><div class="badge">DON'T · 절대 피할 3가지</div><ul>{dont_lis}</ul></div>
      <div class="dodont-card do"><div class="badge">DO · 지금 당장 실천할 3가지</div><ul>{do_lis}</ul></div>
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

    # ---- 마무리 페이지 ----
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
{cover_html}
<div class="page">
  <div class="toc">{"".join(toc_rows)}</div>
  <hr class="rule">
{"".join(chapter_html_blocks)}
{verdict_html}
{closing_html}
</div>
'''

    return DOC_SKELETON.format(title=f"{name} 님 프리미엄 사주 해답지", css=CSS, body=body_html)


def render_pdf(html: str) -> bytes:
    """완성된 HTML 문서를 PDF 바이트로 렌더링한다 (headless Chromium, @media print 규칙 적용).
    규칙서 6장의 페이지 번호(표지 제외, 하단 중앙)는 Playwright의 footer template으로 구현한다."""
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page()
            page.emulate_media(media="print")
            page.set_content(html, wait_until="networkidle")
            pdf_bytes = page.pdf(
                format="A4",
                print_background=True,
                margin={"top": "25mm", "bottom": "25mm", "left": "20mm", "right": "20mm"},
                display_header_footer=True,
                header_template=HEADER_TEMPLATE,
                footer_template=FOOTER_TEMPLATE,
            )
        finally:
            browser.close()
    return pdf_bytes


def build_pdf(report_markdown: str, saju_data: dict) -> bytes:
    """n8n이 만든 리포트 텍스트 + saju_data JSON으로 바로 PDF 바이트를 만든다."""
    html = render_html(report_markdown, saju_data)
    return render_pdf(html)
