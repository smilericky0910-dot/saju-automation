# -*- coding: utf-8 -*-
"""
사주 리포트 PDF 자동 조립 및 렌더링 엔진 (v5.3 - 100% 상업용 완성 버전)
- 원국표 4대 귀인(천을/천덕/천관/문창) 전수 정밀 매핑
- 제5장 용신(用神) 처방전 시각화 카드 추가
- 제14장 10대 대운 로드맵 종합표 추가
- 제15장 향후 5개년 세운 종합표 추가
- 모바일 13pt 가독성 및 1페이지 목차 정돈
"""
import os, re, json, subprocess, shutil
from typing import Dict, Any, List

OHAENG_COLORS = {'木': '#4E788B', '火': '#D26E6E', '土': '#C89B54', '金': '#8F8E8C', '水': '#384B66'}

STEM_INFO_MAP = {
    '甲': {'element': '木', 'polarity': '陽', 'ko': '갑'}, '乙': {'element': '木', 'polarity': '陰', 'ko': '을'},
    '丙': {'element': '火', 'polarity': '陽', 'ko': '병'}, '丁': {'element': '火', 'polarity': '陰', 'ko': '정'},
    '戊': {'element': '土', 'polarity': '陽', 'ko': '무'}, '己': {'element': '土', 'polarity': '陰', 'ko': '기'},
    '庚': {'element': '金', 'polarity': '陽', 'ko': '경'}, '辛': {'element': '金', 'polarity': '陰', 'ko': '신'},
    '壬': {'element': '水', 'polarity': '陽', 'ko': '임'}, '癸': {'element': '水', 'polarity': '陰', 'ko': '계'},
}

BRANCH_INFO_MAP = {
    '子': {'element': '水', 'polarity': '陰', 'animal': '쥐', 'ko': '자'}, '丑': {'element': '土', 'polarity': '陰', 'animal': '소', 'ko': '축'},
    '寅': {'element': '木', 'polarity': '陽', 'animal': '호랑이', 'ko': '인'}, '卯': {'element': '木', 'polarity': '陽', 'animal': '토끼', 'ko': '묘'},
    '辰': {'element': '土', 'polarity': '陽', 'animal': '용', 'ko': '진'}, '巳': {'element': '火', 'polarity': '陰', 'animal': '뱀', 'ko': '사'},
    '午': {'element': '火', 'polarity': '陽', 'animal': '말', 'ko': '오'}, '未': {'element': '土', 'polarity': '陰', 'animal': '양', 'ko': '미'},
    '申': {'element': '金', 'polarity': '陽', 'animal': '원숭이', 'ko': '신'}, '酉': {'element': '金', 'polarity': '陰', 'animal': '닭', 'ko': '유'},
    '戌': {'element': '土', 'polarity': '陽', 'animal': '개', 'ko': '술'}, '亥': {'element': '水', 'polarity': '陽', 'animal': '돼지', 'ko': '해'},
}

ANIMAL_COLOR_NAMES = {'木': '푸른', '火': '붉은', '土': '황금', '金': '하얀', '水': '검은'}
ANIMAL_EMOJIS = {'쥐': '🐭', '소': '🐮', '호랑이': '🐯', '토끼': '🐰', '용': '🐲', '뱀': '🐍', '말': '🐴', '양': '🐑', '원숭이': '🐵', '닭': '🐔', '개': '🐶', '돼지': '🐷'}

