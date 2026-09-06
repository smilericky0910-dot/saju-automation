# -*- coding: utf-8 -*-
"""
[답답명쾌 사주해답소] 고객 신청서 & 사장님 전용 히든 관리자 시스템
- 손님 화면: 관리자 버튼 완전 제거, 밝은 모드 강제 고정, 심층 사주풀이 신청서만 표시
- 사장님 화면: URL 뒤에 ?admin=true 접속 시 비밀번호 입력창 오픈
"""

import streamlit as st
import requests
import pandas as pd
import datetime
import calendar
import time
import os
import json

# 사장님 기존 사주 엔진 모듈 불러오기
from dabdab_saju_app import (
    convert_to_pillars,
    AdvancedSajuAnalyzer,
    get_dst_offset_minutes,
    CITY_LONGITUDE_OFFSETS
)
from saju_report_generator import generate_saju_report
from saju_pdf_renderer import render_saju_report_pdf
import gdrive_uploader
from saju_alimtalk import schedule_saju_alimtalk_3hours_later

# -----------------------------------------------------------------------------
# 1. 페이지 기본 설정 (모바일 최적화)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="답답명쾌 사주해답소 | 심층 사주풀이",
    page_icon="🔮",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# 구글 시트 웹앱 URL
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbxFPVPgYvx3q-saacm0OkUuELMb-GomV5UDLTVUGRrSuzxDCQdXywyPePQqVhRxJz25Kw/exec"

# 관리자 비밀번호
ADMIN_PASSWORD = "1234"

ADMIN_CITY_OFFSETS = {
    "서울": -32, "경기/인천": -32, "부산": -24, "대구": -26, "대전": -30,
    "광주": -33, "울산": -23, "강원": -28, "충청": -31, "전라": -32,
    "경상": -25, "제주": -34, "해외": 0
}

