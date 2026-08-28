# -*- coding: utf-8 -*-
"""
사주분석 대화형 웹 애플리케이션 제8판 (Complete Enhanced Version)
- 작성일: 2026-08-26
- 기술 스택: Python, Streamlit
- 주요 향상사항:
  ✅ 納音五行(납음오행) 추가
  ✅ 形(형)/害(해) 분석 추가
  ✅ 公望(공망) 계산 추가
  ✅ 月令(월령) 판정 추가
  ✅ 小限(소한)/世運(세운) 추가
  ✅ 格局(격국) 자동 판별 추가
  ✅ 인생영역별 분석 (배우자운, 재운, 직업운) 추가
"""

import streamlit as st
import math
import datetime
import json

import report_pipeline
import pdf_report

try:
    from korean_lunar_calendar import KoreanLunarCalendar
    LUNAR_CALENDAR_AVAILABLE = True
except ImportError:
    LUNAR_CALENDAR_AVAILABLE = False

from SAJU_ENHANCEMENT_ADDITIONS import (
    get_naeum_ohaeng, check_xing_hae, calculate_gongmang,
    classify_deukryeong, get_season_multipliers, analyze_johu_yongshin, analyze_tonggwan_yongshin,
    analyze_marriage_luck, analyze_wealth_luck, analyze_career_luck,
    check_dohwasal, check_yanginsal, check_goegangsal, check_cheoneul_gwiin, check_munchang_gwiin, check_wonjinsal
)

STEMS_LIST = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']
BRANCHES_LIST = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']

GANJI_60 = []
for i in range(60):
    GANJI_60.append(STEMS_LIST[i % 10] + BRANCHES_LIST[i % 12])

MONTH_BRANCHES = ['寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥', '子', '丑']

# ============================================================================
# 출생 도시별 경도 시차 보정표(분 단위) - 표준 경도 135°E(동경 135도) 기준
# (도시 경도 - 135) / 15 * 60 을 반올림한 값. "시" 단위 도시까지만 지원.
# ============================================================================
CITY_LONGITUDE_OFFSETS = {
    "서울특별시": -32, "부산광역시": -24, "대구광역시": -26, "인천광역시": -33,
    "광주광역시": -33, "대전광역시": -30, "울산광역시": -23, "세종특별자치시": -31,
    "수원시": -32, "성남시": -31, "의정부시": -32, "안양시": -32, "부천시": -33,
    "광명시": -33, "평택시": -32, "동두천시": -32, "안산시": -33, "고양시": -33,
    "과천시": -32, "구리시": -31, "남양주시": -31, "오산시": -32, "시흥시": -33,
    "군포시": -32, "의왕시": -32, "하남시": -31, "용인시": -31, "파주시": -33,
    "이천시": -30, "안성시": -31, "김포시": -33, "화성시": -33, "광주시(경기)": -31,
    "양주시": -32, "포천시": -31, "여주시": -29,
    "춘천시": -29, "원주시": -28, "강릉시": -24, "동해시": -24, "태백시": -24,
    "속초시": -26, "삼척시": -23,
    "청주시": -30, "충주시": -28, "제천시": -27,
    "천안시": -31, "공주시": -32, "보령시": -34, "아산시": -32, "서산시": -34,
    "논산시": -32, "계룡시": -31, "당진시": -33,
    "전주시": -31, "군산시": -33, "익산시": -32, "정읍시": -33, "남원시": -30,
    "김제시": -32,
    "목포시": -34, "여수시": -29, "순천시": -30, "나주시": -33, "광양시": -29,
    "포항시": -23, "경주시": -23, "김천시": -28, "안동시": -25, "구미시": -27,
    "영주시": -26, "영천시": -24, "상주시": -27, "문경시": -27, "경산시": -25,
    "창원시": -25, "진주시": -28, "통영시": -26, "사천시": -28, "김해시": -24,
    "밀양시": -25, "거제시": -26, "양산시": -24,
    "제주시": -34, "서귀포시": -34,
    "보정 없음 (표준시 그대로 0분)": 0,
}

# ============================================================================
# 납음오행 / 형·해 관계는 SAJU_ENHANCEMENT_ADDITIONS 모듈에서 가져와 사용합니다.
# (60갑자 전체 매핑 + 정확도 검증은 해당 모듈 참고)
# ============================================================================
STEM_INFO = {
    '甲': {'element': '木', 'polarity': '陽', 'name': '갑목(甲木)', 'desc': '하늘로 곧게 뻗은 아름드리 큰 나무로, 진취적이고 책임감이 강한 리더의 기상입니다.'},
    '乙': {'element': '木', 'polarity': '陰', 'name': '을목(乙木)', 'desc': '유연하고 질긴 생명력을 지닌 화초나 넝쿨식물로, 환경 적응력이 뛰어나고 예술적 감각이 돋보입니다.'},
    '丙': {'element': '火', 'polarity': '陽', 'name': '병화(丙火)', 'desc': '만물을 골고루 비추는 뜨거운 태양으로, 열정적이고 사교적이며 성격이 솔직담백합니다.'},
    '丁': {'element': '火', 'polarity': '陰', 'name': '정화(丁火)', 'desc': '어둠을 밝히는 은은한 등불이나 별빛으로, 온화하고 예의가 바르며 내적인 집중력과 탐구심이 강합니다.'},
    '戊': {'element': '土', 'polarity': '陽', 'name': '무토(戊土)', 'desc': '드넓은 대지나 우직한 산맥으로, 포용력이 깊고 신용이 두터우며 듬직하고 신중합니다.'},
    '己': {'element': '土', 'polarity': '陰', 'name': '기토(己土)', 'desc': '새싹을 키워내는 비옥한 논밭이나 정원으로, 섬세하고 따뜻하며 실리적이고 계획성이 뛰어납니다.'},
    '庚': {'element': '金', 'polarity': '陽', 'name': '경금(庚金)', 'desc': '정제되지 않은 원석이나 단단한 무쇠로, 의리가 깊고 결단력이 뛰어나며 과감한 추진력을 가집니다.'},
    '辛': {'element': '金', 'polarity': '陰', 'name': '신금(辛金)', 'desc': '정교하게 다듬어진 값진 보석이나 칼날로, 예리하고 철저하며 자존심이 세고 세심한 완벽주의자입니다.'},
    '壬': {'element': '水', 'polarity': '陽', 'name': '임수(壬水)', 'desc': '모든 것을 품는 도도한 바다나 거대한 강물로, 통찰력이 깊고 지혜로우며 큰 흐름을 읽는 스케일을 지녔습니다.'},
    '癸': {'element': '水', 'polarity': '陰', 'name': '계수(癸水)', 'desc': '대지를 조용히 적시는 단비나 맑은 샘물로, 총명하고 사려가 깊으며 창의적인 아이디어와 유연성이 뛰어납니다.'}
}

BRANCH_INFO = {
    '子': {'element': '水', 'polarity': '陰', 'jijanggan': {'壬': 10, '癸': 20}, 'k_name': '자수(子水)', 'animal': '쥐', 'desc': '생각이 깊고 지혜를 품은 기운'},
    '丑': {'element': '土', 'polarity': '陰', 'jijanggan': {'癸': 9, '辛': 3, '己': 18}, 'k_name': '축토(丑土)', 'animal': '소', 'desc': '성실하고 끈기 있게 결실을 준비하는 기운'},
    '寅': {'element': '木', 'polarity': '陽', 'jijanggan': {'戊': 7, '丙': 7, '甲': 16}, 'k_name': '인목(寅木)', 'animal': '호랑이', 'desc': '강한 솟구침과 시작을 이끄는 개척의 기운'},
    '卯': {'element': '木', 'polarity': '陽', 'jijanggan': {'甲': 10, '乙': 20}, 'k_name': '묘목(卯木)', 'animal': '토끼', 'desc': '섬세함과 생동하는 직관력을 품은 기운'},
    '辰': {'element': '土', 'polarity': '陽', 'jijanggan': {'乙': 9, '癸': 3, '戊': 18}, 'k_name': '진토(辰土)', 'animal': '용', 'desc': '무궁무진한 변화와 넓은 포부를 품은 기운'},
    '巳': {'element': '火', 'polarity': '陰', 'jijanggan': {'戊': 7, '庚': 7, '丙': 16}, 'k_name': '사화(巳火)', 'animal': '뱀', 'desc': '밝고 화려하게 뻗어나가는 표현력의 기운'},
    '午': {'element': '火', 'polarity': '陽', 'jijanggan': {'丙': 10, '己': 9, '丁': 11}, 'k_name': '오화(午火)', 'animal': '말', 'desc': '정열적이고 거침없이 질주하는 심장의 기운'},
    '未': {'element': '土', 'polarity': '陰', 'jijanggan': {'丁': 9, '乙': 3, '己': 18}, 'k_name': '미토(未土)', 'animal': '양', 'desc': '묵묵한 인내심과 따스함을 품은 완숙의 기운'},
    '申': {'element': '金', 'polarity': '陽', 'jijanggan': {'戊': 7, '壬': 7, '庚': 16}, 'k_name': '신금(申金)', 'animal': '원숭이', 'desc': '재주가 다채롭고 현실 감각이 뛰어난 기운'},
    '酉': {'element': '金', 'polarity': '陰', 'jijanggan': {'庚': 10, '辛': 20}, 'k_name': '유금(酉金)', 'animal': '닭', 'desc': '칼날 같은 판단력과 깔끔함을 품은 결실의 기운'},
    '戌': {'element': '土', 'polarity': '陽', 'jijanggan': {'辛': 9, '丁': 3, '戊': 18}, 'k_name': '술토(戌土)', 'animal': '개', 'desc': '신뢰를 중시하고 책임감 있게 가두는 기운'},
    '亥': {'element': '水', 'polarity': '陽', 'jijanggan': {'戊': 7, '甲': 7, '壬': 16}, 'k_name': '해수(亥水)', 'animal': '돼지', 'desc': '바다처럼 통찰하고 수렴하는 생명의 기운'}
}

# [기본 데이터 유지]
RELATION_MAP = {
    ('木', '木'): '비겁', ('木', '火'): '식상', ('木', '土'): '재성', ('木', '金'): '관성', ('木', '水'): '인성',
    ('火', '火'): '비겁', ('火', '土'): '식상', ('火', '金'): '재성', ('火', '水'): '관성', ('火', '木'): '인성',
    ('土', '土'): '비겁', ('土', '金'): '식상', ('土', '水'): '재성', ('土', '木'): '관성', ('土', '火'): '인성',
    ('金', '金'): '비겁', ('金', '水'): '식상', ('金', '木'): '재성', ('金', '火'): '관성', ('金', '土'): '인성',
    ('水', '水'): '비겁', ('水', '木'): '식상', ('水', '火'): '재성', ('水', '土'): '관성', ('水', '金'): '인성'
}

STEM_COMBINATIONS = {
    ('甲', '己'): '土', ('己', '甲'): '土', ('乙', '庚'): '金', ('庚', '乙'): '金',
    ('丙', '辛'): '水', ('辛', '丙'): '水', ('丁', '壬'): '木', ('壬', '丁'): '木',
    ('戊', '癸'): '火', ('癸', '戊'): '火'
}

BRANCH_SIX_COMBINATIONS = {
    ('子', '丑'): '土', ('丑', '子'): '土', ('寅', '亥'): '木', ('亥', '寅'): '木',
    ('卯', '戌'): '火', ('戌', '卯'): '火', ('辰', '酉'): '金', ('酉', '辰'): '金',
    ('巳', '申'): '水', ('申', '巳'): '水', ('午', '未'): '火', ('未', '午'): '火'
}

BRANCH_THREE_COMBINATIONS = {
    frozenset(['申', '子', '辰']): {'target': '水', 'name': '신자진(申子辰) 삼합水'},
    frozenset(['亥', '卯', '未']): {'target': '木', 'name': '해묘미(亥卯未) 삼합木'},
    frozenset(['寅', '午', '戌']): {'target': '火', 'name': '인오술(寅午戌) 삼합火'},
    frozenset(['巳', '酉', '丑']): {'target': '金', 'name': '사유축(巳酉丑) 삼합金'}
}

BRANCH_HALF_COMBINATIONS = {
    frozenset(['申', '子']): {'target': '水', 'name': '신자(申子) 반합수'},
    frozenset(['子', '辰']): {'target': '水', 'name': '자진(子辰) 반합수'},
    frozenset(['亥', '卯']): {'target': '木', 'name': '해묘(亥卯) 반합목'},
    frozenset(['卯', '未']): {'target': '木', 'name': '묘미(卯未) 반합목'},
    frozenset(['寅', '午']): {'target': '火', 'name': '인오(寅午) 반합화'},
    frozenset(['午', '戌']): {'target': '火', 'name': '오술(午戌) 반합화'},
    frozenset(['巳', '酉']): {'target': '金', 'name': '사유(巳酉) 반합금'},
    frozenset(['酉', '丑']): {'target': '金', 'name': '유축(酉丑) 반합금'}
}