GLOBAL_CSS = """
@page { size: A4 portrait; margin: 20mm 16mm 22mm 16mm; @bottom-center { content: "— " counter(page) " —"; font-size: 10pt; color: #7A7267; font-family: sans-serif; } }
@page:first { margin: 0; @bottom-center { content: ""; } }
* { box-sizing: border-box; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { margin: 0; padding: 0; font-family: 'Pretendard', sans-serif; font-size: 13pt; line-height: 1.85; color: #2B2B2B; background-color: #F9F8F3; }

h1, h2, h3 { font-family: 'Noto Serif KR', 'Nanum Myeongjo', serif; color: #1D2D44; }

.cover-page { width: 210mm; height: 297mm; padding: 35mm 20mm; border: 12mm solid #ECE8DC; display: flex; flex-direction: column; justify-content: space-between; align-items: center; text-align: center; page-break-after: always; }
.cover-inner { width: 100%; height: 100%; border: 1.5px solid #A3344B; padding: 30mm 15mm; display: flex; flex-direction: column; justify-content: space-between; align-items: center; }
.cover-sub { font-size: 18pt; color: #5C5247; letter-spacing: 0.18em; margin-bottom: 20px; font-weight: 600; }
.cover-main { font-size: 38pt; font-weight: 800; color: #1D2D44; letter-spacing: -0.02em; line-height: 1.35; margin: 0 0 25px 0; }
.cover-badge { display: inline-block; background-color: #A3344B; color: #FFF; font-size: 11pt; padding: 6px 20px; border-radius: 20px; letter-spacing: 0.08em; margin-bottom: 30px; font-weight: 700; }
.cover-meta { background: rgba(255,255,255,0.92); border: 1px solid #DCD5C5; border-radius: 12px; padding: 18px 28px; font-size: 12pt; color: #3D352E; }

.chapter-divider { min-height: 220mm; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; page-break-before: always; page-break-after: always; padding: 40mm 15mm; }
.chapter-num { font-size: 14pt; color: #A3344B; letter-spacing: 0.25em; font-weight: 700; margin-bottom: 12px; }
.chapter-title { font-size: 26pt; font-weight: 800; color: #1D2D44; line-height: 1.35; margin: 0 0 24px 0; }
.chapter-line { width: 50px; height: 2.5px; background-color: #A3344B; margin: 0 auto; }

.chapter-content { page-break-before: always; }
.chapter-header { border-bottom: 2px solid #A3344B; padding-bottom: 8px; margin-bottom: 20px; page-break-after: avoid; }

.toc-page { page-break-before: always; width: 100%; }
.toc-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 7px 14px; margin-top: 12px; }
.toc-item { display: flex; align-items: center; gap: 8px; padding: 6px 8px; background: rgba(255, 255, 255, 0.7); border-radius: 6px; border: 1px solid #EAE5D9; }
.toc-badge { background: #A3344B; color: #FFF; font-size: 9pt; font-weight: 700; padding: 2px 6px; border-radius: 4px; line-height: 1.2; }
.toc-text { flex: 1; display: flex; flex-direction: column; }
.toc-title { font-size: 10.5pt; font-weight: 700; color: #1D2D44; }
.toc-desc { font-size: 8.5pt; color: #6E6659; line-height: 1.3; }

.snapshot-container { width: 100%; margin-bottom: 20px; background: rgba(255,255,255,0.75); border-radius: 10px; padding: 8px; border: 1px solid #E5E0D3; page-break-inside: avoid; }
.snapshot-table { width: 100%; border-collapse: separate; border-spacing: 3px; table-layout: fixed; text-align: center; }
.snapshot-th { padding: 4px 2px; font-size: 9pt; color: #6E6659; background: #EFECE3; border-radius: 4px; font-weight: 700; }
.snapshot-td { padding: 3px 2px; font-size: 8.5pt; background: #FFF; border-radius: 4px; border: 1px solid #EAE6DB; vertical-align: middle; }
.char-cell { padding: 6px 2px; font-size: 14pt; font-weight: 800; color: #FFF !important; border-radius: 6px; }
.focus-cell { outline: 2.5px solid #A3344B !important; opacity: 1.0 !important; position: relative; z-index: 2; }
.dim-cell { opacity: 0.32 !important; filter: grayscale(40%) !important; }

.profile-card { background: #FFF; border: 1.5px solid #DCD5C5; border-radius: 12px; padding: 16px 20px; display: flex; align-items: center; gap: 16px; margin-bottom: 20px; page-break-inside: avoid; }
.profile-avatar { font-size: 40pt; line-height: 1; background: #F4F1EA; padding: 12px; border-radius: 50%; border: 1px solid #E0DAD0; }
.profile-info { flex: 1; }
.profile-name { font-size: 17pt; font-weight: 800; color: #1D2D44; margin-bottom: 4px; }

.ohaeng-bars-card { background: #FFF; border: 1px solid #E5E0D3; border-radius: 10px; padding: 14px 18px; margin-bottom: 16px; page-break-inside: avoid; }
.ohaeng-bar-row { display: flex; align-items: center; margin-bottom: 7px; font-size: 10.5pt; }
.ohaeng-bar-label { width: 70px; font-weight: 700; }
.ohaeng-bar-track { flex: 1; height: 13px; background: #EDE8DD; border-radius: 6px; overflow: hidden; margin: 0 12px; }
.ohaeng-bar-fill { height: 100%; border-radius: 6px; }
.ohaeng-bar-value { width: 48px; text-align: right; font-weight: 700; color: #4A4238; }

.grid-3-cards { display: flex; flex-direction: column; gap: 12px; margin: 18px 0; page-break-inside: avoid; }
.white-card { background: rgba(255,255,255,0.95); border: 1px solid #E5DFD1; border-radius: 10px; padding: 14px 16px; font-size: 12pt; line-height: 1.8; }
.white-card-title { font-weight: 700; color: #A3344B; font-size: 13pt; margin-bottom: 8px; border-bottom: 1px dashed #DCD5C5; padding-bottom: 4px; }

.dodont-container { display: flex; flex-direction: column; gap: 14px; margin: 20px 0; page-break-inside: avoid; }
.dodont-card { background: #FFF; border-radius: 10px; border: 1px solid #E2DCD0; overflow: hidden; }
.dodont-header-dont { background: #5C5247; color: #FFF; padding: 10px 16px; font-weight: 700; font-size: 12pt; }
.dodont-header-do { background: #A3344B; color: #FFF; padding: 10px 16px; font-weight: 700; font-size: 12pt; }
.dodont-body { padding: 14px 16px; font-size: 12pt; line-height: 1.8; color: #333; }

.feature-impact-block { background: #FFF; border-left: 4px solid #A3344B; border-radius: 0 8px 8px 0; padding: 14px 18px; margin: 16px 0; page-break-inside: avoid; font-size: 12.5pt; }
p { margin: 0 0 14px 0; text-align: justify; }
blockquote { border-left: 3px solid #C89B54; margin: 14px 0; padding: 10px 16px; background: rgba(200,155,84,0.08); font-size: 12pt; }
"""

# ============================================================================
# 4대 귀인(천을/천덕/천관/문창) 정밀 판별 함수
# ============================================================================
def calculate_pillar_gwiins(day_master: str, month_branch: str, stem: str, branch: str) -> str:
    CHEONEUL_MAP = {
        '甲': ('丑', '未'), '戊': ('丑', '未'), '庚': ('丑', '未'),
        '乙': ('子', '申'), '己': ('子', '申'),
        '丙': ('亥', '酉'), '丁': ('亥', '酉'),
        '辛': ('寅', '午'), '壬': ('巳', '卯'), '癸': ('巳', '卯')
    }
    CHEONDEOK_MAP = {
        '寅': '丁', '卯': '申', '辰': '壬', '巳': '辛',
        '午': '亥', '未': '甲', '申': '癸', '酉': '寅',
        '戌': '丙', '亥': '乙', '子': '巳', '丑': '庚'
    }
    CHEONGWAN_MAP = {
        '甲': '未', '乙': '辰', '丙': '巳', '丁': '寅', '戊': '卯',
        '己': '酉', '庚': '亥', '辛': '申', '壬': '戌', '癸': '午'
    }
    MUNCHANG_MAP = {
        '甲': '巳', '乙': '午', '丙': '申', '戊': '申', '丁': '酉',
        '己': '酉', '庚': '亥', '辛': '子', '壬': '寅', '癸': '卯'
    }

    g_list = []
    if branch in CHEONEUL_MAP.get(day_master, ()):
        g_list.append("천을귀인")
    td = CHEONDEOK_MAP.get(month_branch)
    if td and (branch == td or stem == td):
        g_list.append("천덕귀인")
    if branch == CHEONGWAN_MAP.get(day_master):
        g_list.append("천관귀인")
    if branch == MUNCHANG_MAP.get(day_master):
        g_list.append("문창귀인")

    return "·".join(g_list) if g_list else "—"