# -----------------------------------------------------------------------------
# 2. 스타일 CSS (다크모드 원천 차단, 밝은 모드 강제 고정, 상단 메뉴 숨김)
# -----------------------------------------------------------------------------
st.markdown("""
<style>
    /* 1. 스트림릿 기본 상단 헤더 및 메뉴(다크모드 선택창) 숨기기 */
    #MainMenu {visibility: hidden !important;}
    header {visibility: hidden !important;}
    footer {visibility: hidden !important;}

    /* 2. 전체 배경 밝은 모드 강제 고정 */
    html, body, [data-testid="stAppViewContainer"] {
        background-color: #f4f4f7 !important;
        color: #18181b !important;
    }

    /* 3. 모바일 카드형 레이아웃 (480px) */
    .block-container {
        max-width: 480px !important;
        margin: 15px auto !important;
        padding: 24px 18px !important;
        background-color: #ffffff !important;
        border-radius: 18px !important;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05) !important;
        border: 1px solid #e4e4e7 !important;
    }

    @media (max-width: 520px) {
        .block-container {
            max-width: 100% !important;
            margin: 0 !important;
            padding: 16px 14px !important;
            border-radius: 0 !important;
            box-shadow: none !important;
            border: none !important;
        }
    }

    /* 4. 상단 배너 (가운데 정렬) */
    .banner-box {
        background: linear-gradient(135deg, #1c1917 0%, #292524 100%);
        color: #fafaf9;
        padding: 24px 18px;
        border-radius: 14px;
        margin-bottom: 20px;
        text-align: center !important;
        border-top: 4px solid #d97706;
    }
    .banner-badge {
        font-size: 12.5px;
        font-weight: 600;
        color: #f59e0b;
        margin-bottom: 6px;
        text-align: center !important;
    }
    .banner-title {
        font-size: 24px;
        font-weight: 800;
        color: #ffffff;
        margin-bottom: 8px;
        font-family: 'Noto Serif KR', serif;
        text-align: center !important;
    }
    .banner-desc {
        font-size: 12.5px;
        color: #d6d3d1;
        line-height: 1.6;
        text-align: center !important;
        word-break: keep-all;
    }

    .section-title {
        font-size: 15px;
        font-weight: 700;
        color: #18181b !important;
        margin-top: 16px;
        margin-bottom: 10px;
    }

    /* 모든 라벨 및 텍스트 밝은색 유지 */
    label, p, span, div {
        color: #18181b !important;
    }
    .banner-box * {
        color: #fafaf9 !important;
    }
    .banner-badge {
        color: #f59e0b !important;
    }

    /* 배지 스타일 */
    .status-badge {
        padding: 3px 8px;
        border-radius: 9999px;
        font-size: 11px;
        font-weight: 700;
        display: inline-block;
    }
    .badge-pending { background-color: #fef3c7 !important; color: #92400e !important; border: 1px solid #fde68a; }
    .badge-sent { background-color: #d1fae5 !important; color: #065f46 !important; border: 1px solid #a7f3d0; }
    
    .stButton>button {
        border-radius: 8px !important;
        font-weight: 700 !important;
    }
</style>
""", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# 3. 구글 시트 통신 함수
# -----------------------------------------------------------------------------
def fetch_applicants():
    try:
        res = requests.get(WEB_APP_URL, timeout=10)
        return res.json() if res.status_code == 200 else []
    except Exception as e:
        st.error(f"구글 시트 연동 오류: {e}")
        return []

def update_status_in_sheet(row_index, new_status, customer_name="", phone=""):
    try:
        payload = {
            "action": "update_status",
            "row_index": int(row_index),
            "status": str(new_status),
            "name": str(customer_name),
            "phone": str(phone)
        }
        res = requests.post(WEB_APP_URL, json=payload, timeout=10)
        return res.status_code == 200
    except Exception:
        return False

def move_customer_to_sheet2(row_index, customer_name="", phone=""):
    try:
        payload = {
            "action": "move_to_sheet2",
            "row_index": int(row_index),
            "name": str(customer_name),
            "phone": str(phone)
        }
        res = requests.post(WEB_APP_URL, json=payload, timeout=10)
        return res.status_code == 200
    except Exception:
        return False

def delete_customer_from_sheet1(row_index, customer_name="", phone=""):
    try:
        payload = {
            "action": "delete_row",
            "row_index": int(row_index),
            "name": str(customer_name),
            "phone": str(phone)
        }
        res = requests.post(WEB_APP_URL, json=payload, timeout=10)
        return res.status_code == 200
    except Exception:
        return False

def parse_time_from_string(time_str):
    if not time_str or "모름" in str(time_str) or str(time_str).strip() == "-":
        return None, 0, True
    s = str(time_str)
    time_map = {
        "자시": (0, 0), "축시": (2, 30), "인시": (4, 30), "묘시": (6, 30),
        "진시": (8, 30), "사시": (10, 30), "오시": (12, 30), "미시": (14, 30),
        "신시": (16, 30), "유시": (18, 30), "술시": (20, 30), "해시": (22, 30)
    }
    for k, v in time_map.items():
        if k in s:
            return v[0], v[1], False
    try:
        p = s.split(":")
        return int(p[0]), int(p[1]), False
    except Exception:
        return 12, 0, False


# -----------------------------------------------------------------------------
# 4. 모드 판별: URL 뒤에 ?admin=true 가 붙어있는지 비밀 확인!
# -----------------------------------------------------------------------------
query_params = st.query_params if hasattr(st, "query_params") else st.experimental_get_query_params()
is_admin_mode = str(query_params.get("admin", "")).lower() in ["true", "1", "yes"]


# =============================================================================
# [화면 1] 손님용 심층 사주풀이 신청서 (손님 접속 시 오직 이것만 보임!)
# =============================================================================
if not is_admin_mode:
    st.markdown("""
    <div class="banner-box">
        <div class="banner-badge">✨ 답답명쾌 사주 해답소</div>
        <div class="banner-title">심층 사주풀이 신청서</div>
        <div class="banner-desc">고객님의 생년월일시와 상담 고민을 남겨주시면, 정밀 사주원국을 분석하여 심층 풀이 및 맞춤형 PDF 보고서를 카카오톡으로 발송해 드립니다.</div>
    </div>
    """, unsafe_allow_html=True)

    with st.container():
        st.markdown('<div class="section-title">👤 신청자 기본 정보 <span style="font-size:12px;color:#dc2626;font-weight:normal;">* 필수 항목</span></div>', unsafe_allow_html=True)
        name = st.text_input("성명 (이름) *", placeholder="예: 홍길동")
        gender = st.radio("성별 *", ["남성", "여성"], horizontal=True)

        st.markdown('<div class="section-title">📅 생년월일 및 출생시 <span style="font-size:12px;color:#dc2626;font-weight:normal;">* 필수 항목</span></div>', unsafe_allow_html=True)
        col_cal, col_city = st.columns(2)
        with col_cal:
            cal_type = st.selectbox("양력 / 음력 구분 *", ["양력 (Solar)", "음력 (평달)", "음력 (윤달)"])
        with col_city:
            city = st.selectbox("출생도시 *", ["서울", "경기/인천", "부산", "대구", "대전", "광주", "울산", "강원", "충청", "전라", "경상", "제주", "해외"])

        st.markdown("**생년월일 (년 · 월 · 일)**")
        current_year = datetime.datetime.now().year
        year_options = [f"{y}년" for y in range(current_year, current_year - 101, -1)]
        month_options = [f"{m}월" for m in range(1, 13)]
        day_options = [f"{d}일" for d in range(1, 32)]

        c_y, c_m, c_d = st.columns(3)
        with c_y:
            selected_year = st.selectbox("출생년도", year_options, index=year_options.index("1990년"), label_visibility="collapsed")
        with c_m:
            selected_month = st.selectbox("출생월", month_options, index=0, label_visibility="collapsed")
        with c_d:
            selected_day = st.selectbox("출생일", day_options, index=0, label_visibility="collapsed")

        y_val = int(selected_year.replace("년", ""))
        m_val = int(selected_month.replace("월", ""))
        d_val = int(selected_day.replace("일", ""))
        try:
            birth_date = datetime.date(y_val, m_val, d_val)
        except ValueError:
            last_day = calendar.monthrange(y_val, m_val)[1]
            birth_date = datetime.date(y_val, m_val, min(d_val, last_day))

        time_unknown = st.checkbox("태어난 시간 모름 선택")
        if not time_unknown:
            time_options = [
                "자시(子時) 23:30 ~ 01:30", "축시(丑時) 01:30 ~ 03:30",
                "인시(寅時) 03:30 ~ 05:30", "묘시(卯時) 05:30 ~ 07:30",
                "진시(辰時) 07:30 ~ 09:30", "사시(巳時) 09:30 ~ 11:30",
                "오시(午時) 11:30 ~ 13:30", "미시(未時) 13:30 ~ 15:30",
                "신시(申時) 15:30 ~ 17:30", "유시(酉時) 17:30 ~ 19:30",
                "술시(戌時) 19:30 ~ 21:30", "해시(亥時) 21:30 ~ 23:30"
            ]
            selected_time = st.selectbox("태어난 시간 *", time_options, index=6)
            time_final = selected_time
        else:
            st.caption("시간을 모르실 경우 년·월·일(삼주)을 기반으로 정밀 풀이됩니다.")
            time_final = "모름 (시간미상)"

        st.markdown('<div class="section-title">📱 연락처 정보 (보고서 수신용) <span style="font-size:12px;color:#dc2626;font-weight:normal;">* 필수 항목</span></div>', unsafe_allow_html=True)
        phone = st.text_input("📱 휴대폰 번호 * (카카오 알림톡/PDF 수신용)", placeholder="010-1234-5678")
        email = st.text_input("✉️ 이메일 주소 (선택)", placeholder="example@naver.com")

        st.markdown('<div class="section-title">💬 상담 고민 및 집중 질문 (선택)</div>', unsafe_allow_html=True)
        concern = st.text_area(
            "가장 궁금한 점이나 고민을 적어주세요.",
            placeholder="예: 올해 이직운과 시험 합격운이 궁금합니다. 연애 및 결혼 시기, 재물운의 흐름을 알고 싶어요.",
            height=100
        )

        st.caption("🔒 입력하신 개인정보는 1:1 맞춤 사주 감정서 작성 및 카카오톡 발송에만 안전하게 사용됩니다.")
        st.markdown("<br>", unsafe_allow_html=True)

        if st.button("🔮 사주풀이 신청하기", type="primary", use_container_width=True):
            if not name.strip():
                st.error("성명을 입력해 주세요!")
            elif not phone.strip():
                st.error("휴대폰 번호를 입력해 주세요!")
            else:
                with st.spinner("고객님의 사주풀이 신청이 접수 중입니다..."):
                    gender_clean = "남" if "남" in gender else "여"
                    cal_clean = "양력" if "양력" in cal_type else ("음력(윤달)" if "윤달" in cal_type else "음력")
                    b_date_str = birth_date.strftime("%Y-%m-%d")
                    concern_clean = concern.strip() if concern.strip() else "전반적인 인생 운세 및 직업/재물운"

                    payload = {
                        "action": "new_application",
                        "이름": name.strip(),
                        "성별": gender_clean,
                        "양음력": cal_clean,
                        "생년월일": b_date_str,
                        "태어난시간": time_final,
                        "출생도시": city,
                        "휴대폰": phone.strip(),
                        "이메일": email.strip(),
                        "고객고민": concern_clean,
                        "sex": gender_clean,
                        "gender": gender_clean,
                        "name": name.strip(),
                        "cal_type": cal_clean,
                        "birth_date": b_date_str,
                        "birth_time": time_final,
                        "city": city,
                        "phone": phone.strip(),
                        "email": email.strip(),
                        "concern": concern_clean
                    }

                    try:
                        res = requests.post(WEB_APP_URL, json=payload, timeout=15)
                        if res.status_code == 200:
                            st.success(
                                f"🎉 {name}님, 사주풀이 신청이 접수되었습니다!\n\n"
                                "답답하신 마음이 시원하게 풀리도록 꼼꼼히 분석하겠습니다.\n"
                                "약 3~6시간 후 접수 순서에 따라 등록하신 휴대폰 카톡으로 발송해 드리겠습니다.\n\n"
                                "편히 기다려 주시면 정성 가득한 해답지로 찾아뵙겠습니다. 😄"
                            )
                            st.balloons()
                        else:
                            st.error("접수 전송에 실패했습니다. 잠시 후 다시 시도해 주세요.")
                    except Exception as e:
                        st.error(f"접수 통신 중 오류가 발생했습니다: {e}")


# =============================================================================
# [화면 2] 사장님 전용 비밀 관리자 모드 (?admin=true 로 접속했을 때만 열림!)
# =============================================================================
else:
    st.markdown("### 🔐 사장님 전용 접수 관리 센터")
    admin_pw = st.text_input("관리자 비밀번호를 입력해 주세요", type="password", placeholder="비밀번호: 1234")

    if admin_pw == ADMIN_PASSWORD:
        st.success("관리자 모드가 활성화되었습니다.")
        
        if st.button("🔄 시트1 최신 데이터 즉시 새로고침", use_container_width=True):
            st.rerun()

        with st.spinner("구글 스프레드시트1에서 접수 목록을 조회하는 중..."):
            raw_data = fetch_applicants()

        if not raw_data:
            st.info("현재 시트1에 접수 데이터가 없습니다. (모두 처리되었거나 비어있음)")
        else:
            df = pd.DataFrame(raw_data)
            st.caption(f"현재 시트1에 총 **{len(df)}명**의 고객이 있습니다.")

            for idx, row in df.iterrows():
                row_idx = row.get("row_index", idx + 2)
                c_name = row.get("이름", "무명")
                status = row.get("처리상태", "대기중")
                if not status:
                    status = "대기중"

                badge_class = "badge-sent" if status == "발송완료" else "badge-pending"
                raw_phone = str(row.get("휴대폰", ""))
                clean_phone = "".join(c for c in raw_phone if c.isdigit())

                with st.container():
                    st.markdown(f"""
                    <div style="background:#fcfcfc; border:1px solid #e2e2e8; border-radius:12px; padding:14px; margin-bottom:10px;">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                            <span style="font-size:17px; font-weight:800; color:#18181b;">{c_name} 님</span>
                            <span class='status-badge {badge_class}'>{status}</span>
                        </div>
                        <div style="font-size:12px; color:#52525b; line-height:1.6; margin-bottom:8px;">
                            • 접수일시: {row.get('접수일시', '-')}<br/>
                            • 성별/양음력: {row.get('성별','-')} | {row.get('양음력','-')}<br/>
                            • 생년월일: {str(row.get('생년월일','-')).split('T')[0]} ({row.get('태어난시간','-')})<br/>
                            • 출생도시: {row.get('출생도시','-')}<br/>
                            • 연락처: <strong>{row.get('휴대폰','-')}</strong>
                        </div>
                        <div style="font-size:12px; color:#27272a; background:#f4f4f5; padding:8px 10px; border-radius:6px; margin-bottom:12px;">
                            💬 <em>"{row.get('고객고민', '고민 미작성')}"</em>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    # 1. [사주 분석 시작] 버튼
                    btn_label = "⚡ 사주 분석 시작 (원클릭 자동생성)" if status == "대기중" else "🔄 리포트 재분석 (다시 생성하기)"
                    btn_color = "primary" if status == "대기중" else "secondary"

                    if st.button(btn_label, key=f"btn_run_{row_idx}", type=btn_color, use_container_width=True):
                        with st.status(f"🔮 [{c_name}] 님 사주 분석 및 리포트 자동 생성 중...", expanded=True) as status_box:
                            try:
                                status_box.write("1️⃣ 고객 정보 파싱 중...")
                                gender_internal = "남성" if "남" in str(row.get("성별", "남")) else "여성"
                                cal_type_str = str(row.get("양음력", "양력"))
                                is_lunar = "음력" in cal_type_str
                                is_leap = "윤달" in cal_type_str

                                b_raw = str(row.get("생년월일", "1990-01-01")).split("T")[0].strip()
                                b_parts = [int(p) for p in b_raw.split("-")]
                                birth_date_obj = datetime.date(b_parts[0], b_parts[1], b_parts[2])

                                b_hour, b_minute, time_unknown = parse_time_from_string(row.get("태어난시간", ""))
                                city_str = str(row.get("출생도시", "서울"))
                                region_offset = ADMIN_CITY_OFFSETS.get(city_str, -32)

                                dst_offset = 0
                                if not time_unknown and not is_lunar:
                                    auto_dst = get_dst_offset_minutes(
                                        birth_date_obj.year, birth_date_obj.month, birth_date_obj.day,
                                        b_hour, b_minute
                                    )
                                    dst_offset = 60 if auto_dst > 0 else 0

                                status_box.write("2️⃣ 정밀 만세력 계산 중...")
                                (year_p, month_p, day_p, hour_p,
                                 daewoon_num, daewoon_pillars, is_forward, lst_dt) = convert_to_pillars(
                                    birth_date_obj.year, birth_date_obj.month, birth_date_obj.day,
                                    b_hour, b_minute, is_lunar, is_leap, gender_internal,
                                    "표준 자시(기본)", region_offset, dst_offset
                                )

                                analyzer = AdvancedSajuAnalyzer(
                                    c_name, gender_internal, year_p, month_p, day_p, hour_p,
                                    daewoon_num, daewoon_pillars, birth_date=lst_dt.date(),
                                    profile={"deep_question": row.get("고객고민")}
                                )
                                saju_data = analyzer.compute_all()
                                contact_info = {"phone": clean_phone, "email": str(row.get("이메일", ""))}
                                saju_data["contact"] = contact_info

                                status_box.write("3️⃣ 클로드 AI 19개 챕터 리포트 작성 중...")
                                report_md = generate_saju_report(saju_data)

                                status_box.write("4️⃣ PDF 파일 렌더링 중...")
                                now = datetime.datetime.now()
                                pdf_filename = f"{c_name}_{clean_phone}.pdf" if clean_phone else f"{c_name}_{now.strftime('%Y%m%d%H%M')}.pdf"

                                pdf_ok = render_saju_report_pdf(saju_data, report_md, pdf_filename)
                                if not pdf_ok:
                                    raise RuntimeError("PDF 렌더링에 실패했습니다.")

                                status_box.write("5️⃣ 구글 드라이브 업로드 중...")
                                upload_res = gdrive_uploader.upload_pdf_to_date_folder(
                                    file_content=pdf_filename,
                                    filename=pdf_filename,
                                    date_obj=now,
                                    contact_info=contact_info
                                )

                                if os.path.exists(pdf_filename):
                                    os.remove(pdf_filename)

                                status_box.write("6️⃣ 카카오 알림톡 3시간 뒤 자동 예약 등록 중...")
                                file_id = upload_res.get("id", "")
                                if clean_phone and file_id:
                                    schedule_saju_alimtalk_3hours_later(c_name, clean_phone, file_id)

                                status_box.write("7️⃣ 시트1 상태를 '발송완료'로 업데이트 중...")
                                update_status_in_sheet(row_idx, "발송완료", c_name, clean_phone)

                                status_box.update(label=f"✅ [{c_name}] 님 사주 분석 및 알림톡 발송 완료!", state="complete")
                                st.success(f"🎉 [{c_name}] 님 완료! 상태가 '발송완료'로 변경되었습니다.")
                                time.sleep(1.2)
                                st.rerun()

                            except Exception as run_err:
                                status_box.update(label=f"❌ 오류 발생: {run_err}", state="error")
                                st.error(f"실패: {run_err}")

                    # 2. 사장님 2대 관리 버튼 (시트2 이동 / 미입금자 삭제)
                    st.write("")
                    col_move, col_del = st.columns(2)
                    with col_move:
                        if st.button("📦 시트2(보관)로 이동", key=f"btn_move_{row_idx}", use_container_width=True):
                            with st.spinner("시트2로 이동 처리 중..."):
                                if move_customer_to_sheet2(row_idx, c_name, clean_phone):
                                    st.success(f"✅ [{c_name}] 님이 시트2로 이동되었습니다!")
                                    time.sleep(0.8)
                                    st.rerun()
                                else:
                                    st.error("이동 실패")

                    with col_del:
                        if st.button("🗑️ 미입금자 삭제", key=f"btn_del_{row_idx}", use_container_width=True):
                            with st.spinner("시트1에서 삭제 중..."):
                                if delete_customer_from_sheet1(row_idx, c_name, clean_phone):
                                    st.warning(f"🗑️ [{c_name}] 님이 시트1에서 삭제되었습니다.")
                                    time.sleep(0.8)
                                    st.rerun()
                                else:
                                    st.error("삭제 실패")

                    st.markdown("---")

    elif admin_pw:
        st.error("비밀번호가 일치하지 않습니다.")