BRANCH_CLASHES = {
    ('子', '午'): '자오(子午) 충', ('午', '子'): '자오(子午) 충',
    ('丑', '未'): '축미(丑未) 충', ('未', '丑'): '축미(丑未) 충',
    ('寅', '申'): '인신(寅申) 충', ('申', '寅'): '인신(寅申) 충',
    ('卯', '酉'): '묘유(卯酉) 충', ('酉', '卯'): '묘유(卯酉) 충',
    ('辰', '戌'): '진술(辰戌) 충', ('戌', '辰'): '진술(辰戌) 충',
    ('巳', '亥'): '사해(巳亥) 충', ('亥', '巳'): '사해(巳亥) 충'
}

UNSEONG_MAP = {
    '甲': {'亥': '장생', '子': '목욕', '丑': '관대', '寅': '건록', '卯': '제왕', '辰': '쇠', '巳': '병', '午': '사', '未': '묘', '申': '절', '酉': '태', '戌': '양'},
    '乙': {'午': '장생', '巳': '목욕', '辰': '관대', '卯': '건록', '寅': '제왕', '丑': '쇠', '子': '병', '亥': '사', '戌': '묘', '酉': '절', '申': '태', '未': '양'},
    '丙': {'寅': '장생', '卯': '목욕', '辰': '관대', '巳': '건록', '午': '제왕', '未': '쇠', '申': '병', '酉': '사', '戌': '묘', '亥': '절', '子': '태', '丑': '양'},
    '丁': {'酉': '장생', '申': '목욕', '未': '관대', '午': '건록', '巳': '제왕', '辰': '쇠', '卯': '병', '寅': '사', '丑': '묘', '子': '절', '亥': '태', '戌': '양'},
    '戊': {'寅': '장생', '卯': '목욕', '辰': '관대', '巳': '건록', '午': '제왕', '未': '쇠', '申': '병', '酉': '사', '戌': '묘', '亥': '절', '子': '태', '丑': '양'},
    '己': {'酉': '장생', '申': '목욕', '未': '관대', '午': '건록', '巳': '제왕', '辰': '쇠', '卯': '병', '寅': '사', '丑': '묘', '子': '절', '亥': '태', '戌': '양'},
    '庚': {'巳': '장생', '午': '목욕', '未': '관대', '申': '건록', '酉': '제왕', '戌': '쇠', '亥': '병', '子': '사', '丑': '묘', '寅': '절', '卯': '태', '辰': '양'},
    '辛': {'子': '장생', '亥': '목욕', '戌': '관대', '酉': '건록', '申': '제왕', '未': '쇠', '午': '병', '巳': '사', '辰': '묘', '卯': '절', '寅': '태', '丑': '양'},
    '壬': {'申': '장생', '酉': '목욕', '戌': '관대', '亥': '건록', '子': '제왕', '丑': '쇠', '寅': '병', '卯': '사', '辰': '묘', '巳': '절', '午': '태', '未': '양'},
    '癸': {'卯': '장생', '寅': '목욕', '丑': '관대', '子': '건록', '亥': '제왕', '戌': '쇠', '酉': '병', '申': '사', '未': '묘', '午': '절', '巳': '태', '辰': '양'}
}

# ============================================================================
# 기본 함수들 (기존과 동일)
# ============================================================================
def get_julian_day_tz(year, month, day, hour=12, minute=0, timezone_offset_hours=9.0):
    local_dt = datetime.datetime(year, month, day, hour, minute)
    utc_dt = local_dt - datetime.timedelta(hours=timezone_offset_hours)
    
    y, m, d = utc_dt.year, utc_dt.month, utc_dt.day
    h, mn = utc_dt.hour, utc_dt.minute
    
    if m <= 2:
        y -= 1
        m += 12
    A = math.floor(y / 100)
    B = 2 - A + math.floor(A / 4)
    jd = math.floor(365.25 * (y + 4716)) + math.floor(30.6001 * (m + 1)) + d + B - 1524.5
    jd += (h + mn / 60.0) / 24.0
    return jd

def get_solar_longitude(jd):
    T = (jd - 2451545.0) / 36525.0
    L0 = 280.46646 + 36000.76983 * T + 0.0003032 * T * T
    M = 357.52911 + 35999.05029 * T - 0.0001537 * T * T
    M_rad = math.radians(M % 360.0)
    
    C = (1.914602 - 0.004817 * T - 0.000014 * T * T) * math.sin(M_rad) + \
        (0.019993 - 0.000101 * T) * math.sin(2 * M_rad) + \
        0.000289 * math.sin(3 * M_rad)
        
    true_lon = (L0 + C) % 360.0
    return true_lon

def get_equation_of_time_minutes(jd):
    """
    균시차(均時差, Equation of Time) - 평균태양시와 진태양시의 차이를 분 단위로 반환.
    진태양시 = 평균태양시(경도 보정 시각) + 이 값.
    Meeus, 'Astronomical Algorithms' 28장의 근사식 (오차 수 초 이내).
    """
    T = (jd - 2451545.0) / 36525.0
    L0 = math.radians((280.46646 + 36000.76983 * T + 0.0003032 * T * T) % 360.0)
    M = math.radians((357.52911 + 35999.05029 * T - 0.0001537 * T * T) % 360.0)
    e = 0.016708634 - 0.000042037 * T - 0.0000001267 * T * T
    eps = math.radians(23.439291 - 0.0130042 * T - 0.00000016 * T * T)
    y = math.tan(eps / 2.0) ** 2

    E = (y * math.sin(2 * L0)
         - 2 * e * math.sin(M)
         + 4 * e * y * math.sin(M) * math.cos(2 * L0)
         - 0.5 * y * y * math.sin(4 * L0)
         - 1.25 * e * e * math.sin(2 * M))

    return math.degrees(E) * 4.0  # 1도 = 4분(시간)

SOLAR_TERMS_CONFIG = {
    315: (2, 4), 330: (2, 19), 345: (3, 5), 0: (3, 20), 15: (4, 5), 30: (4, 20),
    45: (5, 5), 60: (5, 20), 75: (6, 5), 90: (6, 21), 105: (7, 7), 120: (7, 23),
    135: (8, 7), 150: (8, 23), 165: (9, 7), 180: (9, 23), 195: (10, 8), 210: (10, 23),
    225: (11, 7), 240: (11, 22), 255: (12, 7), 270: (12, 21), 285: (1, 5), 300: (1, 20)
}

def find_solar_term_time(year, target_longitude):
    month, day = SOLAR_TERMS_CONFIG[target_longitude]
    start_jd = get_julian_day_tz(year, month, day, 12, 0, 9.0)
    
    low = start_jd - 4.0
    high = start_jd + 4.0
    
    for _ in range(50):
        mid = (low + high) / 2.0
        lon = get_solar_longitude(mid)
        diff = (lon - target_longitude + 180.0) % 360.0 - 180.0
        if diff < 0:
            low = mid
        else:
            high = mid
            
    return (low + high) / 2.0

def get_dst_offset_minutes(year, month, day, hour, minute):
    if hour is None:
        return 0
    dt = datetime.datetime(year, month, day, hour, minute)
    if year == 1948 and datetime.datetime(1948, 5, 1) <= dt <= datetime.datetime(1948, 9, 13, 0, 0): return 60
    if year == 1949 and datetime.datetime(1949, 4, 3) <= dt <= datetime.datetime(1949, 10, 2, 0, 0): return 60
    if year == 1950 and datetime.datetime(1950, 4, 1) <= dt <= datetime.datetime(1950, 9, 10, 0, 0): return 60
    if year == 1951 and datetime.datetime(1951, 5, 6) <= dt <= datetime.datetime(1951, 9, 9, 0, 0): return 60
    if year == 1955 and datetime.datetime(1955, 5, 5) <= dt <= datetime.datetime(1955, 9, 11, 0, 0): return 60
    if year == 1956 and datetime.datetime(1956, 5, 5) <= dt <= datetime.datetime(1956, 9, 11, 0, 0): return 60
    if year == 1957 and datetime.datetime(1957, 5, 5) <= dt <= datetime.datetime(1957, 9, 22, 0, 0): return 60
    if year == 1958 and datetime.datetime(1958, 5, 4) <= dt <= datetime.datetime(1958, 9, 21, 0, 0): return 60
    if year == 1959 and datetime.datetime(1959, 5, 3) <= dt <= datetime.datetime(1959, 9, 20, 0, 0): return 60
    if year == 1960 and datetime.datetime(1960, 5, 1) <= dt <= datetime.datetime(1960, 9, 18, 0, 0): return 60
    if year == 1987 and datetime.datetime(1987, 5, 10) <= dt <= datetime.datetime(1987, 10, 11, 0, 0): return 60
    if year == 1988 and datetime.datetime(1988, 5, 8) <= dt <= datetime.datetime(1988, 10, 9, 0, 0): return 60
    return 0

def determine_ten_deity(me_stem, target_char, is_branch=False):
    me_elem = STEM_INFO[me_stem]['element']
    me_pol = STEM_INFO[me_stem]['polarity']
    
    if is_branch:
        target_info = BRANCH_INFO[target_char]
    else:
        target_info = STEM_INFO[target_char]
        
    target_elem = target_info['element']
    target_pol = target_info['polarity']
    
    relation = RELATION_MAP[(me_elem, target_elem)]
    same_polarity = (me_pol == target_pol)
    
    if relation == '비겁':
        return '비견' if same_polarity else '겁재'
    elif relation == '식상':
        return '식신' if same_polarity else '상관'
    elif relation == '재성':
        return '편재' if same_polarity else '정재'
    elif relation == '관성':
        return '편관' if same_polarity else '정관'
    elif relation == '인성':
        return '편인' if same_polarity else '정인'
    
    return '미상'

def get_sinsal(base_branch, target_branch):
    if base_branch in ['申', '子', '辰']:
        start_idx = 8
    elif base_branch in ['巳', '酉', '丑']:
        start_idx = 5
    elif base_branch in ['寅', '午', '戌']:
        start_idx = 2
    else:
        start_idx = 11
        
    target_idx = BRANCHES_LIST.index(target_branch)
    sinsal_list = ['지살', '년살', '월살', '망신살', '장성살', '반안살', '역마살', '육해살', '화개살', '겁살', '재살', '천살']
    idx = (target_idx - start_idx) % 12
    return sinsal_list[idx]

def get_historical_kst_correction_minutes(year, month, day):
    """
    한국 표준시(KST)는 시대에 따라 여러 차례 바뀌었다. 이 프로그램의 모든 계산은
    현재 표준시(UTC+9)를 기준으로 하므로, 다른 표준시를 쓰던 시대에 태어난 사람은
    시계가 실제로 가리키던 시각을 UTC+9 기준으로 환산해주는 보정이 필요하다.
      - 1908-04-01 ~ 1911-12-31: 대한제국 표준시 UTC+8:30 (현재보다 30분 느림)
      - 1954-03-21 ~ 1961-08-09: 대한민국 표준시 UTC+8:30 (현재보다 30분 느림)
      - 그 외 기간(1912~1954, 1961~현재): 지금과 같은 UTC+9 → 보정 없음
    """
    dt = datetime.date(year, month, day)
    if datetime.date(1908, 4, 1) <= dt <= datetime.date(1911, 12, 31):
        return 30
    if datetime.date(1954, 3, 21) <= dt <= datetime.date(1961, 8, 9):
        return 30
    return 0