def generate_snapshot_html(saju_data: Dict[str, Any], chapter_type: str = 'all') -> str:
    meta = saju_data.get('meta', {})
    day_master = meta.get('day_master', '甲')
    pillars_raw = saju_data.get('pillars_raw', {})
    has_hour = meta.get('has_hour', False) and (pillars_raw.get('hour') is not None)
    m_stem, m_branch = pillars_raw.get('month', ('丁', '酉'))

    cols = []
    if has_hour:
        h_stem, h_branch = pillars_raw.get('hour')
        cols.append(('시주', h_stem, h_branch, 'hour'))
    else:
        cols.append(('시주', None, None, 'hour'))

    d_stem, d_branch = pillars_raw.get('day')
    cols.append(('일주', d_stem, d_branch, 'day'))
    m_stem, m_branch_val = pillars_raw.get('month')
    cols.append(('월주', m_stem, m_branch_val, 'month'))
    y_stem, y_branch = pillars_raw.get('year')
    cols.append(('년주', y_stem, y_branch, 'year'))

    pos_idx = {p: i for i, p in enumerate(saju_data.get('positions', []))}
    deities = saju_data.get('deities', {})

    def is_focused(col_type: str, row_type: str, deity_name: str) -> bool:
        if chapter_type == 'all': return True
        if chapter_type == 'day_pillar': return col_type == 'day'
        if chapter_type == 'wolji_guckguk': return (col_type == 'month') and (row_type in ('branch_char', 'branch_ohaeng', 'branch_deity', 'unseong', 'sinsal', 'gwiin'))
        if chapter_type == 'career_gwansung': return (col_type == 'month') or ('관' in deity_name)
        if chapter_type == 'wealth_jaesung': return (col_type == 'day') or ('재' in deity_name)
        if chapter_type == 'partner_ilji': return (col_type == 'day') and (row_type in ('branch_char', 'branch_ohaeng', 'branch_deity', 'unseong', 'sinsal', 'gwiin'))
        return True

    col_data = []
    for label, stem, branch, c_type in cols:
        if stem is None or branch is None:
            col_data.append({'label': label, 'c_type': c_type, 'stem_deity': '—', 'stem_ohaeng': '—', 'stem_char': '—', 'stem_color': '#8F8E8C', 'branch_char': '—', 'branch_color': '#8F8E8C', 'branch_ohaeng': '—', 'branch_deity': '—', 'unseong': '—', 'sinsal': '—', 'gwiin': '—'})
            continue
        s_info = STEM_INFO_MAP.get(stem, {'element': '木', 'polarity': '陽', 'ko': stem})
        b_info = BRANCH_INFO_MAP.get(branch, {'element': '木', 'polarity': '陽', 'animal': '동물', 'ko': branch})
        s_pol = '양' if s_info.get('polarity') == '陽' else '음'
        s_elem_name = {'木':'목','火':'화','土':'토','金':'금','水':'수'}.get(s_info.get('element'), '목')
        b_pol = '양' if b_info.get('polarity') == '陽' else '음'
        b_elem_name = {'木':'목','火':'화','土':'토','金':'금','水':'수'}.get(b_info.get('element'), '토')

        s_deity = '비견' if c_type == 'day' else (re.search(r'\((.*?)\)', deities.get('시간' if c_type=='hour' else ('월간' if c_type=='month' else '년간'), '—')).group(1) if '(' in deities.get('시간' if c_type=='hour' else ('월간' if c_type=='month' else '년간'), '') else deities.get('시간' if c_type=='hour' else ('월간' if c_type=='month' else '년간'), '—'))
        b_pos = '시지' if c_type == 'hour' else ('일지' if c_type == 'day' else ('월지' if c_type == 'month' else '년지'))
        b_deity = re.search(r'\((.*?)\)', deities.get(b_pos, '—')).group(1) if '(' in deities.get(b_pos, '') else deities.get(b_pos, '—')

        b_idx = pos_idx.get(b_pos, -1)
        unseong = saju_data.get('unseong_list', [])[b_idx] if (0 <= b_idx < len(saju_data.get('unseong_list', []))) else '—'
        sinsal = saju_data.get('sinsal_list', [])[b_idx] if (0 <= b_idx < len(saju_data.get('sinsal_list', []))) else '—'
        
        gwiin = calculate_pillar_gwiins(day_master, m_branch, stem, branch)

        col_data.append({
            'label': label, 'c_type': c_type, 'stem_deity': s_deity, 'stem_ohaeng': f"{stem}({s_pol}{s_elem_name})",
            'stem_char': f"{s_info.get('ko')}{stem}", 'stem_color': OHAENG_COLORS.get(s_info.get('element'), '#8F8E8C'),
            'branch_char': f"{b_info.get('ko')}{branch}", 'branch_color': OHAENG_COLORS.get(b_info.get('element'), '#8F8E8C'),
            'branch_ohaeng': f"{branch}({b_pol}{b_elem_name})", 'branch_deity': b_deity, 'unseong': unseong, 'sinsal': sinsal, 'gwiin': gwiin
        })

    def cell_class(c_type, r_type, deity):
        return ('snapshot-td focus-cell' if chapter_type != 'all' else 'snapshot-td') if is_focused(c_type, r_type, deity) else 'snapshot-td dim-cell'

    rows = (
        ('십성(천간)', [ (c['c_type'], 'stem_deity', c['stem_deity'], cell_class(c['c_type'], 'stem_deity', c['stem_deity'])) for c in col_data ]),
        ('음양오행', [ (c['c_type'], 'stem_ohaeng', c['stem_ohaeng'], cell_class(c['c_type'], 'stem_ohaeng', c['stem_deity'])) for c in col_data ]),
        ('천간', [ (c['c_type'], 'stem_char', c['stem_char'], cell_class(c['c_type'], 'stem_char', c['stem_deity']), c['stem_color']) for c in col_data ]),
        ('지지', [ (c['c_type'], 'branch_char', c['branch_char'], cell_class(c['c_type'], 'branch_char', c['branch_deity']), c['branch_color']) for c in col_data ]),
        ('음양오행', [ (c['c_type'], 'branch_ohaeng', c['branch_ohaeng'], cell_class(c['c_type'], 'branch_ohaeng', c['branch_deity'])) for c in col_data ]),
        ('십성(지지)', [ (c['c_type'], 'branch_deity', c['branch_deity'], cell_class(c['c_type'], 'branch_deity', c['branch_deity'])) for c in col_data ]),
        ('십이운성', [ (c['c_type'], 'unseong', c['unseong'], cell_class(c['c_type'], 'unseong', c['branch_deity'])) for c in col_data ]),
        ('십이신살', [ (c['c_type'], 'sinsal', c['sinsal'], cell_class(c['c_type'], 'sinsal', c['branch_deity'])) for c in col_data ]),
        ('귀인', [ (c['c_type'], 'gwiin', c['gwiin'], cell_class(c['c_type'], 'gwiin', c['branch_deity'])) for c in col_data ]),
    )

    html = ['<div class="snapshot-container"><table class="snapshot-table"><thead><tr><th class="snapshot-th" style="width:16%;">구분</th>']
    for c in col_data: html.append(f'<th class="snapshot-th">{c["label"]}</th>')
    html.append('</tr></thead><tbody>')
    
    for label, cells in rows:
        html.append(f'<tr><td class="snapshot-th" style="background:#F4F1EA;font-size:8pt;">{label}</td>')
        for c in cells:
            if len(c) == 5:
                col_k, row_k, val_text, css_cls, bg_color = c
                html.append(f'<td class="char-cell {css_cls}" style="background:{bg_color};">{val_text}</td>')
            else:
                col_k, row_k, val_text, css_cls = c
                html.append(f'<td class="{css_cls}">{val_text}</td>')
        html.append('</tr>')
        
    html.append('</tbody></table></div>')
    return "\n".join(html)

