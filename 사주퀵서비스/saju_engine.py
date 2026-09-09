# -*- coding: utf-8 -*-
"""
사주분석 대화형 웹 애플리케이션 제8판 (Complete Enhanced Version)
- 작성일: 2026-08-26 / 수정일: 2026-09-05
- 기술 스택: Python, Streamlit
"""

import streamlit as st
import math
import datetime
import json
import os


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

MYUNGRI_TIME_OPTIONS = [
    "시간 모름 (선택 시 시간 제외)",
    "자시 (23:30 ~ 01:30)",
    "축시 (01:30 ~ 03:30)",
    "인시 (03:30 ~ 05:30)",
    "묘시 (05:30 ~ 07:30)",
    "진시 (07:30 ~ 09:30)",
    "사시 (09:30 ~ 11:30)",
    "오시 (11:30 ~ 13:30)",
    "미시 (13:30 ~ 15:30)",
    "신시 (15:30 ~ 17:30)",
    "유시 (17:30 ~ 19:30)",
    "술시 (19:30 ~ 21:30)",
    "해시 (21:30 ~ 23:30)",
]

MYUNGRI_TIME_MAPPING = {
    "자시 (23:30 ~ 01:30)": datetime.time(0, 30),
    "축시 (01:30 ~ 03:30)": datetime.time(2, 30),
    "인시 (03:30 ~ 05:30)": datetime.time(4, 30),
    "묘시 (05:30 ~ 07:30)": datetime.time(6, 30),
    "진시 (07:30 ~ 09:30)": datetime.time(8, 30),
    "사시 (09:30 ~ 11:30)": datetime.time(10, 30),
    "오시 (11:30 ~ 13:30)": datetime.time(12, 30),
    "미시 (13:30 ~ 15:30)": datetime.time(14, 30),
    "신시 (15:30 ~ 17:30)": datetime.time(16, 30),
    "유시 (17:30 ~ 19:30)": datetime.time(18, 30),
    "술시 (19:30 ~ 21:30)": datetime.time(20, 30),
    "해시 (21:30 ~ 23:30)": datetime.time(22, 30),
}

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
    "양평군": -31, "가평군": -30, "연천군": -32,
    "홍천군": -29, "횡성군": -28, "영월군": -26, "평창군": -26, "정선군": -25, 
    "철원군": -31, "화천군": -30, "양구군": -28, "인제군": -27, "고성군(강원)": -26, "양양군": -25,
    "보은군": -29, "옥천군": -30, "영동군": -29, "증평군": -30, "진천군": -31, 
    "괴산군": -29, "음성군": -30, "단양군": -26,
    "금산군": -30, "부여군": -32, "서천군": -33, "청양군": -32, "홍성군": -33, "예산군": -33, "태안군": -35,
    "완주군": -31, "진안군": -30, "무주군": -29, "장수군": -29, "임실군": -31, "순창군": -31, "고창군": -33, "부안군": -33,
    "담양군": -32, "곡성군": -31, "구례군": -30, "고흥군": -31, "보성군": -32, "화순군": -32, "장흥군": -32, 
    "강진군": -33, "해남군": -34, "영암군": -34, "무안군": -34, "함평군": -34, "영광군": -34, "장성군": -33, 
    "완도군": -33, "진도군": -35, "신안군": -35,
    "군위군": -25, "의성군": -25, "청송군": -23, "영양군": -23, "영덕군": -22, "청도군": -25, "고령군": -26, 
    "성주군": -27, "칠곡군": -26, "예천군": -26, "봉화군": -25, "울진군": -22, "울릉군": -16,
    "의령군": -27, "함안군": -26, "창녕군": -26, "고성군(경남)": -27, "남해군": -28, "하동군": -29, 
    "산청군": -28, "함양군": -29, "거창군": -28, "합천군": -27,
    "강원도": -29, "경기도": -32, "충청북도": -29, "충청남도": -32,
    "전라북도": -31, "전라남도": -32, "경상북도": -26, "경상남도": -27, "제주도": -34,
    "보정 없음 (표준시 그대로 0분)": 0,
}

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
    return (L0 + C) % 360.0