def convert_to_pillars(year, month, day, hour=None, minute=0, is_lunar=False, is_leap=False, sex="남성", time_boundary="선택 안 함(기본)", region_offset_mins=0, dst_offset_mins=0):
    solar_year, solar_month, solar_day = year, month, day
    if is_lunar:
        if not LUNAR_CALENDAR_AVAILABLE:
            raise RuntimeError(
                "음력 변환에 필요한 'korean_lunar_calendar' 패키지가 설치되어 있지 않습니다. "
                "'pip install korean_lunar_calendar'로 설치한 뒤 다시 시도해주세요."
            )
        lunar_conv = KoreanLunarCalendar()
        try:
            lunar_conv.setLunarDate(year, month, day, is_leap)
        except Exception as e:
            raise ValueError(f"입력하신 음력 날짜({year}-{month}-{day}, 윤달={is_leap})가 유효하지 않습니다: {e}")
        solar_year, solar_month, solar_day = lunar_conv.solarYear, lunar_conv.solarMonth, lunar_conv.solarDay

    h_val = hour if hour is not None else 12

    # 서머타임 기간에는 시계가 표준시(KST)보다 1시간 앞서 있고, 1954~1961년 등 과거 한국
    # 표준시가 UTC+8:30이던 시기는 지금(UTC+9)보다 시계가 30분 느리므로, 절기 판정(연주/
    # 월주/대운)에 쓰이는 birth_jd는 이 두 보정을 모두 반영한 '현재 기준 표준시'로 계산해야 한다.
    historical_kst_correction_mins = get_historical_kst_correction_minutes(solar_year, solar_month, solar_day)
    _civil_dt = datetime.datetime(solar_year, solar_month, solar_day, h_val, minute)
    _std_kst_dt = _civil_dt - datetime.timedelta(minutes=dst_offset_mins) + datetime.timedelta(minutes=historical_kst_correction_mins)
    birth_jd = get_julian_day_tz(_std_kst_dt.year, _std_kst_dt.month, _std_kst_dt.day, _std_kst_dt.hour, _std_kst_dt.minute, 9.0)

    ipchun_jd = find_solar_term_time(solar_year, 315)
    saju_year = solar_year
    if birth_jd < ipchun_jd:
        saju_year = solar_year - 1
        
    year_diff = saju_year - 4
    year_stem = STEMS_LIST[year_diff % 10]
    year_branch = BRANCHES_LIST[year_diff % 12]
    
    jeolgi_longitudes = [315, 345, 15, 45, 75, 105, 135, 165, 195, 225, 255, 285]
    jeolgi_jds = []
    for lon in jeolgi_longitudes:
        # 285도(소한)는 입춘 기준 saju_year의 "다음 해" 1월에 오는 절기이므로 saju_year+1로 계산해야
        # jeolgi_jds가 시간순으로 단조 증가한다 (대설(255) 이후에 와야 함).
        term_year = saju_year + 1 if lon == 285 else saju_year
        jeolgi_jds.append(find_solar_term_time(term_year, lon))

    next_ipchun_jd = find_solar_term_time(saju_year + 1, 315)
    
    month_idx = -1
    if birth_jd < jeolgi_jds[0]: 
        month_idx = 11 
    else:
        for m in range(11):
            if jeolgi_jds[m] <= birth_jd < jeolgi_jds[m+1]:
                month_idx = m
                break
        if month_idx == -1:
            if jeolgi_jds[11] <= birth_jd < next_ipchun_jd:
                month_idx = 11
                
    year_stem_idx = year_diff % 10
    month_base_stem_idx = (year_stem_idx % 5 * 2 + 2) % 10
    month_stem_idx = (month_base_stem_idx + month_idx) % 10
    month_stem = STEMS_LIST[month_stem_idx]
    month_branch = MONTH_BRANCHES[month_idx]
    
    standard_dt = datetime.datetime(solar_year, solar_month, solar_day, h_val, minute)
    # 진태양시(眞太陽時) = 표준시 - 서머타임 + 과거 표준시 보정 + 경도 시차 + 균시차
    eot_minutes = get_equation_of_time_minutes(birth_jd)
    total_offset_mins = region_offset_mins - dst_offset_mins + historical_kst_correction_mins + eot_minutes
    lst_dt = standard_dt + datetime.timedelta(minutes=total_offset_mins)
    
    lst_year = lst_dt.year
    lst_month = lst_dt.month
    lst_day = lst_dt.day
    lst_hour = lst_dt.hour
    lst_minute = lst_dt.minute
    
    base_date = datetime.date(1950, 1, 1)
    birth_date_lst = datetime.date(lst_year, lst_month, lst_day)
    
    is_next_day = False
    tot_min_lst = lst_hour * 60 + lst_minute
    if hour is not None:
        if time_boundary == "선택 안 함(기본)":
            if tot_min_lst >= 1380:
                is_next_day = True
        elif time_boundary == "조자시 적용 (00:00~00:30)":
            if tot_min_lst >= 1380:
                is_next_day = True
        elif time_boundary == "야자시 적용 (23:30~24:00)":
            is_next_day = False
            
    if is_next_day:
        birth_date_lst += datetime.timedelta(days=1)
        
    days_diff = (birth_date_lst - base_date).days
    day_idx = (32 + days_diff) % 60
    day_stem = STEMS_LIST[day_idx % 10]
    day_branch = BRANCHES_LIST[day_idx % 12]
    
    if hour is None:
        hour_p = None
    else:
        if tot_min_lst >= 1380 or tot_min_lst < 60:
            h_idx = 0  
        elif tot_min_lst < 180:
            h_idx = 1  
        elif tot_min_lst < 300:
            h_idx = 2  
        elif tot_min_lst < 420:
            h_idx = 3  
        elif tot_min_lst < 540:
            h_idx = 4  
        elif tot_min_lst < 660:
            h_idx = 5  
        elif tot_min_lst < 780:
            h_idx = 6  
        elif tot_min_lst < 900:
            h_idx = 7  
        elif tot_min_lst < 1020:
            h_idx = 8  
        elif tot_min_lst < 1140:
            h_idx = 9  
        elif tot_min_lst < 1260:
            h_idx = 10 
        else:
            h_idx = 11 
            
        day_stem_idx = day_idx % 10
        hour_base_stem_idx = (day_stem_idx % 5 * 2) % 10
        hour_stem_idx = (hour_base_stem_idx + h_idx) % 10
        hour_stem = STEMS_LIST[hour_stem_idx]
        hour_branch = BRANCHES_LIST[h_idx]
        hour_p = (hour_stem, hour_branch)
        
    is_yang_year = (year_diff % 2 == 0) 
    is_forward = (is_yang_year == (sex == "남성"))
    
    if is_forward:
        next_term_jd = None
        for jd in jeolgi_jds:
            if jd > birth_jd:
                next_term_jd = jd
                break
        if next_term_jd is None:
            next_term_jd = next_ipchun_jd
        jd_diff = next_term_jd - birth_jd
    else:
        prev_term_jd = None
        for jd in reversed(jeolgi_jds):
            if jd < birth_jd:
                prev_term_jd = jd
                break
        if prev_term_jd is None:
            prev_term_jd = find_solar_term_time(saju_year - 1, 285)
        jd_diff = birth_jd - prev_term_jd
        
    daewoon_num = max(1, round(jd_diff / 3.0)) 
    
    daewoon_pillars = []
    month_pillar_idx = GANJI_60.index(month_stem + month_branch)
    for i in range(1, 11):
        step = i if is_forward else -i
        p_idx = (month_pillar_idx + step) % 60
        pillar_str = GANJI_60[p_idx]
        daewoon_pillars.append((daewoon_num + (i-1)*10, pillar_str[0], pillar_str[1]))
        
    return (year_stem, year_branch), (month_stem, month_branch), (day_stem, day_branch), hour_p, daewoon_num, daewoon_pillars, is_forward, lst_dt

# ============================================================================
# 납음오행 / 형·해 / 격국 / 공망 / 월령 / 배우자운·재운·직업운 함수는
# SAJU_ENHANCEMENT_ADDITIONS 모듈에서 import 하여 사용합니다 (상단 import 참고).
# ============================================================================

def get_year_ganji(year):
    """연도(서기) → 세운(歲運)에 쓰이는 그 해의 년주(年柱) 간지"""
    year_diff = year - 4
    return STEMS_LIST[year_diff % 10], BRANCHES_LIST[year_diff % 12]

# ============================================================================
# 격국(格局) 판별 - 월지(月支) 지장간의 정기(正氣) 기준 (정통 방식)
# ============================================================================
_GUCKGUK_BY_SIPSIN = {
    '식신': ('식신격(食神格)', '식신이 월지 정기에 드러나 표현력과 창의력, 여유로움이 돋보이는 귀한 격국입니다.'),
    '상관': ('상관격(傷官格)', '상관이 월지 정기에 드러나 재능과 자유로운 기질이 두드러지는 격국. 조직생활보다 전문성이 유리합니다.'),
    '편재': ('편재격(偏財格)', '편재가 월지 정기에 드러나는 격국. 기회를 잘 살피고 변화에 강하며 사업 수완이 돋보입니다.'),
    '정재': ('정재격(正財格)', '정재가 월지 정기에 드러나는 귀한 격국. 현실적이고 착실하게 재물을 쌓아가는 기운입니다.'),
    '편관': ('편관격(偏官格)', '편관(칠살)이 월지 정기에서 왕성하게 드러나는 격국. 추진력과 리더십이 강합니다.'),
    '정관': ('정관격(正官格)', '정관이 월지 정기에서 강하게 드러나는 귀한 격국. 공직·조직생활에 유리하고 신용을 중시합니다.'),
    '편인': ('편인격(偏印格)', '편인이 월지 정기에 드러나는 격국. 직관과 독창성이 강조되고 특수 분야에서 두각을 나타냅니다.'),
    '정인': ('정인격(正印格)', '정인이 월지 정기에 자리한 귀한 격국. 학문과 명예를 중시하며 문서·교육운이 좋습니다.'),
}


def determine_guckguk_by_wolji(day_master, month_branch):
    """
    격국(格局) 판별 - 월지(月支) 지장간 중 정기(正氣, 배정 일수가 가장 큰 지장간)를
    기준으로 판별하는 정통 방식. (기존의 월간 십신 기준 간이 방식보다 정확함)
    """
    jijanggan = BRANCH_INFO[month_branch]['jijanggan']
    jeonggi_stem = max(jijanggan.items(), key=lambda x: x[1])[0]
    sipsin = determine_ten_deity(day_master, jeonggi_stem, is_branch=False)

    if sipsin in _GUCKGUK_BY_SIPSIN:
        name, desc = _GUCKGUK_BY_SIPSIN[sipsin]
        return {'name': name, 'desc': desc, 'jeonggi_stem': jeonggi_stem, 'sipsin': sipsin}

    # 비견/겁재는 격의 대상신으로 삼지 않는 것이 정석이라 건록격/양인격/월겁격으로 별도 처리
    is_yang_stem = STEM_INFO[day_master]['polarity'] == '陽'
    if sipsin == '비견':
        return {
            'name': '건록격(建祿格)',
            'desc': '월지 정기가 일간과 같은 비견(比肩)으로 드러나 자립심과 독립심이 강한 격국. 스스로의 힘으로 성취하는 자수성가형입니다.',
            'jeonggi_stem': jeonggi_stem, 'sipsin': sipsin,
        }
    if is_yang_stem:
        return {
            'name': '양인격(陽刃格)',
            'desc': '월지 정기가 겁재(劫財)로 드러나고 일간이 양간이라 기세가 매우 강한 격국. 추진력과 승부욕이 극대화되지만 재물·인간관계 다툼에 유의해야 합니다.',
            'jeonggi_stem': jeonggi_stem, 'sipsin': sipsin,
        }
    return {
        'name': '월겁격(月劫格)',
        'desc': '월지 정기가 겁재(劫財)로 드러나는 격국. 경쟁심과 독립심이 강하며, 비겁의 도움을 받아 활동하는 기운입니다.',
        'jeonggi_stem': jeonggi_stem, 'sipsin': sipsin,
    }

# ============================================================================
# [IMPORTANT] 향상된 AdvancedSajuAnalyzer 클래스
# ============================================================================