def generate_ohaeng_bars_html(saju_data: Dict[str, Any]) -> str:
    adj = saju_data.get('adj_scores', {})
    total = sum(adj.values()) or 1.0
    html = ['<div class="ohaeng-bars-card"><div style="font-weight:700;color:#1D2D44;margin-bottom:10px;font-size:11pt;">📊 실질 오행(五行) 에너지 분포도 (합화 반영)</div>']
    for elem in ('木', '火', '土', '金', '水'):
        score = adj.get(elem, 0.0)
        pct = (score / total) * 100.0
        color = OHAENG_COLORS.get(elem, '#8F8E8C')
        elem_name = {'木':'목(木)','火':'화(火)','土':'토(土)','金':'금(金)','水':'수(水)'}.get(elem, elem)
        html.append(f'<div class="ohaeng-bar-row"><span class="ohaeng-bar-label" style="color:{color};">{elem_name}</span><div class="ohaeng-bar-track"><div class="ohaeng-bar-fill" style="width:{pct:.1f}%;background:{color};"></div></div><span class="ohaeng-bar-value">{pct:.1f}%</span></div>')
    html.append('</div>')
    return "\n".join(html)

# ============================================================================
# 제5장 전용: 용신(用神) 처방전 시각화 카드
# ============================================================================
def generate_yongshin_card_html(saju_data: Dict[str, Any]) -> str:
    eokbu = saju_data.get('eokbu_elem', '木')
    johu = saju_data.get('johu_info', {})
    tonggwan = saju_data.get('tonggwan_info', {})
    strength = saju_data.get('adj_strength', {}).get('strength', '중화')

    OHAENG_NAMES = {'木': '목(木, 나무)', '火': '화(火, 불)', '土': '토(土, 흙)', '金': '금(金, 쇠)', '水': '수(水, 물)'}

    html = ['<div style="background:#FFF; border:1.5px solid #A3344B; border-radius:12px; padding:14px 18px; margin-bottom:22px; page-break-inside:avoid; box-shadow:0 3px 10px rgba(163,52,75,0.05);">']
    html.append('<div style="font-size:12pt; font-weight:800; color:#A3344B; margin-bottom:10px;">🎯 나를 살리는 핵심 기운: 용신(用神) 처방전</div>')
    
    # 억부용신
    e_color = OHAENG_COLORS.get(eokbu, '#4E788B')
    html.append(f"""
    <div style="display:flex; align-items:center; gap:10px; margin-bottom:8px; background:#FBF9F5; padding:8px 12px; border-radius:8px; border-left:4px solid {e_color};">
        <div style="min-width:75px; font-weight:700; color:#1D2D44; font-size:10.5pt;">억부용신(主)</div>
        <div style="background:{e_color}; color:#FFF; font-weight:800; font-size:10.5pt; padding:2px 8px; border-radius:5px;">{OHAENG_NAMES.get(eokbu, eokbu)}</div>
        <div style="font-size:9.5pt; color:#5C5247; flex:1;">{strength} 사주의 균형을 잡고 나의 주도성과 뿌리를 세우는 핵심 기운</div>
    </div>
    """)

    # 조후용신
    if johu.get('needed'):
        j_elem = johu.get('element', '火')
        j_color = OHAENG_COLORS.get(j_elem, '#D26E6E')
        html.append(f"""
        <div style="display:flex; align-items:center; gap:10px; margin-bottom:8px; background:#FBF9F5; padding:8px 12px; border-radius:8px; border-left:4px solid {j_color};">
            <div style="min-width:75px; font-weight:700; color:#1D2D44; font-size:10.5pt;">조후용신(氣)</div>
            <div style="background:{j_color}; color:#FFF; font-weight:800; font-size:10.5pt; padding:2px 8px; border-radius:5px;">{OHAENG_NAMES.get(j_elem, j_elem)}</div>
            <div style="font-size:9.5pt; color:#5C5247; flex:1;">태어난 계절의 기후 불균형을 조절하여 생기를 틔워주는 기운</div>
        </div>
        """)
    else:
        html.append(f"""
        <div style="display:flex; align-items:center; gap:10px; margin-bottom:8px; background:#FBF9F5; padding:8px 12px; border-radius:8px; border-left:4px solid #8F8E8C;">
            <div style="min-width:75px; font-weight:700; color:#1D2D44; font-size:10.5pt;">조후용신(氣)</div>
            <div style="background:#8F8E8C; color:#FFF; font-weight:700; font-size:9.5pt; padding:2px 8px; border-radius:5px;">조후 원만</div>
            <div style="font-size:9.5pt; color:#5C5247; flex:1;">극단적으로 춥거나 덥지 않아 기후적 편중은 발생하지 않습니다.</div>
        </div>
        """)

    # 통관용신
    if tonggwan.get('needed'):
        t_elem = tonggwan.get('element', '土')
        t_color = OHAENG_COLORS.get(t_elem, '#C89B54')
        html.append(f"""
        <div style="display:flex; align-items:center; gap:10px; background:#FBF9F5; padding:8px 12px; border-radius:8px; border-left:4px solid {t_color};">
            <div style="min-width:75px; font-weight:700; color:#1D2D44; font-size:10.5pt;">통관용신(通)</div>
            <div style="background:{t_color}; color:#FFF; font-weight:800; font-size:10.5pt; padding:2px 8px; border-radius:5px;">{OHAENG_NAMES.get(t_elem, t_elem)}</div>
            <div style="font-size:9.5pt; color:#5C5247; flex:1;">원국 내 상극하는 두 기운의 충돌을 이어주고 순환시키는 완충 다리</div>
        </div>
        """)

    html.append('</div>')
    return "\n".join(html)

