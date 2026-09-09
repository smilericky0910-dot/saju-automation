# -*- coding: utf-8 -*-
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

from saju_engine import *

ELEMENT_COLORS = {
    '木': ('#e8f5e9', '#2e7d32'),
    '火': ('#ffebee', '#c62828'),
    '土': ('#fff8e1', '#a66a00'),
    '金': ('#f5f5f5', '#555555'),
    '水': ('#e3f2fd', '#1565c0'),
}

def _ohaeng_band_label(pct):
    if pct < 5: return '부족'
    elif pct < 15: return '약함'
    elif pct < 30: return '적정'
    elif pct < 40: return '발달'
    return '과다'

def _sipsin_distribution(analyzer):
    order = ['비견', '겁재', '식신', '상관', '편재', '정재', '편관', '정관', '편인', '정인']
    counts = {k: 0 for k in order}
    for s in analyzer.stems:
        if s != analyzer.day_master:
            counts[determine_ten_deity(analyzer.day_master, s, False)] += 1
    for b in analyzer.branches:
        counts[determine_ten_deity(analyzer.day_master, b, True)] += 1
    total = sum(counts.values()) or 1
    return order, counts, total

def _pillar_card_html(label, stem, stem_deity, branch, branch_deity, jijanggan, unseong, sinsal):
    s_bg, s_fg = ELEMENT_COLORS[STEM_INFO[stem]['element']]
    b_bg, b_fg = ELEMENT_COLORS[BRANCH_INFO[branch]['element']]
    
    k_stem = STEM_INFO[stem]['name'][0]
    k_branch = BRANCH_INFO[branch]['k_name'][0]
    
    return f"""
    <div style="border:1px solid #e0e0e0;border-radius:12px;padding:10px 6px;text-align:center;background:#fff;">
      <div style="font-size:12px;color:#888;margin-bottom:6px;">{label}</div>
      <div style="background:{s_bg};color:{s_fg};border-radius:8px;padding:10px 2px;font-size:22px;font-weight:800;margin-bottom:4px;letter-spacing:1px;">{k_stem}{stem}</div>
      <div style="font-size:11px;color:#666;margin-bottom:8px;">{stem_deity}</div>
      <div style="background:{b_bg};color:{b_fg};border-radius:8px;padding:10px 2px;font-size:22px;font-weight:800;margin-bottom:4px;letter-spacing:1px;">{k_branch}{branch}</div>
      <div style="font-size:11px;color:#666;margin-bottom:6px;">{branch_deity}</div>
      <div style="font-size:10px;color:#aaa;">지장간 {jijanggan}</div>
      <div style="font-size:10px;color:#aaa;">{unseong} · {sinsal}</div>
    </div>
    """