class AdvancedSajuAnalyzer:
    def __init__(self, name, sex, year_pillar, month_pillar, day_pillar, hour_pillar, daewoon_num, daewoon_pillars, birth_date=None, profile=None):
        self.name = name
        self.sex = sex
        self.year = year_pillar
        self.month = month_pillar
        self.day = day_pillar
        self.hour = hour_pillar
        self.daewoon_num = daewoon_num
        self.birth_date = birth_date
        self.daewoon_pillars = daewoon_pillars
        # 고객이 선택 입력한 혼인상태/자녀유무/직업상태/심층질문 (없으면 값이 None) —
        # 풀이 엔진이 서술 깊이·심층 질문 답변 여부를 판단하는 데만 쓰고, 계산에는 관여하지 않는다.
        self.profile = profile or {}
        
        self.day_master = day_pillar[0]
        
        self.stems = [self.year[0], self.month[0], self.day[0]]
        self.branches = [self.year[1], self.month[1], self.day[1]]
        if self.hour:
            self.stems.append(self.hour[0])
            self.branches.append(self.hour[1])
            
    def calculate_raw_element_scores(self):
        scores = {'木': 0.0, '火': 0.0, '土': 0.0, '金': 0.0, '水': 0.0}
        for stem in self.stems:
            elem = STEM_INFO[stem]['element']
            scores[elem] += 10.0
            
        for idx, branch in enumerate(self.branches):
            weight = 30.0 if idx == 1 else 10.0  
            jijanggan = BRANCH_INFO[branch]['jijanggan']
            total_days = sum(jijanggan.values())
            
            for stem_char, days in jijanggan.items():
                elem = STEM_INFO[stem_char]['element']
                distributed_score = weight * (days / total_days)
                scores[elem] += distributed_score
                
        for k in scores:
            scores[k] = round(scores[k], 2)
            
        return scores

    def detect_combinations_and_clashes(self):
        results = {
            'stem_combinations': [],
            'branch_three_comb': [],
            'branch_half_comb': [],
            'branch_six_comb': [],
            'branch_clashes': [],
            'xing_hae': []  # NEW
        }
        
        adjacent_stem_pairs = [('년간-월간', self.stems[0], self.stems[1]), ('월간-일간', self.stems[1], self.stems[2])]
        if self.hour:
            adjacent_stem_pairs.append(('일간-시간', self.stems[2], self.stems[3]))
            
        for name, s1, s2 in adjacent_stem_pairs:
            if (s1, s2) in STEM_COMBINATIONS:
                target = STEM_COMBINATIONS[(s1, s2)]
                results['stem_combinations'].append({
                    'pair': (s1, s2), 'position': name, 'target_element': target,
                    'desc': f"{name} {s1}·{s2} 합화{target}"
                })
                
        branches_set = set(self.branches)
        
        for comb_set, info in BRANCH_THREE_COMBINATIONS.items():
            if comb_set.issubset(branches_set):
                results['branch_three_comb'].append({
                    'combination': comb_set, 'target_element': info['target'], 'name': info['name'], 'desc': f"{info['name']}"
                })
                
        if not results['branch_three_comb']:
            for comb_set, info in BRANCH_HALF_COMBINATIONS.items():
                if comb_set.issubset(branches_set):
                    results['branch_half_comb'].append({
                        'combination': comb_set, 'target_element': info['target'], 'name': info['name'], 'desc': f"{info['name']}"
                    })
                    
        adjacent_branch_pairs = [('년지-월지', self.branches[0], self.branches[1]), ('월지-일지', self.branches[1], self.branches[2])]
        if self.hour:
            adjacent_branch_pairs.append(('일지-시지', self.branches[2], self.branches[3]))
            
        for name, b1, b2 in adjacent_branch_pairs:
            if (b1, b2) in BRANCH_SIX_COMBINATIONS:
                target = BRANCH_SIX_COMBINATIONS[(b1, b2)]
                results['branch_six_comb'].append({
                    'pair': (b1, b2), 'position': name, 'target_element': target, 'desc': f"{name} {b1}·{b2} 육합{target}"
                })
            
            # NEW: 형/해 관계 추가
            xing_hae = check_xing_hae(b1, b2)
            if xing_hae['exists']:
                results['xing_hae'].append({
                    'pair': (b1, b2), 'position': name, 'type': xing_hae['type'],
                    'name': xing_hae['name'], 'desc': f"{name} {xing_hae['name']} ({xing_hae['desc']})"
                })
                
        for name, b1, b2 in adjacent_branch_pairs:
            if (b1, b2) in BRANCH_CLASHES:
                clash_name = BRANCH_CLASHES[(b1, b2)]
                results['branch_clashes'].append({
                    'pair': (b1, b2), 'position': name, 'desc': f"{name} {clash_name} (강한 인접 충)"
                })
                
        return results

    def calculate_adjusted_element_scores(self, raw_scores, comb_results):
        adjusted = raw_scores.copy()
        shifts = []
        
        for comb in comb_results['branch_three_comb']:
            target_elem = comb['target_element']
            desc = comb['name']
            for b in comb['combination']:
                orig_elem = BRANCH_INFO[b]['element']
                if orig_elem != target_elem:
                    shift_amount = round(raw_scores[orig_elem] * 0.30, 2)
                    if adjusted[orig_elem] >= shift_amount:
                        adjusted[orig_elem] -= shift_amount
                        adjusted[target_elem] += shift_amount
                        shifts.append(f"삼합({desc}) 효과로 {orig_elem} 기운 {shift_amount}점이 {target_elem}(으)로 변형 흡수")

        if not comb_results['branch_three_comb']:
            for comb in comb_results['branch_half_comb']:
                target_elem = comb['target_element']
                desc = comb['name']
                for b in comb['combination']:
                    orig_elem = BRANCH_INFO[b]['element']
                    if orig_elem != target_elem:
                        shift_amount = round(raw_scores[orig_elem] * 0.15, 2)
                        if adjusted[orig_elem] >= shift_amount:
                            adjusted[orig_elem] -= shift_amount
                            adjusted[target_elem] += shift_amount
                            shifts.append(f"반합({desc}) 효과로 {orig_elem} 기운 {shift_amount}점이 {target_elem}(으)로 변형 흡수")

        for comb in comb_results['branch_six_comb']:
            target_elem = comb['target_element']
            pos = comb['position']
            for b in comb['pair']:
                orig_elem = BRANCH_INFO[b]['element']
                if orig_elem != target_elem:
                    shift_amount = round(raw_scores[orig_elem] * 0.15, 2)
                    if adjusted[orig_elem] >= shift_amount:
                        adjusted[orig_elem] -= shift_amount
                        adjusted[target_elem] += shift_amount
                        shifts.append(f"육합({pos} {b}) 효과로 {orig_elem} 기운 {shift_amount}점이 {target_elem}(으)로 변형 흡수")

        for k in adjusted:
            adjusted[k] = max(0.0, round(adjusted[k], 2))
            
        return adjusted, shifts

    def analyze_strength(self, scores):
        me_elem = STEM_INFO[self.day_master]['element']
        helpers = [me_elem]
        for other_elem in ['木', '火', '土', '金', '水']:
            if other_elem != me_elem:
                if RELATION_MAP.get((me_elem, other_elem)) == '인성':
                    helpers.append(other_elem)

        # 월령(月令) 왕상휴수사 반영: 태어난 계절에 따라 오행별 실질 힘을 가중치로 보정
        season_info = get_season_multipliers(self.month[1])
        weighted_scores = {elem: scores[elem] * season_info['multipliers'][elem] for elem in scores}

        total_score = sum(weighted_scores.values())
        helper_score = sum(weighted_scores[elem] for elem in helpers)
        helper_ratio = (helper_score / total_score) * 100 if total_score > 0 else 0

        if helper_ratio >= 45:
            strength = "신강(身强)"
        elif helper_ratio >= 35:
            strength = "중화(中和)"
        else:
            strength = "신약(身弱)"

        return {
            'strength': strength,
            'helper_score': helper_score,
            'helper_ratio': helper_ratio,
            'helper_elements': helpers,
            'season_info': season_info,
        }

    def determine_yongshin(self, adj_scores, strength_info):
        """억부용신(抑扶用神) - 신강/신약을 기준으로 한 용신 판정. 오행 한 글자를 반환."""
        me_elem = STEM_INFO[self.day_master]['element']
        helpers = strength_info['helper_elements']

        if strength_info['strength'] == "신약(身弱)":
            other_helpers = [h for h in helpers if h != me_elem]
            if other_helpers:
                if adj_scores[me_elem] > 0:
                    return me_elem
                else:
                    return other_helpers[0]
            return me_elem
        else:
            opponents = [e for e in ['木', '火', '土', '金', '水'] if e not in helpers]
            if opponents:
                return max(opponents, key=lambda x: adj_scores[x])
            return "土"

    def compute_all(self):
        """
        사주 분석에 필요한 모든 계산을 한 번에 수행해서 구조화된 dict로 반환한다.
        generate_detailed_report()(텍스트 리포트)와 카드형 화면 렌더러가 이 dict 하나를
        공유해서 쓰므로, 계산 로직은 여기 한 곳에만 있으면 된다.
        """
        raw_scores = self.calculate_raw_element_scores()
        comb_results = self.detect_combinations_and_clashes()
        adj_scores, shift_logs = self.calculate_adjusted_element_scores(raw_scores, comb_results)

        raw_strength = self.analyze_strength(raw_scores)
        adj_strength = self.analyze_strength(adj_scores)

        eokbu_elem = self.determine_yongshin(adj_scores, adj_strength)
        johu_info = analyze_johu_yongshin(self.month[1], adj_scores)
        tonggwan_info = analyze_tonggwan_yongshin(adj_scores)

        positions = ['년간', '년지', '월간', '월지', '일간(본인)', '일지']
        eight_chars_list = [
            (self.stems[0], False), (self.branches[0], True),
            (self.stems[1], False), (self.branches[1], True),
            (self.stems[2], False), (self.branches[2], True)
        ]
        if self.hour:
            positions.extend(['시간', '시지'])
            eight_chars_list.extend([(self.stems[3], False), (self.branches[3], True)])

        deities = {}
        unseong_list = []
        sinsal_list = []
        jijanggan_list = []

        for idx, (char, is_branch) in enumerate(eight_chars_list):
            pos = positions[idx]
            if idx == 4:
                deities[pos] = f"일간({char})"
                unseong_list.append("-")
                sinsal_list.append("-")
                jijanggan_list.append("-")
                continue

            deity = determine_ten_deity(self.day_master, char, is_branch)
            deities[pos] = f"{char}({deity})"

            if is_branch:
                unseong_val = UNSEONG_MAP[self.day_master].get(char, "-")
                unseong_list.append(unseong_val)
                if idx == 1:
                    sinsal_val = get_sinsal(self.branches[2], char)
                else:
                    sinsal_val = get_sinsal(self.branches[0], char)
                sinsal_list.append(sinsal_val)
                jijanggan_list.append(''.join(BRANCH_INFO[char]['jijanggan'].keys()))
            else:
                unseong_list.append("-")
                sinsal_list.append("-")
                jijanggan_list.append("-")

        # 격국 판별 (월지 지장간 정기 기준 - 정통 방식)
        month_deity = deities.get('월간', '')
        guckguk_info = determine_guckguk_by_wolji(self.day_master, self.month[1])

        # 배우자운/재운/직업운 - 계산은 항상 해두되(추후 사주풀이 단계에서 사용),
        # "사주 정보" 카드 화면에는 노출하지 않는다.
        marriage_info = analyze_marriage_luck(month_deity, adj_scores, self.sex)
        wealth_info = analyze_wealth_luck(self.day_master, adj_scores, adj_strength['strength'])
        career_info = analyze_career_luck(self.day_master, adj_scores)

        # 납음오행 (년주 기준, 60갑자 전체 지원)
        year_ganji = self.year[0] + self.year[1]
        naeum_info = get_naeum_ohaeng(year_ganji)

        # 공망(空亡) - 일주 기준으로 원국/대운에 걸리는 공망 지지를 함께 판정
        gongmang_info = calculate_gongmang(self.day[0], self.day[1])
        gongmang_branches = gongmang_info['branches']

        # 월령(月令) 득령/실령 - 일간의 월지 12운성을 기준으로 판정
        deukryeong_info = classify_deukryeong(UNSEONG_MAP[self.day_master].get(self.month[1], '-'))

        # 주요 신살(神殺) - 도화살/양인살/괴강살/천을귀인/문창귀인/원진살
        dohwasal_info = check_dohwasal(self.day[1], self.branches)
        yanginsal_info = check_yanginsal(self.day_master, UNSEONG_MAP, self.branches)
        goegangsal_info = check_goegangsal(self.day[0] + self.day[1])
        cheoneul_info = check_cheoneul_gwiin(self.day_master, self.branches)
        munchang_info = check_munchang_gwiin(self.day_master, self.branches)
        wonjinsal_list = check_wonjinsal(self.branches)

        # 세운(歲運) - 생년월일이 있을 때만 (현재 대운 + 향후 5년 유년운)
        saeyun = None
        if self.birth_date is not None:
            today = datetime.date.today()
            birth_year = self.birth_date.year
            current_age = today.year - birth_year + 1  # 세는나이 기준

            current_daewoon = None
            for age, stem, branch in self.daewoon_pillars:
                if age <= current_age < age + 10:
                    current_daewoon = (age, stem, branch)
                    break

            years = []
            for offset in range(5):
                target_year = today.year + offset
                y_stem, y_branch = get_year_ganji(target_year)
                years.append({
                    'year': target_year, 'offset': offset, 'stem': y_stem, 'branch': y_branch,
                    'sipsin_stem': determine_ten_deity(self.day_master, y_stem, False),
                    'sipsin_branch': determine_ten_deity(self.day_master, y_branch, True),
                    'unseong': UNSEONG_MAP[self.day_master].get(y_branch, "-"),
                    'gongmang': y_branch in gongmang_branches,
                })

            saeyun = {
                'current_age': current_age,
                'before_first_daewoon': current_age < self.daewoon_pillars[0][0],
                'current_daewoon': current_daewoon,
                'years': years,
            }

        # 대운 전체 (나이/간지/십신/12운성/공망 여부까지 - saeyun의 'years'와 같은 형태)
        daewoon_full = []
        for age, stem, branch in self.daewoon_pillars:
            daewoon_full.append({
                'age': age, 'stem': stem, 'branch': branch,
                'sipsin_stem': determine_ten_deity(self.day_master, stem, False),
                'sipsin_branch': determine_ten_deity(self.day_master, branch, True),
                'unseong': UNSEONG_MAP[self.day_master].get(branch, "-"),
                'gongmang': branch in gongmang_branches,
            })

        return {
            # 이 dict 하나만으로 완결되도록 고객 기본정보 + 원국 간지도 함께 담는다
            # (풀이 단계에서 analyzer 객체 없이 이 JSON만 보고도 전부 알 수 있어야 하므로)
            'meta': {
                'name': self.name, 'sex': self.sex,
                'birth_date': self.birth_date.isoformat() if self.birth_date else None,
                'has_hour': self.hour is not None,
                'saju_type': "사주팔자(四柱八字)" if self.hour else "사주삼주(三柱 - 시간모름)",
                'day_master': self.day_master,
            },
            # 고객이 선택 입력한 프로필 (없는 값은 null) — 풀이 단계에서 챕터별 서술 범위
            # 조정 및 심층 질문 답변 여부 판단에 사용
            'profile': {
                'marital_status': self.profile.get('marital_status'),
                'has_children': self.profile.get('has_children'),
                'job_status': self.profile.get('job_status'),
                'deep_question': self.profile.get('deep_question'),
            },
            'pillars_raw': {
                'year': list(self.year), 'month': list(self.month), 'day': list(self.day),
                'hour': list(self.hour) if self.hour else None,
            },
            'daewoon': {'num': self.daewoon_num, 'pillars': daewoon_full},
            'positions': positions, 'deities': deities, 'unseong_list': unseong_list, 'sinsal_list': sinsal_list,
            'jijanggan_list': jijanggan_list,
            'raw_scores': raw_scores, 'adj_scores': adj_scores, 'shift_logs': shift_logs,
            'comb_results': comb_results,
            'raw_strength': raw_strength, 'adj_strength': adj_strength,
            'eokbu_elem': eokbu_elem, 'johu_info': johu_info, 'tonggwan_info': tonggwan_info,
            'guckguk_info': guckguk_info,
            'life_areas': {'marriage': marriage_info, 'wealth': wealth_info, 'career': career_info},
            'year_ganji': year_ganji, 'naeum_info': naeum_info,
            'gongmang_info': gongmang_info, 'gongmang_branches': gongmang_branches,
            'deukryeong_info': deukryeong_info,
            'sinsal': {
                'dohwa': dohwasal_info, 'yangin': yanginsal_info, 'goegang': goegangsal_info,
                'cheoneul': cheoneul_info, 'munchang': munchang_info, 'wonjin': wonjinsal_list,
            },
            'saeyun': saeyun,
        }

    def generate_detailed_report(self):
        d = self.compute_all()
        raw_scores, adj_scores, shift_logs = d['raw_scores'], d['adj_scores'], d['shift_logs']
        comb_results = d['comb_results']
        raw_strength, adj_strength = d['raw_strength'], d['adj_strength']
        eokbu_elem, johu_info, tonggwan_info = d['eokbu_elem'], d['johu_info'], d['tonggwan_info']
        positions, deities = d['positions'], d['deities']
        unseong_list, sinsal_list = d['unseong_list'], d['sinsal_list']
        guckguk_info = d['guckguk_info']
        marriage_info, wealth_info, career_info = d['life_areas']['marriage'], d['life_areas']['wealth'], d['life_areas']['career']
        year_ganji, naeum_info = d['year_ganji'], d['naeum_info']
        gongmang_info, gongmang_branches = d['gongmang_info'], d['gongmang_branches']
        deukryeong_info = d['deukryeong_info']
        dohwasal_info, yanginsal_info, goegangsal_info = d['sinsal']['dohwa'], d['sinsal']['yangin'], d['sinsal']['goegang']
        cheoneul_info, munchang_info, wonjinsal_list = d['sinsal']['cheoneul'], d['sinsal']['munchang'], d['sinsal']['wonjin']

        report = []
        report.append("=" * 80)
        report.append(f"      [ {self.name} 님 정밀 사주명리 분석 자동화 V8 리포트 ]")
        report.append("=" * 80)
        saju_type = "사주팔자(四柱八字)" if self.hour else "사주삼주(三柱六字 - 시간모름)"
        report.append(f"■ 성별 구별: {self.sex} 명식")
        report.append(f"■ 연산 형식: {saju_type}")
        hour_p_str = f"{self.hour[0]}{self.hour[1]}" if self.hour else "시간모름"
        report.append(f"■ 대상 명식: 년주({self.year[0]}{self.year[1]}) 월주({self.month[0]}{self.month[1]}) 일주({self.day[0]}{self.day[1]}) 시주({hour_p_str})")
        report.append(f"■ 일간 기질: 본인을 나타내는 기운은 {self.day_master}({STEM_INFO[self.day_master]['name']}) 기운입니다.")
        report.append("-" * 80)
        
        report.append("1. 십신(육친) 매핑 및 신살/운성 지표")
        for idx, pos in enumerate(positions):
            char_str = deities[pos]
            uns_str = f" | 12운성: {unseong_list[idx]}" if unseong_list[idx] != "-" else ""
            sin_str = f" | 12신살: {sinsal_list[idx]}" if sinsal_list[idx] != "-" else ""
            report.append(f"  - {pos}: {char_str}{uns_str}{sin_str}")
        report.append("-" * 80)
        
        # NEW: 납음오행 추가
        report.append(f"2. 납음오행(納音五行) 분석")
        report.append(f"  - 년주 {year_ganji}: {naeum_info['name']} ({naeum_info['desc']})")
        report.append("-" * 80)
        
        report.append(f"3. 격국(格局) 판별")
        report.append(f"  - 격국: {guckguk_info['name']}")
        report.append(f"  - 판별 근거: 월지({self.month[1]}) 지장간 중 정기(正氣) {guckguk_info['jeonggi_stem']} → 일간 기준 {guckguk_info['sipsin']}")
        report.append(f"  - 특징: {guckguk_info['desc']}")
        report.append("-" * 80)
        
        report.append(f"4. 형(形) / 해(害) 분석")
        if comb_results['xing_hae']:
            for xh in comb_results['xing_hae']:
                report.append(f"  - {xh['desc']}")
        else:
            report.append(f"  - 원국 내 형/해 관계가 없습니다.")
        report.append("-" * 80)

        report.append("5. 공망(空亡) 분석")
        report.append(f"  - {gongmang_info['desc']}")
        own_branches = {'년지': self.year[1], '월지': self.month[1], '일지': self.day[1]}
        if self.hour:
            own_branches['시지'] = self.hour[1]
        hit_positions = [pos for pos, b in own_branches.items() if b in gongmang_branches]
        if hit_positions:
            report.append(f"  - 원국 내 공망 해당: {', '.join(hit_positions)}이(가) 공망 지지({'·'.join(gongmang_branches)})에 해당합니다.")
        else:
            report.append("  - 원국의 년지/월지/일지" + ("/시지" if self.hour else "") + "에는 공망이 걸리지 않았습니다.")
        report.append("-" * 80)

        report.append(f"6. 대운수 및 대운 흐름 (대운수: {self.daewoon_num})")
        for age, stem, branch in self.daewoon_pillars:
            d_deity_s = determine_ten_deity(self.day_master, stem, False)
            d_deity_b = determine_ten_deity(self.day_master, branch, True)
            d_uns = UNSEONG_MAP[self.day_master].get(branch, "-")
            gm_tag = " [공망]" if branch in gongmang_branches else ""
            report.append(f"  - {age:2d}세 대운: {stem}{branch} ({d_deity_s}/{d_deity_b} | {d_uns}){gm_tag}")
        report.append("-" * 80)

        report.append("7. 용신(用神) 판정 - 억부/조후/통관 교차검증")
        report.append(f"  [억부용신] {eokbu_elem} — 신강도({adj_strength['strength']})를 기준으로 원국의 균형을 맞추는 주(主) 용신")

        if johu_info['needed']:
            report.append(f"  [조후용신] {johu_info['element']} — {johu_info['desc']}")
            if johu_info.get('urgent'):
                if johu_info['element'] == eokbu_elem:
                    report.append(f"  → 억부용신과 조후용신이 {eokbu_elem}(으)로 일치합니다. 신뢰도가 높은 용신입니다.")
                else:
                    report.append(f"  → 억부상 {eokbu_elem}, 조후상 {johu_info['element']}이(가) 모두 필요합니다. 두 오행을 함께 보완하는 것이 이상적입니다.")
        else:
            report.append(f"  [조후용신] {johu_info['desc']}")

        if tonggwan_info['needed']:
            report.append(f"  [통관용신] {tonggwan_info['element']} — {tonggwan_info['desc']}")

        report.append("-" * 80)

        report.append("8. 원국 내 합(合)과 충(冲) 분석")
        has_any = False
        for comb in comb_results['stem_combinations']:
            report.append(f"  [천간합] {comb['desc']} 성립")
            has_any = True
        for comb in comb_results['branch_three_comb']:
            report.append(f"  [삼 합] {comb['desc']} (강력한 {comb['target_element']} 국 형성)")
            has_any = True
        for comb in comb_results['branch_half_comb']:
            report.append(f"  [반 합] {comb['desc']} ({comb['target_element']} 기운 강화)")
            has_any = True
        for comb in comb_results['branch_six_comb']:
            report.append(f"  [육 합] {comb['desc']}")
            has_any = True
            
        if not has_any:
            report.append("  - 특이한 원국 내 합/충 작용이 감지되지 않았습니다.")
        report.append("-" * 80)
        
        report.append("9. 지장간 사령 기반 실질 오행 점수")
        report.append("  [오행]      [순수 원국 점수]      [합화 시프트 반영 최종 점수]")
        for elem in ['木', '火', '土', '金', '水']:
            raw_s = raw_scores[elem]
            adj_s = adj_scores[elem]
            arrow = "→" if raw_s != adj_s else " "
            report.append(f"   - {elem} 기운:     {raw_s:5.1f} 점               {arrow}   {adj_s:5.1f} 점 ({adj_s:.1f}%)")
        report.append("-" * 80)

        if shift_logs:
            report.append("10. 에너지 합화(합화 시프트) 연산 로그")
            for log in shift_logs:
                report.append(f"  * {log}")
            report.append("-" * 80)

        season_info = adj_strength['season_info']
        season_line = " ".join(f"{e}({season_info['status_by_element'][e]})" for e in ['木', '火', '土', '金', '水'])
        report.append("11. 격국 신강도 최종 판정")
        report.append(f"  [월령 왕상휴수사]: {self.month[1]}월은 {season_info['season_element']}이(가) 왕성한 절기 → {season_line}")
        report.append(f"  [합화 전 순수 원국 신강도]: {raw_strength['strength']} (월령 가중 반영 비율: {raw_strength['helper_ratio']:.1f}%)")
        report.append(f"  [합화 반영 최종 실질 신강도]: {adj_strength['strength']} (월령 가중 반영 비율: {adj_strength['helper_ratio']:.1f}%)")
        report.append(f"  [월령(月令) 득실]: {deukryeong_info['status']} - {deukryeong_info['desc']}")
        report.append("-" * 80)

        report.append("12. 본질적 기질 및 성격 상세 분석")
        day_master_info = STEM_INFO[self.day_master]
        day_branch_info = BRANCH_INFO[self.day[1]]
        report.append(f"  - [일간(日干) 본질 기질 - {day_master_info['name']}]")
        report.append(f"    {day_master_info['desc']}")
        report.append(f"  - [일지(日支) 행동 및 무의식 성향 - {day_branch_info['k_name']}]")
        report.append(f"    지지에서는 동물 [{day_branch_info['animal']}]의 성향을 나타내며, {day_branch_info['desc']}")
        report.append("-" * 80)

        report.append("13. 배우자운(婚運) 분석 ✨")
        report.append(f"  - 배우자 기운: {marriage_info['type']}")
        report.append(f"  - 안정도: {marriage_info['strength']}")
        report.append(f"  - 설명: {marriage_info['desc']}")
        report.append(f"  - 배우자 유형: {marriage_info['partner_desc']}")
        report.append("-" * 80)

        report.append("14. 재운(財運) 분석 💰")
        report.append(f"  - 재성 점수: {wealth_info['score']:.1f}")
        report.append(f"  - 수준: {wealth_info['level']}")
        report.append(f"  - 분석: {wealth_info['desc']}")
        report.append("-" * 80)
        
        report.append("15. 직업운(職業運) 분석 🏢")
        report.append(f"  - 주도 오행: {career_info['elem']}")
        report.append(f"  - 강도: {career_info['strength']}")
        report.append(f"  - 적성 직업: {', '.join(career_info['suitable_jobs'])}")
        report.append(f"  - 분석: {career_info['desc']}")
        report.append("-" * 80)

        report.append("16. 주요 신살(神殺) 종합 ✨")
        if dohwasal_info['exists']:
            report.append(f"  - [도화살(桃花殺)] 있음 — {dohwasal_info['desc']}")
        else:
            report.append(f"  - [도화살(桃花殺)] 없음 — {dohwasal_info['desc']}")
        if yanginsal_info['exists']:
            report.append(f"  - [양인살(陽刃殺)] 있음 — {yanginsal_info['desc']}")
        else:
            report.append(f"  - [양인살(陽刃殺)] 없음 — {yanginsal_info['desc']}")
        if goegangsal_info['exists']:
            report.append(f"  - [괴강살(魁罡殺)] 있음 — {goegangsal_info['desc']}")
        if cheoneul_info['exists']:
            report.append(f"  - [천을귀인(天乙貴人)] 있음 — {cheoneul_info['desc']}")
        else:
            report.append(f"  - [천을귀인(天乙貴人)] 없음 — {cheoneul_info['desc']}")
        if munchang_info['exists']:
            report.append(f"  - [문창귀인(文昌貴人)] 있음 — {munchang_info['desc']}")
        else:
            report.append(f"  - [문창귀인(文昌貴人)] 없음 — {munchang_info['desc']}")
        for w in wonjinsal_list:
            report.append(f"  - [원진살(怨嗔殺) - {w['name']}] 있음 — {w['desc']}")
        if not wonjinsal_list:
            report.append("  - [원진살(怨嗔殺)] 없음 — 원국 지지 간 원진 관계가 없습니다.")
        report.append("=" * 80)

        sy = d['saeyun']
        if sy is not None:
            report.append("17. 세운(歲運) 흐름 - 현재 대운 및 향후 5년 유년운")

            if sy['before_first_daewoon']:
                report.append(f"  - 현재 만 나이(세는나이 {sy['current_age']}세) 기준, 아직 첫 대운(대운수 {self.daewoon_num}) 이전입니다.")
            elif sy['current_daewoon']:
                age, stem, branch = sy['current_daewoon']
                d_deity_s = determine_ten_deity(self.day_master, stem, False)
                d_deity_b = determine_ten_deity(self.day_master, branch, True)
                gm_tag = " [공망]" if branch in gongmang_branches else ""
                report.append(f"  - 현재 대운(세는나이 {sy['current_age']}세): {stem}{branch} ({age}세~{age+9}세, {d_deity_s}/{d_deity_b}){gm_tag}")

            for y in sy['years']:
                gm_tag = " [공망]" if y['gongmang'] else ""
                label = "올해" if y['offset'] == 0 else f"{y['offset']}년 후"
                report.append(f"  - {y['year']}년({label}) 세운: {y['stem']}{y['branch']} ({y['sipsin_stem']}/{y['sipsin_branch']} | {y['unseong']}){gm_tag}")
            report.append("-" * 80)
            report.append("  ※ 세운은 세는나이(태어난 해를 1세로 계산) 기준의 근사치이며, 연도 자체의 년주로 계산됩니다.")
            report.append("=" * 80)

        return "\n".join(report)