# ============================================================================
# 제14장 전용: 10대 대운 로드맵 종합표
# ============================================================================
def generate_daewoon_roadmap_html(saju_data: Dict[str, Any]) -> str:
    daewoon = saju_data.get('daewoon', {})
    pillars = daewoon.get('pillars', [])
    if not pillars: return ""

    STEM_INFO = {'甲': '木', '乙': '木', '丙': '火', '丁': '火', '戊': '土', '己': '土', '庚': '金', '辛': '金', '壬': '水', '癸': '水'}
    BRANCH_INFO = {'子': '水', '丑': '土', '寅': '木', '卯': '木', '辰': '土', '巳': '火', '午': '火', '未': '土', '申': '金', '酉': '金', '戌': '土', '亥': '水'}

    html = ['<div style="width:100%; margin:16px 0 22px 0; background:#FFF; border:1px solid #DCD5C5; border-radius:12px; padding:12px; page-break-inside:avoid; box-shadow:0 2px 8px rgba(0,0,0,0.03);">']
    html.append(f'<div style="font-size:12pt; font-weight:800; color:#1D2D44; margin-bottom:10px; border-bottom:1.5px solid #A3344B; padding-bottom:5px;">🗺️ 인생 100년 대운(大運) 로드맵 (대운수 {daewoon.get("num", 1)})</div>')
    html.append('<div style="overflow-x:auto;"><table style="width:100%; border-collapse:separate; border-spacing:3px; text-align:center; font-size:8.5pt;">')
    
    # 1. 시작나이
    html.append('<tr><td style="background:#EFECE3; padding:4px 2px; font-weight:700; color:#6E6659; border-radius:4px; width:55px;">시작나이</td>')
    for p in pillars:
        gm = " 🈳" if p.get('gongmang') else ""
        html.append(f'<td style="background:#F4F1EA; padding:4px 2px; font-weight:800; color:#1D2D44; border-radius:4px;">{p["age"]}세{gm}</td>')
    html.append('</tr>')

    # 2. 천간십성
    html.append('<tr><td style="background:#EFECE3; padding:4px 2px; font-weight:700; color:#6E6659; border-radius:4px;">천간십성</td>')
    for p in pillars:
        html.append(f'<td style="background:#FFF; padding:4px 2px; border:1px solid #EAE6DB; border-radius:4px;">{p.get("sipsin_stem", "—")}</td>')
    html.append('</tr>')