def get_equation_of_time_minutes(jd):
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
    return math.degrees(E) * 4.0

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
    target_info = BRANCH_INFO[target_char] if is_branch else STEM_INFO[target_char]
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
    return sinsal_list[(target_idx - start_idx) % 12]

def get_historical_kst_correction_minutes(year, month, day):
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
            raise RuntimeError("음력 변환에 필요한 'korean_lunar_calendar' 패키지가 설치되어 있지 않습니다.")
        lunar_conv = KoreanLunarCalendar()
        try:
            lunar_conv.setLunarDate(year, month, day, is_leap)
        except Exception as e:
            raise ValueError(f"입력하신 음력 날짜({year}-{month}-{day})가 유효하지 않습니다: {e}")
        solar_year, solar_month, solar_day = lunar_conv.solarYear, lunar_conv.solarMonth, lunar_conv.solarDay

    h_val = hour if hour is not None else 12
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
        term_year = saju_year + 1 if lon == 285 else saju_year
        jeolgi_jds.append(find_solar_term_time(term_year, lon))

    next_ipchun_jd = find_solar_term_time(saju_year + 1, 315)
    month_idx = -1
    if birth_jd < jeolgi_jds[0]: 
        month_idx = 11 
    else:
        for m in range(11):
            if jeolgi_jds[m] <= birth_jd < jeolgi_jds[m + 1]:
                month_idx = m
                break
        if month_idx == -1 and jeolgi_jds[11] <= birth_jd < next_ipchun_jd:
            month_idx = 11
                
    year_stem_idx = year_diff % 10
    month_base_stem_idx = (year_stem_idx % 5 * 2 + 2) % 10
    month_stem_idx = (month_base_stem_idx + month_idx) % 10
    month_stem = STEMS_LIST[month_stem_idx]
    month_branch = MONTH_BRANCHES[month_idx]
    
    standard_dt = datetime.datetime(solar_year, solar_month, solar_day, h_val, minute)
    eot_minutes = get_equation_of_time_minutes(birth_jd)
    total_offset_mins = region_offset_mins - dst_offset_mins + historical_kst_correction_mins + eot_minutes
    lst_dt = standard_dt + datetime.timedelta(minutes=total_offset_mins)
    
    lst_year, lst_month, lst_day = lst_dt.year, lst_dt.month, lst_dt.day
    lst_hour, lst_minute = lst_dt.hour, lst_dt.minute
    
    base_date = datetime.date(1950, 1, 1)
    birth_date_lst = datetime.date(lst_year, lst_month, lst_day)
    
    is_next_day = False
    tot_min_lst = lst_hour * 60 + lst_minute
    if hour is not None:
        if time_boundary in ["선택 안 함(기본)", "조자시 적용 (00:00~00:30)"]:
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
        if tot_min_lst >= 1380 or tot_min_lst < 60: h_idx = 0  
        elif tot_min_lst < 180: h_idx = 1  
        elif tot_min_lst < 300: h_idx = 2  
        elif tot_min_lst < 420: h_idx = 3  
        elif tot_min_lst < 540: h_idx = 4  
        elif tot_min_lst < 660: h_idx = 5  
        elif tot_min_lst < 780: h_idx = 6  
        elif tot_min_lst < 900: h_idx = 7  
        elif tot_min_lst < 1020: h_idx = 8  
        elif tot_min_lst < 1140: h_idx = 9  
        elif tot_min_lst < 1260: h_idx = 10 
        else: h_idx = 11 
            
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
        daewoon_pillars.append((daewoon_num + (i - 1) * 10, pillar_str[0], pillar_str[-1]))
        
    return (year_stem, year_branch), (month_stem, month_branch), (day_stem, day_branch), hour_p, daewoon_num, daewoon_pillars, is_forward, lst_dt