# ============================================================================
# [Streamlit UI] 입력 → 확인 → 사주정보 3단계
# ============================================================================

ELEMENT_COLORS = {
    '木': ('#e8f5e9', '#2e7d32'),
    '火': ('#ffebee', '#c62828'),
    '土': ('#fff8e1', '#a66a00'),
    '金': ('#f5f5f5', '#555555'),
    '水': ('#e3f2fd', '#1565c0'),
}


def _ohaeng_band_label(pct):
    if pct < 5:
        return '부족'
    elif pct < 15:
        return '약함'
    elif pct < 30:
        return '적정'
    elif pct < 40:
        return '발달'
    return '과다'


def _sipsin_distribution(analyzer):
    """일간을 제외한 나머지 글자들의 십신 분포(개수/비율)"""
    order = ['비견', '겁재', '식신', '상관', '편재', '정재', '편관', '정관', '편인', '정인']
    counts = {k: 0 for k in order}
    for s in analyzer.stems:
        if s == analyzer.day_master:
            continue
        counts[determine_ten_deity(analyzer.day_master, s, False)] += 1
    for b in analyzer.branches:
        counts[determine_ten_deity(analyzer.day_master, b, True)] += 1
    total = sum(counts.values()) or 1
    return order, counts, total


def _pillar_card_html(label, stem, stem_deity, branch, branch_deity, jijanggan, unseong, sinsal):
    s_bg, s_fg = ELEMENT_COLORS[STEM_INFO[stem]['element']]
    b_bg, b_fg = ELEMENT_COLORS[BRANCH_INFO[branch]['element']]
    return f"""
    <div style="border:1px solid #e0e0e0;border-radius:12px;padding:10px 6px;text-align:center;background:#fff;">
      <div style="font-size:12px;color:#888;margin-bottom:6px;">{label}</div>
      <div style="background:{s_bg};color:{s_fg};border-radius:8px;padding:10px 2px;font-size:24px;font-weight:800;margin-bottom:4px;">{stem}</div>
      <div style="font-size:11px;color:#666;margin-bottom:8px;">{stem_deity}</div>
      <div style="background:{b_bg};color:{b_fg};border-radius:8px;padding:10px 2px;font-size:24px;font-weight:800;margin-bottom:4px;">{branch}</div>
      <div style="font-size:11px;color:#666;margin-bottom:6px;">{branch_deity}</div>
      <div style="font-size:10px;color:#aaa;">지장간 {jijanggan}</div>
      <div style="font-size:10px;color:#aaa;">{unseong} · {sinsal}</div>
    </div>
    """