# 3. 천간 글자 (한글 + 한자 병기)
    html.append('<tr><td style="background:#EFECE3; padding:4px 2px; font-weight:700; color:#6E6659; border-radius:4px;">천간</td>')
    for p in pillars:
        stem = p['stem']
        stem_ko = STEM_INFO_MAP.get(stem, {}).get('ko', '')
        color = OHAENG_COLORS.get(STEM_INFO.get(stem, '木'), '#888')
        html.append(f'<td style="background:{color}; color:#FFF; font-weight:800; padding:4px 2px; border-radius:4px;"><span style="font-size:8pt; opacity:0.9;">{stem_ko}</span><br/><span style="font-size:12pt;">{stem}</span></td>')
    html.append('</tr>')

    # 4. 지지 글자 (한글 + 한자 병기)
    html.append('<tr><td style="background:#EFECE3; padding:4px 2px; font-weight:700; color:#6E6659; border-radius:4px;">지지</td>')
    for p in pillars:
        branch = p['branch']
        branch_ko = BRANCH_INFO_MAP.get(branch, {}).get('ko', '')
        color = OHAENG_COLORS.get(BRANCH_INFO.get(branch, '土'), '#888')
        html.append(f'<td style="background:{color}; color:#FFF; font-weight:800; padding:4px 2px; border-radius:4px;"><span style="font-size:8pt; opacity:0.9;">{branch_ko}</span><br/><span style="font-size:12pt;">{branch}</span></td>')
    html.append('</tr>')

    # 5. 지지십성
    html.append('<tr><td style="background:#EFECE3; padding:4px 2px; font-weight:700; color:#6E6659; border-radius:4px;">지지십성</td>')
    for p in pillars:
        html.append(f'<td style="background:#FFF; padding:4px 2px; border:1px solid #EAE6DB; border-radius:4px;">{p.get("sipsin_branch", "—")}</td>')
    html.append('</tr>')

    # 6. 12운성
    html.append('<tr><td style="background:#EFECE3; padding:4px 2px; font-weight:700; color:#6E6659; border-radius:4px;">12운성</td>')
    for p in pillars:
        html.append(f'<td style="background:#FFF; padding:4px 2px; border:1px solid #EAE6DB; border-radius:4px; font-weight:700; color:#A3344B;">{p.get("unseong", "—")}</td>')
    html.append('</tr>')

    html.append('</table></div></div>')
    return "\n".join(html)

def generate_profile_card_html(saju_data: Dict[str, Any]) -> str:
    meta = saju_data.get('meta', {})
    name = meta.get('name', '고객')
    sex = meta.get('sex', '성별미상')
    day_master = meta.get('day_master', '甲')
    d_stem, d_branch = saju_data.get('pillars_raw', {}).get('day', ('甲', '子'))
    stem_info = STEM_INFO_MAP.get(day_master, {})
    branch_info = BRANCH_INFO_MAP.get(d_branch, {})
    elem = stem_info.get('element', '木')
    pol = '음' if stem_info.get('polarity') == '陰' else '양'
    elem_name = {'木':'목','火':'화','土':'토','金':'금','水':'수'}.get(elem, '목')
    animal = branch_info.get('animal', '소')
    animal_full = f"{ANIMAL_COLOR_NAMES.get(elem, '푸른')} {animal}"
    return f"""<div class="profile-card"><div class="profile-avatar">{ANIMAL_EMOJIS.get(animal, '🐮')}</div><div class="profile-info"><div class="profile-name">{name} 님 ({sex})</div><div style="font-size:10.5pt;color:#5C5247;line-height:1.6;"><strong>생년월일:</strong> {meta.get('birth_date', '미상')}<br/><strong>오행:</strong> {pol}{elem_name} · <strong>일주 동물:</strong> {animal_full}</div><div style="font-size:8.5pt;color:#8C8275;margin-top:6px;">※ 일주 동물은 태어난 연도의 띠가 아닌, 본인의 일주(日柱) 기운을 상징하는 메타포입니다.</div></div></div>"""

def generate_toc_html(customer_name: str) -> str:
    STANDARD_TOC = (
        ("01", "표지", "분석 대상자 프로필 및 기준 명식"),
        ("02", "목차", "리포트 전체 구조 및 챕터 안내"),
        ("03", "사주에 대하여", "사주를 대하는 올바른 관점과 입문 프롤로그"),
        ("04", "사주 스냅샷", "사주 원국표 및 일주 동물 메타포"),
        ("05", "오행 에너지 균형", "합화 반영 점수와 신강·신약, 억부/조후용신"),
        ("06", "본질적 자아", "일간과 일지로 보는 내면 기질과 실생활 3장면"),
        ("07", "생애 4주기 흐름", "초년·청년·중년·말년의 인생 사계절"),
        ("08", "격국과 사회적 가면", "세상에 비추는 나의 얼굴과 내면 심리"),
        ("09", "진로 및 직업 전략", "조직 환경 적합도 vs 독립 전문직 모델"),
        ("10", "재물운의 흐름", "정재와 편재가 그리는 자산 축적의 궤적"),
        ("11", "자산 방어 전략", "지켜야 할 돈의 원칙과 재정 리스크 차단법"),
        ("12", "인간관계·애정·가족운", "묵묵함 뒤의 진심과 배우자궁 소통 가이드"),
        ("13", "건강운과 회복 리듬", "몸이 보내는 신호와 맞춤형 일상 이완 루틴"),
        ("14", "인생 거시 흐름 (대운)", "10대 대운 전수 분석 및 10년 주기 기회"),
        ("15", "미시적 세운 흐름", "향후 5개년(2026~2030) 연도별 집중 실천 전략"),
        ("16", "스페셜 심층 질문 답변", "명리학적 맞춤형 고민 해결 및 전환기 전략"),
        ("17", "일상 균형 가이드", "색상·공간·루틴으로 채우는 맞춤 개운법"),
        ("18", "최종 총평", "인생 한 줄 관통 메시지 & DO / DON'T"),
        ("19", "마무리 응원 메시지", "삶의 계절을 맞이하는 따뜻한 격려"),
    )
    html = ['<div class="toc-page">']
    html.append("""<div class="chapter-header"><span style="font-size:10.5pt;color:#A3344B;font-weight:700;">제2장</span><div style="font-size:22pt;font-weight:800;color:#1D2D44;margin-top:4px;">목차 (Contents)</div></div>""")
    html.append(f'<p style="font-size:11pt;color:#5C5247;margin-bottom:12px;">이 리포트는 다음 순서로, <strong>{customer_name}</strong> 님의 인생을 처음부터 끝까지 하나의 이야기처럼 풀어드립니다.</p>')
    html.append('<div class="toc-grid">')
    for num, title, desc in STANDARD_TOC:
        html.append(f"""<div class="toc-item"><span class="toc-badge">{num}</span><div class="toc-text"><span class="toc-title">{title}</span><span class="toc-desc">{desc}</span></div></div>""")
    html.append('</div></div>')
    return "\n".join(html)