def render_input_screen():
    st.markdown("""
        <style>
        .header-box h1, .header-box h4 {
            color: #ffffff !important;
        }
        </style>
        <div class="header-box" style='background-color:#2b2926; padding:1rem 2rem; border-radius:10px; margin-bottom:1.2rem; text-align:center;'>
            <h4 style='margin-top:0; margin-bottom:4px; font-size:16px;'>답답명쾌 사주 해답소</h4>
            <h1 style='margin-top:0; margin-bottom:0; font-size:26px;'>⚡ 퀵 사주 카톡 / 스레드</h1>
        </div>
    """, unsafe_allow_html=True)
    


    st.markdown("<h3 style='font-size:22px; margin-bottom:10px; color:#222;'>👤 신청자 기본 정보</h3>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("<div style='font-size:16px; font-weight:bold; margin-bottom:8px; color:#222;'>성명 (이름) <span style='color:red;font-size:14px;'>* (필수)</span></div>", unsafe_allow_html=True)
        name = st.text_input("이름", value="", max_chars=12, placeholder="예: 홍길동", label_visibility="collapsed")
    with col2:
        st.markdown("<div style='font-size:16px; font-weight:bold; margin-bottom:8px; color:#222;'>성별 <span style='color:red;font-size:14px;'>* (필수)</span></div>", unsafe_allow_html=True)
        sex = st.radio("성별 선택", ["남자", "여자"], horizontal=True, label_visibility="collapsed")
        sex_internal = "남성" if "남자" in sex else "여성"

    st.markdown("<br><h3 style='font-size:22px; margin-bottom:10px; color:#222;'>📅 생년월일 및 출생시 (사주 원국 산출)</h3>", unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns([15, 12, 10, 10])
    with col1:
        st.markdown("<div style='font-size:16px; font-weight:bold; margin-bottom:8px; color:#222;'>양력 / 음력 <span style='color:red;font-size:14px;'>* (필수)</span></div>", unsafe_allow_html=True)
        calendar_type = st.selectbox("양력/음력", ["양력(Solar)", "음력(Lunar)", "음력 윤달(Leap)"], label_visibility="collapsed")
    with col2:
        st.markdown("<div style='font-size:16px; font-weight:bold; margin-bottom:8px; color:#222;'>년도 <span style='color:red;font-size:14px;'>*</span></div>", unsafe_allow_html=True)
        current_year = datetime.datetime.now().year
        year_options = [f"{y}년" for y in range(current_year, current_year - 101, -1)]
        selected_year = st.selectbox("년", year_options, index=year_options.index("1990년"), label_visibility="collapsed")
    with col3:
        st.markdown("<div style='font-size:16px; font-weight:bold; margin-bottom:8px; color:#222;'>월 <span style='color:red;font-size:14px;'>*</span></div>", unsafe_allow_html=True)
        month_options = [f"{m}월" for m in range(1, 13)]
        selected_month = st.selectbox("월", month_options, index=0, label_visibility="collapsed")
    with col4:
        st.markdown("<div style='font-size:16px; font-weight:bold; margin-bottom:8px; color:#222;'>일 <span style='color:red;font-size:14px;'>*</span></div>", unsafe_allow_html=True)
        day_options = [f"{d}일" for d in range(1, 32)]
        selected_day = st.selectbox("일", day_options, index=0, label_visibility="collapsed")
    
    col_t1, col_t2 = st.columns([1, 1])
    with col_t1:
        st.markdown("<div style='font-size:16px; font-weight:bold; margin-top:15px; margin-bottom:8px; color:#222;'>🕒 태어난 시간 <span style='color:red;font-size:14px;'>* (필수)</span></div>", unsafe_allow_html=True)
        time_selection = st.selectbox("태어난 시간 유형", MYUNGRI_TIME_OPTIONS, index=0, label_visibility="collapsed")
        
        if time_selection == "시간 모름 (선택 시 시간 제외)":
            birth_time = datetime.time(12, 0)
            time_unknown = True
        else:
            birth_time = MYUNGRI_TIME_MAPPING[time_selection]
            time_unknown = False
            
    with col_t2:
        st.markdown("<div style='margin-top:45px;'></div>", unsafe_allow_html=True)
        use_jasi_option = st.checkbox("야자시/조자시 적용 (23:30~24:00)")
    
    y_val = int(selected_year.replace("년", ""))
    m_val = int(selected_month.replace("월", ""))
    d_val = int(selected_day.replace("일", ""))
    try:
        birth_date = datetime.date(y_val, m_val, d_val)
    except ValueError:
        birth_date = datetime.date(1990, 1, 1)
        
    is_lunar = "음력" in calendar_type
    is_leap = "윤달" in calendar_type
    

        
    time_boundary = "야자시 적용 (23:30~24:00)" if use_jasi_option else "표준 자시(기본)"

    st.markdown("<br><div style='font-size:16px; font-weight:bold; margin-bottom:8px; color:#222;'>출생 도시 (태어난 지역) <span style='color:red;font-size:14px;'>* (필수)</span></div>", unsafe_allow_html=True)
    city_options = list(CITY_LONGITUDE_OFFSETS.keys()) + ["직접입력(해외 등)"]
    city = st.selectbox("도시명", city_options, index=city_options.index("서울특별시"), label_visibility="collapsed")
    if city == "직접입력(해외 등)":
        region_offset_mins = st.slider("경도 보정(분)", -45, 0, -30)
    else:
        region_offset_mins = CITY_LONGITUDE_OFFSETS[city]
        
    phone = ""
    email = ""

    st.markdown("<br><h3 style='font-size:22px; margin-bottom:10px; color:#222;'>❓ 상담받고 싶은 고민 / 가장 궁금한 점 <span style='color:red;font-size:14px;'>* (필수)</span></h3>", unsafe_allow_html=True)
    deep_question = st.text_area("고객 고민", placeholder="예: 올해 하반기 이직운과 재물 흐름이 궁금합니다. (특별한 고민이 없으신 경우 '없음'으로 적어주세요)", height=100, label_visibility="collapsed")

    st.markdown("<br><h3 style='font-size:22px; margin-bottom:10px; color:#222;'>💕 궁합 분석 (선택)</h3>", unsafe_allow_html=True)
    want_compat = st.checkbox("궁합 분석을 함께 신청할게요")
    compat_type = partner_name = partner_sex = partner_city = None
    partner_birth_known = False
    partner_is_lunar = partner_is_leap = False
    partner_date = None
    partner_time_unknown = True
    partner_time = None
    if want_compat:
        compat_type = st.radio("궁합 유형", ["연인·배우자 궁합", "재회 궁합", "반려동물 궁합", "기타"], horizontal=True, key="compat_type")
        if compat_type == "기타":
            compat_type_custom = st.text_input("궁합 유형을 직접 입력해주세요", placeholder="예: 동성 커플, 친구, 사업 파트너 등", key="compat_type_custom")
            if compat_type_custom.strip():
                compat_type = f"기타 ({compat_type_custom.strip()})"
        partner_label = "반려동물" if compat_type == "반려동물 궁합" else "상대방"
        pcol1, pcol2 = st.columns(2)
        with pcol1:
            partner_name = st.text_input(f"{partner_label} 이름", key="partner_name")
        with pcol2:
            partner_sex = st.radio(f"{partner_label} 성별", ["여자", "남자", "모름"], horizontal=True, key="partner_sex")

        partner_birth_known = st.checkbox("생년월일을 알아요", key="partner_birth_known")
        if partner_birth_known:
            qcol1, qcol2, qcol3, qcol4, qcol5 = st.columns([15, 12, 10, 10, 18])
            with qcol1:
                p_calendar_type = st.selectbox("양력/음력", ["양력", "음력", "음력(윤달)"], key="partner_calendar_type", label_visibility="collapsed")
            with qcol2:
                p_selected_year = st.selectbox("년", year_options, index=year_options.index("1990년"), key="partner_year", label_visibility="collapsed")
            with qcol3:
                p_selected_month = st.selectbox("월", month_options, index=0, key="partner_month", label_visibility="collapsed")
            with qcol4:
                p_selected_day = st.selectbox("일", day_options, index=0, key="partner_day", label_visibility="collapsed")
            with qcol5:
                pass

            partner_is_lunar = p_calendar_type in ["음력", "음력(윤달)"]
            partner_is_leap = p_calendar_type == "음력(윤달)"
            p_y = int(p_selected_year.replace("년", ""))
            p_m = int(p_selected_month.replace("월", ""))
            p_d = int(p_selected_day.replace("일", ""))
            try:
                partner_date = datetime.date(p_y, p_m, p_d)
            except ValueError:
                partner_date = datetime.date(1990, 1, 1)

            st.markdown(f"<div style='font-size:16px; font-weight:bold; margin-top:10px; margin-bottom:8px; color:#222;'>🕒 {partner_label} 태어난 시간</div>", unsafe_allow_html=True)
            p_time_selection = st.selectbox(f"{partner_label} 태어난 시간 유형", MYUNGRI_TIME_OPTIONS, index=0, key="p_time_select", label_visibility="collapsed")
            if p_time_selection == "시간 모름 (선택 시 시간 제외)":
                partner_time = None
                partner_time_unknown = True
            else:
                partner_time = MYUNGRI_TIME_MAPPING[p_time_selection]
                partner_time_unknown = False

            partner_city_options = ["선택 안 함"] + list(CITY_LONGITUDE_OFFSETS.keys())
            partner_city = st.selectbox(f"{partner_label} 태어난 도시", partner_city_options, key="partner_city")
            if partner_city == "선택 안 함":
                partner_city = None

    st.write("")
    if st.button("고객정보 입력완료", type="secondary", use_container_width=True):
        if not name.strip():
            st.error("이름을 입력해주세요.")
            return
        st.session_state.show_confirm = True
        
    if st.session_state.get('show_confirm', False):
        st.markdown("---")
        st.markdown("<h3 style='text-align:center;'>✅ 입력 정보 최종 확인</h3>", unsafe_allow_html=True)
        cal_str = ("음력(윤달)" if is_leap else "음력") if is_lunar else "양력"
        time_str = "모름" if time_unknown else birth_time.strftime('%H:%M')
        
        table_html = f"""
        <table style="width: 100%; max-width: 600px; margin: 0 auto; border-collapse: collapse; text-align: left; background-color: white; border: 1px solid #e0e0e0; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
            <tr style="border-bottom: 1px solid #e0e0e0;"><th style="padding: 12px; width: 30%; background-color: #f7f9fa; border-right: 1px solid #e0e0e0;">이름</th><td style="padding: 12px;">{name}</td></tr>
            <tr style="border-bottom: 1px solid #e0e0e0;"><th style="padding: 12px; background-color: #f7f9fa; border-right: 1px solid #e0e0e0;">성별</th><td style="padding: 12px;">{sex}</td></tr>
            <tr style="border-bottom: 1px solid #e0e0e0;"><th style="padding: 12px; background-color: #f7f9fa; border-right: 1px solid #e0e0e0;">생년월일</th><td style="padding: 12px;">{birth_date.strftime('%Y년 %m월 %d일')} ({cal_str})</td></tr>
            <tr style="border-bottom: 1px solid #e0e0e0;"><th style="padding: 12px; background-color: #f7f9fa; border-right: 1px solid #e0e0e0;">태어난 시간</th><td style="padding: 12px;">{time_str} ({time_boundary})</td></tr>
            <tr style="border-bottom: 1px solid #e0e0e0;"><th style="padding: 12px; background-color: #f7f9fa; border-right: 1px solid #e0e0e0;">출생 도시</th><td style="padding: 12px;">{city} (보정: {region_offset_mins}분)</td></tr>
            <tr><th style="padding: 12px; background-color: #f7f9fa; border-right: 1px solid #e0e0e0;">고객 고민</th><td style="padding: 12px;">{deep_question if deep_question.strip() else '없음'}</td></tr>
        </table><br/>
        """
        st.markdown(table_html, unsafe_allow_html=True)

        if want_compat:
            partner_label = "반려동물" if compat_type == "반려동물 궁합" else "상대방"
            if partner_birth_known and partner_date:
                p_cal_str = ("음력(윤달)" if partner_is_leap else "음력") if partner_is_lunar else "양력"
                p_time_str = "모름" if partner_time_unknown else partner_time.strftime('%H:%M')
                birth_row = f"{partner_date.strftime('%Y년 %m월 %d일')} ({p_cal_str}) / {p_time_str}"
            else:
                birth_row = "모름 (참고용 정보만으로 분석)"
            compat_table_html = f"""
            <table style="width: 100%; max-width: 600px; margin: 0 auto; border-collapse: collapse; text-align: left; background-color: white; border: 1px solid #e0e0e0; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                <tr style="border-bottom: 1px solid #e0e0e0;"><th style="padding: 12px; width: 30%; background-color: #f7f9fa; border-right: 1px solid #e0e0e0;">궁합 유형</th><td style="padding: 12px;">{compat_type}</td></tr>
                <tr style="border-bottom: 1px solid #e0e0e0;"><th style="padding: 12px; background-color: #f7f9fa; border-right: 1px solid #e0e0e0;">{partner_label} 이름</th><td style="padding: 12px;">{partner_name.strip() if partner_name and partner_name.strip() else '없음'}</td></tr>
                <tr style="border-bottom: 1px solid #e0e0e0;"><th style="padding: 12px; background-color: #f7f9fa; border-right: 1px solid #e0e0e0;">{partner_label} 성별</th><td style="padding: 12px;">{partner_sex}</td></tr>
                <tr><th style="padding: 12px; background-color: #f7f9fa; border-right: 1px solid #e0e0e0;">{partner_label} 생년월일</th><td style="padding: 12px;">{birth_row}</td></tr>
            </table><br/>
            """
            st.markdown("<h4 style='text-align:center;'>💕 궁합 분석 정보</h4>", unsafe_allow_html=True)
            st.markdown(compat_table_html, unsafe_allow_html=True)

        if st.button("🚀 고객정보입력 완료", type="primary", use_container_width=True):
            # 양력 날짜 유효성 검증
            if not is_lunar:
                try:
                    datetime.date(y_val, m_val, d_val)
                except ValueError:
                    st.error(f"❌ 선택하신 양력 날짜({y_val}년 {m_val}월 {d_val}일)는 유효하지 않은 날짜입니다.")
                    return

            # 파트너 양력 날짜 유효성 검증
            if want_compat and partner_birth_known and not partner_is_lunar:
                try:
                    datetime.date(p_y, p_m, p_d)
                except ValueError:
                    st.error(f"❌ 상대방 양력 날짜({p_y}년 {p_m}월 {p_d}일)는 유효하지 않은 날짜입니다.")
                    return

            # 음력 날짜 유효성 검증
            if is_lunar and LUNAR_CALENDAR_AVAILABLE:
                try:
                    # 입력 음력 → 양력 → 음력 변환으로 유효성 확인
                    test_cal = KoreanLunarCalendar()
                    test_cal.setLunarDate(y_val, m_val, d_val, is_leap)
                    solar_y, solar_m, solar_d = test_cal.solarYear, test_cal.solarMonth, test_cal.solarDay

                    # 다시 음력으로 역변환
                    verify_cal = KoreanLunarCalendar()
                    verify_cal.setSolarDate(solar_y, solar_m, solar_d)

                    # 원래 입력과 다르면 유효하지 않은 날짜
                    if (verify_cal.lunarYear != y_val or verify_cal.lunarMonth != m_val or
                        verify_cal.lunarDay != d_val or verify_cal.isIntercalation != is_leap):
                        st.error(f"❌ 선택하신 음력 날짜({y_val}년 {m_val}월 {d_val}일{'(윤달)' if is_leap else ''})는 유효하지 않은 날짜입니다. 그 달은 {verify_cal.lunarDay}일까지만 있습니다.")
                        return
                except Exception as e:
                    st.error(f"❌ 음력 날짜 검증 중 오류 발생: {e}")
                    return

            # 파트너 음력 날짜 유효성 검증
            if want_compat and partner_birth_known and partner_is_lunar and LUNAR_CALENDAR_AVAILABLE:
                try:
                    # 입력 음력 → 양력 → 음력 변환으로 유효성 확인
                    test_cal = KoreanLunarCalendar()
                    test_cal.setLunarDate(p_y, p_m, p_d, partner_is_leap)
                    solar_y, solar_m, solar_d = test_cal.solarYear, test_cal.solarMonth, test_cal.solarDay

                    # 다시 음력으로 역변환
                    verify_cal = KoreanLunarCalendar()
                    verify_cal.setSolarDate(solar_y, solar_m, solar_d)

                    # 원래 입력과 다르면 유효하지 않은 날짜
                    if (verify_cal.lunarYear != p_y or verify_cal.lunarMonth != p_m or
                        verify_cal.lunarDay != p_d or verify_cal.isIntercalation != partner_is_leap):
                        st.error(f"❌ 상대방 음력 날짜({p_y}년 {p_m}월 {p_d}일{'(윤달)' if partner_is_leap else ''})는 유효하지 않은 날짜입니다.")
                        return
                except Exception as e:
                    st.error(f"❌ 상대방 음력 날짜 검증 중 오류 발생: {e}")
                    return

            data = {
                'name': name.strip(), 'sex': sex_internal, 'is_lunar': is_lunar, 'is_leap': is_leap,
                'time_unknown': time_unknown, 'birth_date': birth_date, 'birth_time': birth_time if not time_unknown else None,
                'city': city, 'region_offset_mins': region_offset_mins,
                'dst_auto': True, 'time_boundary': time_boundary,
                'profile': {
                    'marital_status': None, 'has_children': None, 'job_status': None,
                    'deep_question': deep_question.strip() if deep_question.strip() else None,
                },
                'contact': {},
                'original_birth_str': f"{birth_date.strftime('%Y년 %m월 %d일')} ({cal_str})",
                'compatibility': {'requested': False},
            }
            st.session_state.input_data = data
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
                saju_data['meta'] = saju_data.get('meta', {})
                saju_data['meta']['original_birth_str'] = data.get('original_birth_str')

                compat_out = {'requested': False}
                if want_compat:
                    compat_out = {
                        'requested': True, 'type': compat_type,
                        'partner_name': (partner_name.strip() or None) if partner_name else None,
                        'partner_sex': partner_sex if partner_sex != "모름" else None,
                        'partner_city': partner_city, 'partner_saju': None,
                    }
                    if partner_birth_known and partner_date and partner_sex in ("여자", "남자"):
                        try:
                            p_hour = partner_time.hour if (not partner_time_unknown and partner_time) else None
                            p_minute = partner_time.minute if (not partner_time_unknown and partner_time) else 0
                            p_sex_internal = "남성" if partner_sex == "남자" else "여성"
                            p_region_offset = CITY_LONGITUDE_OFFSETS.get(partner_city, 0) if partner_city else 0
                            py, pm, pd_, ph, p_daewoon_num, p_daewoon_pillars, _, p_lst_dt = convert_to_pillars(
                                partner_date.year, partner_date.month, partner_date.day, p_hour, p_minute,
                                partner_is_lunar, partner_is_leap, p_sex_internal, "표준 자시(기본)", p_region_offset, 0,
                            )
                            partner_analyzer = AdvancedSajuAnalyzer(
                                (partner_name.strip() if partner_name and partner_name.strip() else "상대방"),
                                p_sex_internal, py, pm, pd_, ph, p_daewoon_num, p_daewoon_pillars,
                                birth_date=p_lst_dt.date(),
                            )
                            compat_out['partner_saju'] = partner_analyzer.compute_all()
                        except Exception:
                            compat_out['partner_saju'] = None
                saju_data['compatibility'] = compat_out
                st.session_state.saju_data = saju_data
                
                st.info("⚠️ **안내**: 분석을 즉시 중단하려면 화면 우측 상단의 **[정지(Stop)]** 버튼을 누르거나 키보드의 **ESC** 키를 누르세요.")
                with st.spinner("우주와 교감하며 사주 명식을 심층 분석 중입니다... 🌌 (약 1분 소요)"):
                    report_text = analyzer.generate_detailed_report()
                    st.session_state.report_text = report_text
                
                # 분석 직후 백업 저장
                try:
                    import json, os
                    backup_data = {
                        "saju_data": saju_data,
                        "report_text": report_text,
                        "analyzer_name": analyzer.name,
                        "analyzer_sex": analyzer.sex,
                        "analyzer_hour": analyzer.hour,
                        "analyzer_day_master": analyzer.day_master,
                        "input_data_birth_date": data['birth_date'].strftime('%Y-%m-%d')
                    }
                    with open("last_analysis_backup.json", "w", encoding="utf-8") as f:
                        json.dump(backup_data, f, ensure_ascii=False)
                except Exception as e:
                    print("백업 실패:", e)

                st.session_state.step = 'result'
                st.rerun()
            except Exception as e:
                st.error(f"입력하신 정보로 사주를 계산할 수 없습니다: {e}")

def _get_config(key):
    try:
        val = st.secrets.get(key)
    except Exception:
        val = None
    return val or os.environ.get(key)



def render_result_screen():
    analyzer = st.session_state.analyzer
    d = st.session_state.saju_data
    input_data = st.session_state.get('input_data', {})

    st.header(f"🔮 {analyzer.name} 님의 사주 정보")
    saju_type = "사주팔자(四柱八字)" if analyzer.hour else "사주삼주(三柱 - 시간모름)"
    st.caption(f"{analyzer.sex} · {saju_type} · 일간 {analyzer.day_master}({STEM_INFO[analyzer.day_master]['name']})")

    st.write("---")
    st.markdown("<h3 style='text-align:center;'>⚡ 퀵사주 카톡 / 스레드용 풀이</h3>", unsafe_allow_html=True)
    
    if st.button("✨ 풀이 생성하기", type="primary", use_container_width=True):
        api_key = _get_config("ANTHROPIC_API_KEY")
        if not api_key:
            st.error("API 키가 설정되지 않았습니다. .env 파일을 확인해주세요.")
        else:
            st.session_state.quick_result = None
            with st.spinner("AI 명리학자가 사주를 분석하며 해설을 작성 중입니다... (5~10초 소요)"):
                try:
                    from quick_report_generator import generate_quick_report
                    question = input_data.get('profile', {}).get('deep_question', '없음')
                    result = generate_quick_report(d, question, api_key)
                    st.session_state.quick_result = result
                except Exception as e:
                    st.error(f"풀이 생성 오류: {e}")
                    
    if st.session_state.get('quick_result'):
        res_text = st.session_state.quick_result
        
        if "[PART 1]" in res_text and "[PART 2]" in res_text:
            parts = res_text.split("[PART 2]")
            part1 = parts[0].replace("[PART 1]", "").strip()
            part2 = parts[1].strip()
            
            st.markdown("---")
            st.markdown("#### 💬 카톡 전송용 풀이")
            st.markdown(
                f"<div style='background:#f0f8ff; border-left:4px solid #4a90d9; border-radius:8px; padding:16px 20px; white-space:pre-wrap; font-size:15px; line-height:1.8;'>{part1}</div>",
                unsafe_allow_html=True
            )
            st.write("")
            st.markdown("#### 📱 스레드(Threads) 전용 숏폼")
            st.markdown(
                f"<div style='background:#fff8e1; border-left:4px solid #f0a500; border-radius:8px; padding:16px 20px; white-space:pre-wrap; font-size:15px; line-height:1.8;'>{part2}</div>",
                unsafe_allow_html=True
            )
        else:
            st.markdown("---")
            st.markdown("#### 💬 퀵 풀이 결과")
            st.markdown(
                f"<div style='background:#f0f8ff; border-left:4px solid #4a90d9; border-radius:8px; padding:16px 20px; white-space:pre-wrap; font-size:15px; line-height:1.8;'>{res_text}</div>",
                unsafe_allow_html=True
            )

    st.write("---")
    st.caption("아래는 참고용 요약 화면입니다.")

    pos_idx = {p: i for i, p in enumerate(d['positions'])}
    def branch_meta(pos_key):
        i = pos_idx[pos_key]
        return d['unseong_list'][i], d['sinsal_list'][i], d['jijanggan_list'][i]

    pillars = []
    if analyzer.hour:
        h_s, h_b = analyzer.hour
        pillars.append(('시주', h_s, h_b, '시간', '시지'))
    d_s, d_b = analyzer.day
    pillars.append(('일주', d_s, d_b, None, '일지'))
    m_s, m_b = analyzer.month
    pillars.append(('월주', m_s, m_b, '월간', '월지'))
    y_s, y_b = analyzer.year
    pillars.append(('년주', y_s, y_b, '년간', '년지'))

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
        st.markdown(f"**격국(格局)**  \n{d['guckguk_info']['name']}")
    with c2:
        gm = d['gongmang_info']
        st.markdown(f"**공망(空亡)**  \n{'·'.join(gm['branches']) if gm['branches'] else '-'}")
        st.markdown(f"**월령(月令)**  \n{d['deukryeong_info']['status']}")

    st.write("---")
    st.markdown("<h4 style='color:#333; margin-bottom:5px; font-size:18px;'>📊 오행 및 십성 비율</h4>", unsafe_allow_html=True)
    
    adj = d['adj_scores']
    total_ohaeng = sum(adj.values()) or 1
    ohaeng_html = "<div style='display:flex; justify-content:space-around; font-size:14px; background:#f9f9f9; padding:10px; border-radius:8px; margin-bottom:10px; border:1px solid #eee;'>"
    for elem in ['木', '火', '土', '金', '水']:
        pct = adj[elem] / total_ohaeng * 100
        lbl = _ohaeng_band_label(pct)
        bg, fg = ELEMENT_COLORS[elem]
        ohaeng_html += f"<div style='text-align:center;'><div style='font-weight:bold; color:{fg}; font-size:16px;'>{elem}</div><div style='color:#444;'>{pct:.0f}%</div><div style='font-size:11px;color:#888;'>{lbl}</div></div>"
    ohaeng_html += "</div>"
    
    order, sipsin_counts, sipsin_total = _sipsin_distribution(analyzer)
    sipsin_html = "<div style='display:flex; flex-wrap:wrap; justify-content:center; gap:8px; font-size:12px; background:#f9f9f9; padding:10px; border-radius:8px; border:1px solid #eee;'>"
    for name10 in order:
        pct = sipsin_counts[name10] / sipsin_total * 100
        color = "#222" if pct > 0 else "#ccc"
        sipsin_html += f"<div style='width:18%; text-align:center; color:{color};'><span style='font-weight:bold;'>{name10}</span> {pct:.0f}%</div>"
    sipsin_html += "</div>"
    
    st.markdown(ohaeng_html + sipsin_html, unsafe_allow_html=True)

    st.write("---")
    st.subheader("신강신약")
    strength = d['adj_strength']
    season = strength['season_info']
    season_line = " ".join(f"{e}({season['status_by_element'][e]})" for e in ['木', '火', '土', '金', '水'])
    st.markdown(f"### {strength['strength']}")
    st.caption(f"월령 가중 반영 비율 {strength['helper_ratio']:.1f}% (아군 기운: {'·'.join(strength['helper_elements'])})")
    st.caption(f"월령 왕상휴수사: {season_line}")

    st.subheader("용신(用神)")
    st.markdown(f"- **억부용신**: {d['eokbu_elem']}")
    if d['johu_info']['needed']:
        urgent_tag = " (시급)" if d['johu_info'].get('urgent') else ""
        st.markdown(f"- **조후용신**: {d['johu_info']['element']}{urgent_tag}")
    if d['tonggwan_info']['needed']:
        st.markdown(f"- **통관용신**: {d['tonggwan_info']['element']}")

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
    if s['dohwa']['exists']: badges.append('도화살')
    if s['yangin']['exists']: badges.append('양인살')
    if s['goegang']['exists']: badges.append('괴강살')
    if s['cheoneul']['exists']: badges.append('천을귀인')
    if s['munchang']['exists']: badges.append('문창귀인')
    for w in s['wonjin']: badges.append(w['name'])
    if badges:
        st.markdown(" ".join(f"`{b}`" for b in badges))
    else:
        st.caption("해당하는 주요 신살이 없습니다.")

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
        page_title="답답명쾌 사주해답소",
        page_icon="🔮",
        layout="centered",
        initial_sidebar_state="collapsed",
    )
    st.markdown("""
        <style>
        .stApp { background-color: #ffffff; color: #222222; }
        .stTextInput>div>div>input, .stTextArea textarea { background-color: #ffffff; color: #222222; border: 1px solid #e0a800; border-radius: 5px; }
        .stSelectbox>div>div>div { background-color: #ffffff; color: #222222; border: 1px solid #e0a800; border-radius: 5px; }
        .stButton>button { background-color: #ffcd4a; color: #222222; font-weight: bold; border-radius: 5px; border: none; width: 100%; }
        h1, h2, h3, p, label { color: #222222 !important; }
        .stAlert { background-color: rgba(255, 205, 74, 0.15); color: #222222; }
        @media (max-width: 480px) {
            .block-container { padding-left: 1rem; padding-right: 1rem; }
        }
        </style>
    """, unsafe_allow_html=True)

    if 'step' not in st.session_state:
        st.session_state.step = 'input'

    if st.session_state.step == 'input':
        render_input_screen()
    elif st.session_state.step == 'result':
        render_result_screen()
    else:
        st.session_state.step = 'input'
        st.rerun()

if __name__ == "__main__":
    main()