def render_input_screen():
    st.header("📋 분석 대상자 정보 입력")

    name = st.text_input("이름", value="", max_chars=12, placeholder="최대 12글자 이내로 입력하세요")
    sex = st.radio("성별", ["여자", "남자"], horizontal=True)
    sex_internal = "남성" if sex == "남자" else "여성"

    calendar_type = st.radio("양력 / 음력", ["양력", "음력"], horizontal=True)
    is_lunar = (calendar_type == "음력")
    is_leap = False
    if is_lunar:
        is_leap = st.checkbox("윤달 여부")

    time_unknown = st.checkbox("⏰ 시간 모름")

    birth_date = st.date_input(
        "생년월일",
        value=datetime.date(1990, 1, 1),
        min_value=datetime.date(1920, 1, 1),
        max_value=datetime.date(2030, 12, 31),
    )

    birth_time = None
    if not time_unknown:
        birth_time = st.time_input("생시", value=datetime.time(12, 0))
    else:
        st.caption("⏰ 시간을 모르면 시주(時柱) 없이 년주·월주·일주 세 기둥만으로 분석됩니다. 시지 기반 신살·12운성 일부도 판정에서 제외됩니다.")

    time_boundary = "선택 안 함(기본)"
    if not time_unknown:
        use_jasi_option = st.checkbox("야자시/조자시 세부 설정 사용", value=False, help="자시(23~01시) 처리 방식에 대한 고급 옵션입니다. 잘 모르시면 꺼두시면 기본값(선택 안 함)으로 계산됩니다.")
        if use_jasi_option:
            time_boundary = st.selectbox(
                "야자시 / 조자시 기준",
                ["선택 안 함(기본)", "야자시 적용 (23:30~24:00)", "조자시 적용 (00:00~00:30)"],
            )

    st.markdown("**도시**")
    city_options = list(CITY_LONGITUDE_OFFSETS.keys()) + ["직접 입력(수동 분 단위)"]
    city = st.selectbox("도시명을 입력하거나 목록에서 선택하세요", city_options, index=city_options.index("서울특별시"), label_visibility="collapsed")
    if city == "직접 입력(수동 분 단위)":
        region_offset_mins = st.slider("수동 경도 시차 (분)", -45, 0, -30)
    else:
        region_offset_mins = CITY_LONGITUDE_OFFSETS[city]

    dst_auto = st.checkbox("역사적 서머타임/과거 표준시 자동 보정", value=True, help="서머타임 실시 기간(1948~1988년 일부)과 한국 표준시가 UTC+8:30이던 시기(1954~1961년)를 자동으로 인식해 보정합니다.")

    st.write("")
    with st.expander("📝 선택 입력 — 더 정확한 심층 풀이를 원하시면 입력해주세요"):
        st.caption("혼인·자녀·직업 상태에 따라 풀이 내용의 깊이와 방향이 달라집니다. 모르거나 밝히고 싶지 않으면 비워두셔도 됩니다.")
        marital_status = st.radio("혼인상태", ["선택 안 함", "미혼", "기혼", "이혼·사별"])
        has_children = st.radio("자녀유무", ["선택 안 함", "없음", "있음"])
        job_status = st.radio("직업상태", ["선택 안 함", "재학중(학생)", "재직중(직장인)", "사업·자영업", "구직·전환기"])
        deep_question = st.text_area("심층 질문 (선택)", placeholder="예: 이직 시기가 궁금해요 / 결혼은 언제쯤일까요 / 자녀 학업운이 궁금해요", height=80)

    with st.expander("📞 연락처 및 리포트 전달 방식 (선택)"):
        st.caption("완성된 리포트를 전달받을 방법입니다. 지금은 정보만 저장되고, 실제 자동 발송은 추후 연동될 예정입니다.")
        phone = st.text_input("전화번호", placeholder="010-0000-0000")
        email = st.text_input("이메일", placeholder="example@email.com")
        delivery_method = st.radio("리포트 전달 방식", ["선택 안 함", "이메일로 받기", "문자(SMS)로 받기", "카카오톡으로 받기"])

    with st.expander("💕 궁합 분석 추가 (선택)"):
        want_compat = st.checkbox("궁합 분석을 함께 신청할게요")
        partner_type = partner_name = partner_sex = None
        partner_birth_known = False
        partner_is_lunar = partner_is_leap = False
        partner_date = None
        partner_time_unknown = True
        partner_time = None
        partner_city = None
        if want_compat:
            compat_type = st.radio("궁합 유형", ["연인·배우자 궁합", "재회 궁합", "반려동물 궁합"])
            partner_type = compat_type
            partner_label = "반려동물" if compat_type == "반려동물 궁합" else "상대방"
            st.caption(f"{partner_label} 정보를 아는 만큼만 입력해주세요. 다 몰라도 괜찮습니다 — 아는 정보만 참고해서 함께 분석합니다.")
            partner_name = st.text_input(f"{partner_label} 이름", key="partner_name")
            partner_sex = st.radio(f"{partner_label} 성별", ["모름", "여자", "남자"], key="partner_sex")
            partner_birth_known = st.checkbox("생년월일을 알아요", key="partner_birth_known")
            if partner_birth_known:
                partner_calendar = st.radio("양력 / 음력", ["양력", "음력"], key="partner_calendar")
                partner_is_lunar = (partner_calendar == "음력")
                if partner_is_lunar:
                    partner_is_leap = st.checkbox("윤달 여부", key="partner_is_leap")
                partner_date = st.date_input(
                    f"{partner_label} 생년월일", value=datetime.date(1990, 1, 1),
                    min_value=datetime.date(1920, 1, 1), max_value=datetime.date(2030, 12, 31),
                    key="partner_date",
                )
                partner_time_unknown = st.checkbox("시간 모름", value=True, key="partner_time_unknown")
                if not partner_time_unknown:
                    partner_time = st.time_input(f"{partner_label} 생시", value=datetime.time(12, 0), key="partner_time")
                partner_city_options = ["선택 안 함"] + list(CITY_LONGITUDE_OFFSETS.keys())
                partner_city = st.selectbox(f"{partner_label} 태어난 도시", partner_city_options, key="partner_city")
                if partner_city == "선택 안 함":
                    partner_city = None

    if st.button("만세력 보러가기", type="primary", use_container_width=True):
        if not name.strip():
            st.error("이름을 입력해주세요.")
            return
        if delivery_method == "이메일로 받기" and not email.strip():
            st.error("이메일로 받기를 선택하셨다면 이메일을 입력해주세요.")
            return
        if delivery_method in ("문자(SMS)로 받기", "카카오톡으로 받기") and not phone.strip():
            st.error("문자/카카오톡으로 받기를 선택하셨다면 전화번호를 입력해주세요.")
            return
        st.session_state.input_data = {
            'name': name.strip(), 'sex': sex_internal, 'is_lunar': is_lunar, 'is_leap': is_leap,
            'time_unknown': time_unknown, 'birth_date': birth_date, 'birth_time': birth_time,
            'city': city, 'region_offset_mins': region_offset_mins,
            'dst_auto': dst_auto, 'time_boundary': time_boundary,
            'profile': {
                'marital_status': marital_status if marital_status != "선택 안 함" else None,
                'has_children': has_children if has_children != "선택 안 함" else None,
                'job_status': job_status if job_status != "선택 안 함" else None,
                'deep_question': deep_question.strip() or None,
            },
            'contact': {
                'phone': phone.strip() or None,
                'email': email.strip() or None,
                'delivery_method': delivery_method if delivery_method != "선택 안 함" else None,
            },
            'compatibility': {
                'requested': want_compat,
                'type': partner_type,
                'partner_name': (partner_name.strip() or None) if partner_name else None,
                'partner_sex': partner_sex if partner_sex and partner_sex != "모름" else None,
                'partner_birth_known': partner_birth_known,
                'partner_is_lunar': partner_is_lunar,
                'partner_is_leap': partner_is_leap,
                'partner_date': partner_date,
                'partner_time_unknown': partner_time_unknown,
                'partner_time': partner_time,
                'partner_city': partner_city,
            } if want_compat else {'requested': False},
        }
        st.session_state.step = 'confirm'
        st.rerun()