def parse_markdown_with_cards(text: str) -> str:
    text = re.sub(r'(?:###?\s*)?(?:DON\'?T|절대\s*피할\s*3가지)[^\n]*\n([\s\S]*?)(?:###?\s*)?(?:DO|당장\s*실천할\s*3가지)[^\n]*\n([\s\S]*?)(?=(?:\n###|\n##|\Z))', lambda m: f'<div class="dodont-container"><div class="dodont-card"><div class="dodont-header-dont">🚫 DON\'T (절대 피할 3가지)</div><div class="dodont-body">{"<br/>".join("• " + l.strip("-*0123456789. ") for l in m.group(1).strip().splitlines() if l.strip())}</div></div><div class="dodont-card"><div class="dodont-header-do">✨ DO (당장 실천할 3가지)</div><div class="dodont-body">{"<br/>".join("• " + l.strip("-*0123456789. ") for l in m.group(2).strip().splitlines() if l.strip())}</div></div></div>', text, flags=re.I)
    text = re.sub(r'(?:###?\s*)?직장에서의\s*모습\s*:\s*([\s\S]*?)(?:###?\s*)?갈등\s*상황\s*(?:대처)?\s*:\s*([\s\S]*?)(?:###?\s*)?일상의\s*(?:무의식적\s*)?욕망\s*:\s*([\s\S]*?)(?=(?:\n###|\n##|\Z))', lambda m: f'<div class="grid-3-cards"><div class="white-card"><div class="white-card-title">💼 직장에서의 모습</div>{m.group(1).strip()}</div><div class="white-card"><div class="white-card-title">⚡ 갈등 상황 대처</div>{m.group(2).strip()}</div><div class="white-card"><div class="white-card-title">🌱 일상의 무의식적 욕망</div>{m.group(3).strip()}</div></div>', text)
    text = re.sub(r'\[(?:기질적\s*)?특징\]\s*:\s*([\s\S]*?)\n+\[(?:실생활\s*)?영향(?:\s*장면)?\]\s*:\s*([\s\S]*?)(?=(?:\n###|\n##|\Z))', lambda m: f'<div class="feature-impact-block"><div style="font-weight:700;color:#1D2D44;font-size:12.5pt;">📌 핵심 기질 및 특징</div><p>{m.group(1).strip()}</p><div style="font-weight:700;color:#A3344B;margin-top:8px;font-size:11.5pt;">🔍 실생활 발현 양상</div><p>{m.group(2).strip()}</p></div>', text)
    out = []
    in_p = False
    for line in text.splitlines():
        s = line.strip()
        if not s:
            if in_p: out.append('</p>'); in_p = False
            continue
        if s.startswith('<div') or s.startswith('</div') or s.startswith('<table') or s.startswith('</table'):
            if in_p: out.append('</p>'); in_p = False
            out.append(line); continue
        line = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', line)
        if s.startswith('### '):
            if in_p: out.append('</p>'); in_p = False
            out.append(f'<h3 style="font-size:13.5pt;color:#1D2D44;margin:18px 0 8px 0;border-left:3px solid #A3344B;padding-left:8px;">{s[4:]}</h3>')
        elif s.startswith('## '):
            if in_p: out.append('</p>'); in_p = False
            out.append(f'<h2 style="font-size:15pt;color:#1D2D44;margin:22px 0 10px 0;">{s[3:]}</h2>')
        elif s.startswith('> '):
            if in_p: out.append('</p>'); in_p = False
            out.append(f'<blockquote>{s[2:]}</blockquote>')
        else:
            if not in_p: out.append('<p>'); in_p = True
            out.append(line)
    if in_p: out.append('</p>')
    return "\n".join(out)

def parse_clean_chapters(report_markdown: str) -> List[Dict[str, Any]]:
    pattern = re.compile(
        r'(?:^|\n)(?:#+\s*|\*\*\s*)?제\s*(\d+)\s*장[\.:\s\-]*([^\n]*)\n([\s\S]*?)(?=(?:\n(?:#+\s*|\*\*\s*)?제\s*\d+\s*장|\Z))'
    )
    raw_list = []
    for m in pattern.finditer(report_markdown):
        ch_num = int(m.group(1))
        title = m.group(2).strip()
        body = m.group(3).strip()
        clean_title = re.sub(r'[*#_]+', '', title).strip() or f"제{ch_num}장"
        raw_list.append({'num': ch_num, 'title': clean_title, 'body': body})

    # 중복 번호 처리: 14장처럼 2회에 걸쳐 나온 본문은 하나로 자연스럽게 합치고, 빈 더미는 배제
    combined = {}
    for ch in raw_list:
        num = ch['num']
        if num not in combined:
            combined[num] = ch
        else:
            if len(ch['body'].strip()) > 0:
                combined[num]['body'] = combined[num]['body'].strip() + "\n\n" + ch['body'].strip()

    return [combined[k] for k in sorted(combined.keys())]