def get_year_ganji(year):
    year_diff = year - 4
    return STEMS_LIST[year_diff % 10], BRANCHES_LIST[year_diff % 12]

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
    jijanggan = BRANCH_INFO[month_branch]['jijanggan']
    jeonggi_stem = max(jijanggan.items(), key=lambda x: x)[0]
    sipsin = determine_ten_deity(day_master, jeonggi_stem, is_branch=False)

    if sipsin in _GUCKGUK_BY_SIPSIN:
        name, desc = _GUCKGUK_BY_SIPSIN[sipsin]
        return {'name': name, 'desc': desc, 'jeonggi_stem': jeonggi_stem, 'sipsin': sipsin}

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

class AdvancedSajuAnalyzer:
    def __init__(self, name, sex, year_pillar, month_pillar, day_pillar, hour_pillar, daewoon_num, daewoon_pillars, birth_date=None, profile=None, compatibility=None):
        self.name = name
        self.sex = sex
        self.year = year_pillar
        self.month = month_pillar
        self.day = day_pillar
        self.hour = hour_pillar
        self.daewoon_num = daewoon_num
        self.birth_date = birth_date
        self.daewoon_pillars = daewoon_pillars
        self.profile = profile or {}
        self.compatibility = compatibility or {'requested': False}
        self.day_master = day_pillar[0]
        
        y_stem, y_branch = self.year
        m_stem, m_branch = self.month
        d_stem, d_branch = self.day
        
        self.y_stem = y_stem
        self.y_branch = y_branch
        self.m_stem = m_stem
        self.m_branch = m_branch
        self.d_stem = d_stem
        self.d_branch = d_branch
        
        self.stems = [y_stem, m_stem, d_stem]
        self.branches = [y_branch, m_branch, d_branch]
        if self.hour:
            h_stem, h_branch = self.hour
            self.h_stem = h_stem
            self.h_branch = h_branch
            self.stems.append(h_stem)
            self.branches.append(h_branch)
            
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
            'xing_hae': []
        }
        
        adjacent_stem_pairs = [
            ('년간-월간', self.y_stem, self.m_stem),
            ('월간-일간', self.m_stem, self.d_stem)
        ]
        if self.hour:
            adjacent_stem_pairs.append(('일간-시간', self.d_stem, self.h_stem))
            
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
                    
        adjacent_branch_pairs = [
            ('년지-월지', self.y_branch, self.m_branch),
            ('월지-일지', self.m_branch, self.d_branch)
        ]
        if self.hour:
            adjacent_branch_pairs.append(('일지-시지', self.d_branch, self.h_branch))
            
        for name, b1, b2 in adjacent_branch_pairs:
            if (b1, b2) in BRANCH_SIX_COMBINATIONS:
                target = BRANCH_SIX_COMBINATIONS[(b1, b2)]
                results['branch_six_comb'].append({
                    'pair': (b1, b2), 'position': name, 'target_element': target, 'desc': f"{name} {b1}·{b2} 육합{target}"
                })
            
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
            if other_elem != me_elem and RELATION_MAP.get((me_elem, other_elem)) == '인성':
                helpers.append(other_elem)

        season_info = get_season_multipliers(self.m_branch)
        weighted_scores = {elem: scores[elem] * season_info['multipliers'][elem] for elem in scores}
        total_score = sum(weighted_scores.values())
        helper_score = sum(weighted_scores[elem] for elem in helpers)
        helper_ratio = (helper_score / total_score) * 100 if total_score > 0 else 0

        if helper_ratio >= 45: strength = "신강(身强)"
        elif helper_ratio >= 35: strength = "중화(中和)"
        else: strength = "신약(身弱)"

        return {
            'strength': strength,
            'helper_score': helper_score,
            'helper_ratio': helper_ratio,
            'helper_elements': helpers,
            'season_info': season_info,
        }

    def determine_yongshin(self, adj_scores, strength_info):
        me_elem = STEM_INFO[self.day_master]['element']
        helpers = strength_info['helper_elements']
        if strength_info['strength'] == "신약(身弱)":
            other_helpers = [h for h in helpers if h != me_elem]
            if other_helpers:
                return me_elem if adj_scores[me_elem] > 0 else other_helpers[0]
            return me_elem
        else:
            opponents = [e for e in ['木', '火', '土', '金', '水'] if e not in helpers]
            return max(opponents, key=lambda x: adj_scores[x]) if opponents else "土"

    def compute_all(self):
        raw_scores = self.calculate_raw_element_scores()
        comb_results = self.detect_combinations_and_clashes()
        adj_scores, shift_logs = self.calculate_adjusted_element_scores(raw_scores, comb_results)
        raw_strength = self.analyze_strength(raw_scores)
        adj_strength = self.analyze_strength(adj_scores)

        eokbu_elem = self.determine_yongshin(adj_scores, adj_strength)
        johu_info = analyze_johu_yongshin(self.m_branch, adj_scores)
        tonggwan_info = analyze_tonggwan_yongshin(adj_scores)

        positions = ['년간', '년지', '월간', '월지', '일간(본인)', '일지']
        eight_chars_list = [
            (self.y_stem, False), (self.y_branch, True),
            (self.m_stem, False), (self.m_branch, True),
            (self.d_stem, False), (self.d_branch, True)
        ]
        if self.hour:
            positions.extend(['시간', '시지'])
            eight_chars_list.extend([(self.h_stem, False), (self.h_branch, True)])

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
                base_branch = self.d_branch if idx == 1 else self.y_branch
                sinsal_val = get_sinsal(base_branch, char)
                sinsal_list.append(sinsal_val)
                jijanggan_list.append(''.join(BRANCH_INFO[char]['jijanggan'].keys()))
            else:
                unseong_list.append("-")
                sinsal_list.append("-")
                jijanggan_list.append("-")

        month_deity = deities.get('월간', '')
        guckguk_info = determine_guckguk_by_wolji(self.day_master, self.m_branch)
        marriage_info = analyze_marriage_luck(month_deity, adj_scores, self.sex)
        wealth_info = analyze_wealth_luck(self.day_master, adj_scores, adj_strength['strength'])
        career_info = analyze_career_luck(self.day_master, adj_scores)

        year_ganji = self.y_stem + self.y_branch
        naeum_info = get_naeum_ohaeng(year_ganji)
        gongmang_info = calculate_gongmang(self.d_stem, self.d_branch)
        gongmang_branches = gongmang_info['branches']
        deukryeong_info = classify_deukryeong(UNSEONG_MAP[self.day_master].get(self.m_branch, '-'))

        dohwasal_info = check_dohwasal(self.d_branch, self.branches)
        yanginsal_info = check_yanginsal(self.day_master, UNSEONG_MAP, self.branches)
        goegangsal_info = check_goegangsal(self.d_stem + self.d_branch)
        cheoneul_info = check_cheoneul_gwiin(self.day_master, self.branches)
        munchang_info = check_munchang_gwiin(self.day_master, self.branches)
        wonjinsal_list = check_wonjinsal(self.branches)

        saeyun = None
        if self.birth_date is not None:
            today = datetime.date.today()
            current_age = today.year - self.birth_date.year + 1
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
            'meta': {
                'name': self.name, 'sex': self.sex,
                'birth_date': self.birth_date.isoformat() if self.birth_date else None,
                'has_hour': self.hour is not None,
                'saju_type': "사주팔자(四柱八字)" if self.hour else "사주삼주(三柱 - 시간모름)",
                'day_master': self.day_master,
            },
            'profile': {
                'marital_status': self.profile.get('marital_status'),
                'has_children': self.profile.get('has_children'),
                'job_status': self.profile.get('job_status'),
                'deep_question': self.profile.get('deep_question'),
            },
            'compatibility': self.compatibility,
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
        report = [
            "=" * 80,
            f"      [ {self.name} 님 정밀 사주명리 분석 자동화 V8 리포트 ]",
            "=" * 80,
            f"■ 성별 구별: {self.sex} 명식",
            f"■ 연산 형식: {d['meta']['saju_type']}",
            f"■ 일간 기질: 본인을 나타내는 기운은 {self.day_master}({STEM_INFO[self.day_master]['name']}) 기운입니다.",
            "=" * 80
        ]
        return "\n".join(report)