def render_confirm_screen():
    st.header("✅ 입력 정보 확인")
    data = st.session_state.input_data

    cal_str = ("음력(윤달)" if data['is_leap'] else "음력") if data['is_lunar'] else "양력"
    time_str = data['birth_time'].strftime('%H:%M') if data['birth_time'] else "시간모름"

    st.markdown(f"""
| 항목 | 값 |
|---|---|
| 이름 | {data['name']} |
| 성별 | {data['sex']} |
| 생년월일 | {data['birth_date'].strftime('%Y-%m-%d')} ({cal_str}) |
| 생시 | {time_str} |
| 태어난 도시 | {data['city']} (경도 보정 {data['region_offset_mins']}분) |
| 서머타임/과거 표준시 자동보정 | {'적용' if data['dst_auto'] else '미적용'} |
""")

    profile = data.get('profile') or {}
    profile_rows = [
        ('혼인상태', profile.get('marital_status')),
        ('자녀유무', profile.get('has_children')),
        ('직업상태', profile.get('job_status')),
        ('심층 질문', profile.get('deep_question')),
    ]
    profile_rows = [(k, v) for k, v in profile_rows if v]
    if profile_rows:
        st.markdown("**선택 입력 정보**")
        st.markdown("\n".join(f"- {k}: {v}" for k, v in profile_rows))

    contact = data.get('contact') or {}
    contact_rows = [
        ('전화번호', contact.get('phone')),
        ('이메일', contact.get('email')),
        ('리포트 전달 방식', contact.get('delivery_method')),
    ]
    contact_rows = [(k, v) for k, v in contact_rows if v]
    if contact_rows:
        st.markdown("**연락처 / 리포트 전달**")
        st.markdown("\n".join(f"- {k}: {v}" for k, v in contact_rows))

    compat = data.get('compatibility') or {}
    if compat.get('requested'):
        st.markdown("**궁합 분석 신청 정보**")
        compat_lines = [f"- 유형: {compat.get('type')}"]
        if compat.get('partner_name'):
            compat_lines.append(f"- 상대방 이름: {compat['partner_name']}")
        if compat.get('partner_sex'):
            compat_lines.append(f"- 상대방 성별: {compat['partner_sex']}")
        if compat.get('partner_birth_known') and compat.get('partner_date'):
            p_cal = ("음력(윤달)" if compat.get('partner_is_leap') else "음력") if compat.get('partner_is_lunar') else "양력"
            p_time = "시간모름" if compat.get('partner_time_unknown') else compat['partner_time'].strftime('%H:%M')
            compat_lines.append(f"- 상대방 생년월일: {compat['partner_date'].strftime('%Y-%m-%d')} ({p_cal}) / {p_time}")
            if compat.get('partner_city'):
                compat_lines.append(f"- 상대방 태어난 도시: {compat['partner_city']}")
        else:
            compat_lines.append("- 상대방 생년월일: 모름 (참고용 정보만으로 분석)")
        st.markdown("\n".join(compat_lines))

    if data['time_unknown']:
        st.info("⏰ 시간을 모르셔서 시주(時柱) 없이 년주·월주·일주 세 기둥으로만 분석됩니다. 대운 방향과 신강신약 비율은 정상적으로 계산되지만, 시지 기반 신살·12운성 일부는 판정에서 제외됩니다.")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("← 다시 입력", use_container_width=True):
            st.session_state.step = 'input'
            st.rerun()
    with col2:
        if st.button("이 정보로 분석하기", type="primary", use_container_width=True):
            b_hour = data['birth_time'].hour if data['birth_time'] else None
            b_minute = data['birth_time'].minute if data['birth_time'] else 0

            dst_offset_mins = 0
            if data['dst_auto'] and not data['time_unknown'] and not data['is_lunar']:
                auto_dst = get_dst_offset_minutes(data['birth_date'].year, data['birth_date'].month, data['birth_date'].day, b_hour, b_minute)
                dst_offset_mins = 60 if auto_dst > 0 else 0

            try:
                year_p, month_p, day_p, hour_p, daewoon_num, daewoon_pillars, is_forward, lst_dt = convert_to_pillars(
                    data['birth_date'].year, data['birth_date'].month, data['birth_date'].day,
                    b_hour, b_minute, data['is_lunar'], data['is_leap'], data['sex'],
                    data['time_boundary'], data['region_offset_mins'], dst_offset_mins
                )
                analyzer = AdvancedSajuAnalyzer(
                    data['name'], data['sex'], year_p, month_p, day_p, hour_p,
                    daewoon_num, daewoon_pillars, birth_date=lst_dt.date(),
                    profile=data.get('profile')
                )
                st.session_state.analyzer = analyzer
                saju_data = analyzer.compute_all()
                saju_data['contact'] = data.get('contact') or {}

                compat = data.get('compatibility') or {}
                compat_out = {'requested': compat.get('requested', False), 'type': compat.get('type'),
                               'partner_name': compat.get('partner_name'), 'partner_sex': compat.get('partner_sex'),
                               'partner_city': compat.get('partner_city'), 'partner_saju': None}
                if compat.get('requested') and compat.get('partner_birth_known') and compat.get('partner_date') and compat.get('partner_sex'):
                    p_date = compat['partner_date']
                    p_hour = compat['partner_time'].hour if (not compat.get('partner_time_unknown') and compat.get('partner_time')) else None
                    p_minute = compat['partner_time'].minute if (not compat.get('partner_time_unknown') and compat.get('partner_time')) else 0
                    p_sex_internal = "남성" if compat['partner_sex'] == "남자" else "여성"
                    p_region_offset = CITY_LONGITUDE_OFFSETS.get(compat.get('partner_city'), 0)
                    try:
                        py, pm, pd_, ph, p_daewoon_num, p_daewoon_pillars, _, p_lst_dt = convert_to_pillars(
                            p_date.year, p_date.month, p_date.day, p_hour, p_minute,
                            compat.get('partner_is_lunar', False), compat.get('partner_is_leap', False),
                            p_sex_internal, "선택 안 함(기본)", p_region_offset, 0
                        )
                        partner_analyzer = AdvancedSajuAnalyzer(
                            compat.get('partner_name') or "상대방",
                            p_sex_internal, py, pm, pd_, ph, p_daewoon_num, p_daewoon_pillars,
                            birth_date=p_lst_dt.date()
                        )
                        compat_out['partner_saju'] = partner_analyzer.compute_all()
                    except Exception:
                        compat_out['partner_saju'] = None
                saju_data['compatibility'] = compat_out

                st.session_state.saju_data = saju_data
                st.session_state.report_text = analyzer.generate_detailed_report()
                st.session_state.step = 'result'
                st.rerun()
            except Exception as e:
                st.error(f"입력하신 정보로 사주를 계산할 수 없습니다: {e}")


def _json_safe(obj):
    """compute_all() dict를 json.dumps 가능한 형태로 변환 (frozenset/set/tuple → list)."""
    if isinstance(obj, dict):
        return {str(k): _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set, frozenset)):
        return [_json_safe(v) for v in obj]
    return obj


def render_report_generation_section(saju_data, customer_name):
    """2단계: 지침 문서 + saju_data(JSON)를 Claude API에 넘겨 실제 사주풀이 리포트를 생성하는 섹션."""
    st.subheader("🖋️ AI 인생 전략 리포트 생성")
    st.caption("위 사주 데이터와 풀이 지침을 근거로 Claude가 실제 리포트를 작성합니다. 분량이 길어 완성까지 1~2분 정도 걸릴 수 있고, 1회 생성마다 API 비용이 발생합니다.")

    api_key = report_pipeline.resolve_api_key(st.session_state.get('anthropic_api_key'))
    if not api_key:
        st.info("리포트를 생성하려면 Anthropic API 키가 필요합니다. 아래에 입력하면 이번 세션에서만 사용되고 저장되지 않습니다. (매번 새로 입력하지 않으려면 환경변수 `ANTHROPIC_API_KEY` 또는 `.streamlit/secrets.toml`에 등록해두세요.)")
        entered_key = st.text_input("Anthropic API 키", type="password", key="anthropic_api_key_input")
        if entered_key:
            st.session_state.anthropic_api_key = entered_key
            st.rerun()
        return

    generate_clicked = st.button("📝 리포트 생성하기", type="primary")

    if generate_clicked:
        result_holder = {}
        try:
            full_text = st.write_stream(
                report_pipeline.stream_report(saju_data, api_key, result_holder=result_holder)
            )
        except Exception as e:
            st.error(f"리포트 생성 중 오류가 발생했습니다: {e}")
            return
        st.session_state.generated_report = full_text
        st.session_state.pop('verification_result', None)
        st.session_state.pop('verification_decision', None)
        st.session_state.pop('generated_pdf', None)
        final_message = result_holder.get('final_message')
        if final_message:
            warn = "⚠️ 분량 제한에 걸려 리포트가 끝까지 완성되지 못했습니다. 아래 결과는 중간까지만 포함되어 있습니다." if final_message.stop_reason == "max_tokens" else None
            st.session_state.generated_report_meta = {
                'warn': warn,
                'usage_caption': report_pipeline.usage_caption(final_message.usage),
            }
    elif st.session_state.get('generated_report'):
        st.markdown(st.session_state.generated_report)

    if st.session_state.get('generated_report'):
        meta = st.session_state.get('generated_report_meta') or {}
        if meta.get('warn'):
            st.warning(meta['warn'])
        if meta.get('usage_caption'):
            st.caption(meta['usage_caption'])
        st.download_button(
            "💾 리포트 다운로드 (.md)",
            data=st.session_state.generated_report,
            file_name=f"{customer_name}_인생전략리포트.md",
            mime="text/markdown",
        )

        st.write("")
        render_report_verification_section(saju_data, api_key)

        st.write("")
        render_pdf_export_section(saju_data, customer_name)


def render_pdf_export_section(saju_data, customer_name):
    """3단계: 완성된 리포트 텍스트 + saju_data(JSON)를 pdf_report.py 템플릿에 흘려 넣어
    실제 PDF 파일로 렌더링하는 섹션. 스냅샷의 원국·오행·대운·용신 수치는 리포트 텍스트가
    아니라 항상 saju_data에서 직접 읽으므로, AI가 쓴 문장과 무관하게 정확하다."""
    st.subheader("📄 PDF로 저장")
    st.caption("위 리포트를 세로형 문서 템플릿에 흘려 넣어 챕터별로 페이지가 나뉜 완성된 PDF를 만듭니다. 몇 초 정도 걸릴 수 있습니다.")

    if st.button("📄 PDF 생성하기"):
        try:
            with st.spinner("PDF 생성 중..."):
                pdf_bytes = pdf_report.build_pdf(st.session_state.generated_report, saju_data)
        except Exception as e:
            st.error(f"PDF 생성 중 오류가 발생했습니다: {e}")
            return
        st.session_state.generated_pdf = pdf_bytes

    if st.session_state.get('generated_pdf'):
        st.download_button(
            "💾 PDF 다운로드",
            data=st.session_state.generated_pdf,
            file_name=f"{customer_name}_프리미엄종합사주해답지.pdf",
            mime="application/pdf",
        )