def build_report_html(saju_data: Dict[str, Any], report_markdown: str) -> str:
    meta = saju_data.get('meta', {})
    name = meta.get('name', '고객')
    p_raw = saju_data.get('pillars_raw', {})
    has_hour = meta.get('has_hour', False) and (p_raw.get('hour') is not None)
    y_stem, y_branch = p_raw.get('year', ('丙', '辰'))
    m_stem, m_branch = p_raw.get('month', ('丁', '酉'))
    d_stem, d_branch = p_raw.get('day', ('乙', '丑'))
    if has_hour:
        h_stem, h_branch = p_raw.get('hour', ('戊', '寅'))
        hour_str = f"{h_stem}{h_branch}"
    else:
        hour_str = "시간모름"
    ganji_str = f"년주 {y_stem}{y_branch} | 월주 {m_stem}{m_branch} | 일주 {d_stem}{d_branch} | 시주 {hour_str}"

    html = ["<!DOCTYPE html><html><head><meta charset='utf-8'/><title>사주 해답지</title>", f"<style>{GLOBAL_CSS}</style></head><body>"]
    html.append(f"""<div class="cover-page"><div class="cover-inner"><div style="margin-top:15mm;"><div class="cover-sub">답답명쾌 사주 해답소</div><div class="cover-badge">PREMIUM REPORT</div><div class="cover-main">프리미엄<br/>사주 해답지</div></div><div style="margin-bottom:15mm;"><div class="cover-meta"><span style="font-size:14pt;font-weight:700;color:#A3344B;">{name}</span> 님의 심층 명리 감정서<br/><small style="color:#7A7267;">기준 명식: {ganji_str}</small></div></div></div></div>""")

    chapters = parse_clean_chapters(report_markdown)
    rendered_toc = False

    for ch in chapters:
        ch_num, ch_title, ch_body = ch['num'], ch['title'], ch['body']
        if ch_num == 1 or "표지" in ch_title: continue

        if ch_num == 2 or "목차" in ch_title:
            if not rendered_toc:
                html.append(generate_toc_html(name))
                rendered_toc = True
            continue

        html.append(f"""<div class="chapter-divider"><div class="chapter-num">CHAPTER {ch_num:02d}</div><div class="chapter-title">{ch_title}</div><div class="chapter-line"></div></div><div class="chapter-content"><div class="chapter-header"><span style="font-size:10.5pt;color:#A3344B;font-weight:700;">제{ch_num}장</span><div style="font-size:20pt;font-weight:800;color:#1D2D44;margin-top:4px;">{ch_title}</div></div>""")
        title_clean = ch_title.replace(" ", "")

        if any(k in title_clean for k in ("스냅샷", "프로필", "원국표")):
            html.append(generate_profile_card_html(saju_data))
            html.append(generate_snapshot_html(saju_data, chapter_type='all'))
        elif any(k in title_clean for k in ("기본명식", "오행에너지", "오행분석", "에너지균형")):
            html.append(generate_snapshot_html(saju_data, chapter_type='all'))
            html.append(generate_ohaeng_bars_html(saju_data))
            # 제5장 전용: 용신(用神) 처방전 카드 추가!
            html.append(generate_yongshin_card_html(saju_data))
        elif any(k in title_clean for k in ("일주론", "본질적자아", "일간일지")):
            html.append(generate_snapshot_html(saju_data, chapter_type='day_pillar'))
        elif "격국" in title_clean:
            html.append(generate_snapshot_html(saju_data, chapter_type='wolji_guckguk'))
        elif any(k in title_clean for k in ("진로", "직업", "적성", "사회적")):
            html.append(generate_snapshot_html(saju_data, chapter_type='career_gwansung'))
        elif any(k in title_clean for k in ("재물", "자산", "재정", "금전")):
            html.append(generate_snapshot_html(saju_data, chapter_type='wealth_jaesung'))
        elif any(k in title_clean for k in ("인간관계", "애정", "배우자", "연애", "가족")):
            html.append(generate_snapshot_html(saju_data, chapter_type='partner_ilji'))
        elif any(k in title_clean for k in ("4주기", "생애", "시간흐름", "건강운", "회복리듬")):
            html.append(generate_snapshot_html(saju_data, chapter_type='all'))
        elif "대운" in title_clean:
            # 제14장 전용: 인생 100년 대운 로드맵 종합표 추가!
            html.append(generate_daewoon_roadmap_html(saju_data))

        html.append(parse_markdown_with_cards(ch_body))
        html.append('</div>')
    html.append("</body></html>")
    return "\n".join(html)

def convert_html_to_pdf(html_content: str, output_pdf_path: str) -> bool:
    temp_html_path = output_pdf_path.replace('.pdf', '_temp.html')
    with open(temp_html_path, 'w', encoding='utf-8') as f: f.write(html_content)

    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            b = p.chromium.launch(headless=True)
            page = b.new_page()
            page.goto(f"file://{os.path.abspath(temp_html_path)}")
            page.wait_for_load_state('networkidle')
            page.pdf(path=output_pdf_path, format="A4", print_background=True, margin={"top":"0mm","bottom":"0mm","left":"0mm","right":"0mm"})
            b.close()
        if os.path.exists(output_pdf_path) and os.path.getsize(output_pdf_path) > 1000:
            if os.path.exists(temp_html_path): os.remove(temp_html_path)
            return True
    except Exception: pass

    try:
        from weasyprint import HTML
        HTML(filename=temp_html_path).write_pdf(output_pdf_path)
        if os.path.exists(output_pdf_path) and os.path.getsize(output_pdf_path) > 1000:
            if os.path.exists(temp_html_path): os.remove(temp_html_path)
            return True
    except Exception: pass

    for exe in [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        shutil.which("msedge"), shutil.which("chrome")
    ]:
        if exe and os.path.exists(exe):
            cmd = [exe, "--headless", "--disable-gpu", "--run-all-compositor-stages-before-draw", "--no-pdf-header-footer", f"--print-to-pdf={os.path.abspath(output_pdf_path)}", os.path.abspath(temp_html_path)]
            try:
                subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
                if os.path.exists(output_pdf_path) and os.path.getsize(output_pdf_path) > 1000:
                    if os.path.exists(temp_html_path): os.remove(temp_html_path)
                    return True
            except Exception: continue
    return False

def render_saju_report_pdf(saju_data: Dict[str, Any], report_markdown: str, output_pdf_path: str) -> bool:
    return convert_html_to_pdf(build_report_html(saju_data, report_markdown), output_pdf_path)