def render_report_verification_section(saju_data, api_key):
    """생성된 리포트를 원본 JSON·지침 기준으로 검수하고, 필요하면 수정본을 다시 만드는 섹션."""
    st.subheader("🔍 리포트 검수")

    verify_clicked = st.button("🔍 검증할까요?")
    if verify_clicked:
        result_holder = {}
        try:
            verification_text = st.write_stream(
                report_pipeline.stream_verification(
                    st.session_state.generated_report, saju_data, api_key, result_holder=result_holder
                )
            )
        except Exception as e:
            st.error(f"검증 중 오류가 발생했습니다: {e}")
            return
        st.session_state.verification_result = verification_text
        st.session_state.pop('verification_decision', None)
    elif st.session_state.get('verification_result'):
        st.markdown(st.session_state.verification_result)

    verification_text = st.session_state.get('verification_result')
    if not verification_text:
        return

    if report_pipeline.is_clean_verification(verification_text):
        st.success("✅ 검수 결과 이상 없습니다.")
        return

    decision = st.session_state.get('verification_decision')
    if decision == 'revised':
        st.info("✏️ 위 문제를 반영해 리포트를 다시 작성했습니다. 위쪽 리포트 내용이 수정본으로 교체되었습니다.")
        return
    if decision == 'proceeded':
        st.info("➡️ 수정 없이 현재 리포트로 진행합니다.")
        return

    st.markdown("**수정해서 다시 출력할까요, 그냥 진행할까요?**")
    col1, col2 = st.columns(2)
    with col1:
        revise_clicked = st.button("✏️ 수정해서 다시 출력", type="primary")
    with col2:
        proceed_clicked = st.button("➡️ 그냥 진행")

    if revise_clicked:
        result_holder = {}
        try:
            revised_text = st.write_stream(
                report_pipeline.stream_revision(
                    st.session_state.generated_report, saju_data, verification_text, api_key,
                    result_holder=result_holder
                )
            )
        except Exception as e:
            st.error(f"수정본 생성 중 오류가 발생했습니다: {e}")
            return
        st.session_state.generated_report = revised_text
        st.session_state.pop('generated_pdf', None)
        final_message = result_holder.get('final_message')
        if final_message:
            st.session_state.generated_report_meta = {
                'warn': "⚠️ 분량 제한에 걸려 리포트가 끝까지 완성되지 못했습니다." if final_message.stop_reason == "max_tokens" else None,
                'usage_caption': report_pipeline.usage_caption(final_message.usage),
            }
        st.session_state.verification_decision = 'revised'
        st.rerun()
    elif proceed_clicked:
        st.session_state.verification_decision = 'proceeded'
        st.rerun()


def render_result_screen():
    analyzer = st.session_state.analyzer
    d = st.session_state.saju_data

    st.header(f"🔮 {analyzer.name} 님의 사주 정보")
    saju_type = "사주팔자(四柱八字)" if analyzer.hour else "사주삼주(三柱 - 시간모름)"
    st.caption(f"{analyzer.sex} · {saju_type} · 일간 {analyzer.day_master}({STEM_INFO[analyzer.day_master]['name']})")

    st.subheader("🗂️ 사주 정보 (JSON — 풀이 단계에서 그대로 읽어가는 원본 데이터)")
    st.caption("이 화면 아래 카드들은 관리자가 대충 훑어보기 위한 참고용이고, 실제 풀이는 이 JSON을 기준으로 진행합니다. 배우자운/재운/직업운 등 서술형 계산 결과도 여기엔 전부 포함되어 있습니다.")
    json_data = _json_safe(d)
    json_text = json.dumps(json_data, ensure_ascii=False, indent=2)
    with st.expander("📦 JSON 펼쳐보기", expanded=False):
        st.code(json_text, language="json")
    st.download_button(
        "💾 사주 정보 JSON 다운로드 (.json)",
        data=json_text,
        file_name=f"{analyzer.name}_사주정보.json",
        mime="application/json",
    )

    st.write("---")
    render_report_generation_section(d, analyzer.name)

    st.write("---")
    st.caption("아래는 참고용 요약 화면입니다.")

    pos_idx = {p: i for i, p in enumerate(d['positions'])}

    def branch_meta(pos_key):
        i = pos_idx[pos_key]
        return d['unseong_list'][i], d['sinsal_list'][i], d['jijanggan_list'][i]

    pillars = []
    if analyzer.hour:
        pillars.append(('시주', analyzer.hour[0], analyzer.hour[1], '시간', '시지'))
    pillars.append(('일주', analyzer.day[0], analyzer.day[1], None, '일지'))
    pillars.append(('월주', analyzer.month[0], analyzer.month[1], '월간', '월지'))
    pillars.append(('년주', analyzer.year[0], analyzer.year[1], '년간', '년지'))

    st.subheader("사주 원국")
    cols = st.columns(len(pillars))
    for col, (label, stem, branch, stem_pos, branch_pos) in zip(cols, pillars):
        stem_deity = "본인(일간)" if stem_pos is None else determine_ten_deity(analyzer.day_master, stem, False)
        branch_deity = determine_ten_deity(analyzer.day_master, branch, True)
        unseong, sinsal, jijang = branch_meta(branch_pos)
        with col:
            st.markdown(_pillar_card_html(label, stem, stem_deity, branch, branch_deity, jijang, unseong, sinsal), unsafe_allow_html=True)

    st.write("")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"**납음오행(納音五行)**  \n{d['naeum_info']['name']}")
        st.caption(d['naeum_info']['desc'])
        st.markdown(f"**격국(格局)**  \n{d['guckguk_info']['name']}")
        st.caption(d['guckguk_info']['desc'])
    with c2:
        gm = d['gongmang_info']
        st.markdown(f"**공망(空亡)**  \n{'·'.join(gm['branches']) if gm['branches'] else '-'}")
        st.caption(gm['desc'])
        st.markdown(f"**월령(月令)**  \n{d['deukryeong_info']['status']}")
        st.caption(d['deukryeong_info']['desc'])

    st.write("---")
    st.subheader("오행 분석")
    adj = d['adj_scores']
    total_ohaeng = sum(adj.values()) or 1
    ocols = st.columns(5)
    for oc, elem in zip(ocols, ['木', '火', '土', '金', '水']):
        pct = adj[elem] / total_ohaeng * 100
        with oc:
            st.metric(elem, f"{pct:.1f}%", _ohaeng_band_label(pct))
            st.progress(min(1.0, pct / 100))

    st.subheader("십성 분석")
    order, sipsin_counts, sipsin_total = _sipsin_distribution(analyzer)
    scols = st.columns(5)
    for i, name10 in enumerate(order):
        with scols[i % 5]:
            pct = sipsin_counts[name10] / sipsin_total * 100
            st.metric(name10, f"{pct:.0f}%")

    st.write("---")
    st.subheader("신강신약")
    strength = d['adj_strength']
    season = strength['season_info']
    season_line = " ".join(f"{e}({season['status_by_element'][e]})" for e in ['木', '火', '土', '金', '水'])
    st.markdown(f"### {strength['strength']}")
    st.caption(f"월령 가중 반영 비율 {strength['helper_ratio']:.1f}% (아군 기운: {'·'.join(strength['helper_elements'])})")
    st.caption(f"월령 왕상휴수사: {season_line}")
    st.caption(f"{d['deukryeong_info']['status']} - {d['deukryeong_info']['desc']}")

    st.subheader("용신(用神)")
    st.markdown(f"- **억부용신**: {d['eokbu_elem']}")
    if d['johu_info']['needed']:
        urgent_tag = " (시급)" if d['johu_info'].get('urgent') else ""
        st.markdown(f"- **조후용신**: {d['johu_info']['element']}{urgent_tag}")
        st.caption(d['johu_info']['desc'])
    if d['tonggwan_info']['needed']:
        st.markdown(f"- **통관용신**: {d['tonggwan_info']['element']}")
        st.caption(d['tonggwan_info']['desc'])

    st.write("---")
    st.subheader(f"대운 (대운수: {analyzer.daewoon_num})")
    gongmang_branches = d['gongmang_branches']
    daewoon_cols = st.columns(len(analyzer.daewoon_pillars))
    for dc, (age, stem, branch) in zip(daewoon_cols, analyzer.daewoon_pillars):
        s_deity = determine_ten_deity(analyzer.day_master, stem, False)
        b_deity = determine_ten_deity(analyzer.day_master, branch, True)
        uns = UNSEONG_MAP[analyzer.day_master].get(branch, "-")
        gm_tag = " 🈳" if branch in gongmang_branches else ""
        with dc:
            st.markdown(f"<div style='text-align:center;font-size:12px;color:#888;'>{age}세{gm_tag}</div>", unsafe_allow_html=True)
            st.markdown(_pillar_card_html("", stem, s_deity, branch, b_deity, "", uns, "")[:], unsafe_allow_html=True)

    if d['saeyun']:
        st.write("---")
        st.subheader("세운(歲運) - 현재 대운 및 향후 5년")
        sy = d['saeyun']
        if sy['before_first_daewoon']:
            st.caption(f"현재 세는나이 {sy['current_age']}세 — 아직 첫 대운(대운수 {analyzer.daewoon_num}) 이전입니다.")
        elif sy['current_daewoon']:
            age, stem, branch = sy['current_daewoon']
            st.caption(f"현재 대운(세는나이 {sy['current_age']}세): {stem}{branch} ({age}세~{age+9}세)")
        ycols = st.columns(len(sy['years']))
        for yc, y in zip(ycols, sy['years']):
            label = "올해" if y['offset'] == 0 else f"+{y['offset']}년"
            gm_tag = " 🈳" if y['gongmang'] else ""
            with yc:
                st.markdown(f"<div style='text-align:center;font-size:12px;color:#888;'>{y['year']}({label}){gm_tag}</div>", unsafe_allow_html=True)
                st.markdown(_pillar_card_html("", y['stem'], y['sipsin_stem'], y['branch'], y['sipsin_branch'], "", y['unseong'], "")[:], unsafe_allow_html=True)

    st.write("---")
    st.subheader("주요 신살(神殺)")
    s = d['sinsal']
    badges = []
    if s['dohwa']['exists']:
        badges.append('도화살')
    if s['yangin']['exists']:
        badges.append('양인살')
    if s['goegang']['exists']:
        badges.append('괴강살')
    if s['cheoneul']['exists']:
        badges.append('천을귀인')
    if s['munchang']['exists']:
        badges.append('문창귀인')
    for w in s['wonjin']:
        badges.append(w['name'])
    if badges:
        st.markdown(" ".join(f"`{b}`" for b in badges))
    else:
        st.caption("해당하는 주요 신살이 없습니다.")

    st.write("---")
    with st.expander("📄 상세 텍스트 리포트 보기"):
        st.code(st.session_state.report_text, language="text")
        st.download_button(
            "💾 텍스트 리포트 다운로드 (.txt)",
            data=st.session_state.report_text,
            file_name=f"{analyzer.name}_사주정보.txt",
            mime="text/plain",
        )

    st.write("")
    if st.button("← 처음부터 다시"):
        for k in ['step', 'input_data', 'analyzer', 'saju_data', 'report_text',
                  'generated_report', 'generated_report_meta', 'generated_pdf',
                  'verification_result', 'verification_decision']:
            st.session_state.pop(k, None)
        st.session_state.step = 'input'
        st.rerun()


def main():
    st.set_page_config(
        page_title="사주명리 분석 자동화 V8 통합 플랫폼",
        page_icon="🔮",
        layout="centered",
        initial_sidebar_state="collapsed",
    )
    st.title("🔮 포스텔러 스타일 만세력")

    if 'step' not in st.session_state:
        st.session_state.step = 'input'

    if st.session_state.step == 'input':
        render_input_screen()
    elif st.session_state.step == 'confirm':
        render_confirm_screen()
    elif st.session_state.step == 'result':
        render_result_screen()
    else:
        st.session_state.step = 'input'
        st.rerun()

if __name__ == "__main__":
    main()
