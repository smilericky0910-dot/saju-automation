# -*- coding: utf-8 -*-
"""[답답명쾌 사주해답소] 고객 신청서 & 사장님 전용 원클릭 모바일 친화 관리 시스템"""

import calendar
import datetime
import json
import os
import time
from dabdab_saju_app import (
    CITY_LONGITUDE_OFFSETS,
    AdvancedSajuAnalyzer,
    convert_to_pillars,
    get_dst_offset_minutes,
)
import gdrive_uploader
import pandas as pd
import requests
from saju_alimtalk import schedule_saju_alimtalk_3hours_later
from saju_pdf_renderer import render_saju_report_pdf
from saju_report_generator import generate_saju_report
import streamlit as st

# -----------------------------------------------------------------------------
# 1. 페이지 기본 설정 (모바일 최적화 centered)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="답답명쾌 사주해답소",
    page_icon="🔮",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# 사장님의 구글 웹앱 URL (스프레드시트 연동)
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbxFPVPgYvx3q-saacm0OkUuELMb-GomV5UDLTVUGRrSuzxDCQdXywyPePQqVhRxJz25Kw/exec"

# 관리자 모드 기본 비밀번호
ADMIN_PASSWORD = "1234"

# 간이 도시 경도 오프셋 매핑
ADMIN_CITY_OFFSETS = {
    "서울": -32,
    "경기/인천": -32,
    "부산": -24,
    "대구": -26,
    "대전": -30,
    "광주": -33,
    "울산": -23,
    "강원": -28,
    "충청": -31,
    "전라": -32,
    "경상": -25,
    "제주": -34,
    "해외": 0,
}

# -----------------------------------------------------------------------------
# 2. 모바일 친화형 스타일 CSS (PC에서도 얇고 긴 스마트폰 뷰 구현)
# -----------------------------------------------------------------------------
st.markdown(
    """
<style>
    /* 전체 배경 */
    [data-testid="stAppViewContainer"] {
        background-color: #f1f1f4 !important;
    }
    
    /* PC 모니터에서도 스마트폰처럼 중앙에 480px로 얇고 길게 고정 */
    .block-container {
        max-width: 480px !important;
        margin: 20px auto !important;
        padding: 24px 18px !important;
        background-color: #ffffff !important;
        border-radius: 20px !important;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.08) !important;
        border: 1px solid #e2e2e8 !important;
    }

    /* 실제 스마트폰 접속 시에는 테두리 없이 화면에 꽉 차게 표시 */
    @media (max-width: 520px) {
        [data-testid="stAppViewContainer"] {
            background-color: #ffffff !important;
        }
        .block-container {
            max-width: 100% !important;
            margin: 0 !important;
            padding: 16px 14px !important;
            border-radius: 0 !important;
            box-shadow: none !important;
            border: none !important;
        }
    }

    /* 상단 헤더 배너 */
    .banner-box {
        background: linear-gradient(135deg, #1c1917 0%, #292524 100%);
        color: #fafaf9;
        padding: 20px 18px;
        border-radius: 12px;
        margin-bottom: 20px;
        border-left: 5px solid #d97706;
    }
    .banner-badge {
        font-size: 12px;
        font-weight: 600;
        color: #f59e0b;
        margin-bottom: 4px;
    }
    .banner-title {
        font-size: 22px;
        font-weight: 700;
        color: #ffffff;
        margin-bottom: 6px;
        font-family: 'Noto Serif KR', serif;
    }
    .banner-desc {
        font-size: 12px;
        color: #d6d3d1;
        line-height: 1.5;
    }
    .section-title {
        font-size: 15px;
        font-weight: 700;
        color: #292524;
        margin-top: 16px;
        margin-bottom: 10px;
    }
    
    /* 관리자 상태 배지 */
    .status-badge {
        padding: 3px 8px;
        border-radius: 9999px;
        font-size: 11px;
        font-weight: 600;
        display: inline-block;
    }
    .badge-pending { background-color: #fef3c7; color: #92400e; border: 1px solid #fde68a; }
    .badge-analyzed { background-color: #dbeafe; color: #1e40af; border: 1px solid #bfdbfe; }
    .badge-sent { background-color: #d1fae5; color: #065f46; border: 1px solid #a7f3d0; }
    .badge-closed { background-color: #f3f4f6; color: #4b5563; border: 1px solid #e5e7eb; }

    /* 모바일 터치 최적화 버튼 */
    .stButton>button {
        border-radius: 8px !important;
        font-weight: 700 !important;
    }
</style>
""",
    unsafe_allow_html=True,
)


# -----------------------------------------------------------------------------
# 3. 구글 시트 통신 및 시간 파싱 함수
# -----------------------------------------------------------------------------
def fetch_applicants():
  """구글 시트 웹앱에서 전체 신청자 목록 가져오기"""
  try:
    res = requests.get(WEB_APP_URL, timeout=10)
    if res.status_code == 200:
      return res.json()
    return []
  except Exception as e:
    st.error(f"구글 시트 연동 오류: {e}")
    return []


def update_status_in_sheet(row_index, new_status, customer_name=""):
  """구글 시트의 처리상태 변경"""
  try:
    payload = {
        "action": "update_status",
        "row_index": row_index,
        "status": new_status,
        "name": customer_name,
    }
    res = requests.post(WEB_APP_URL, json=payload, timeout=10)
    return res.status_code == 200
  except Exception as e:
    st.error(f"상태 변경 통신 오류: {e}")
    return False


def parse_time_from_string(time_str):
  """시트의 태어난시간 텍스트를 (hour, minute, time_unknown)으로 변환"""
  if not time_str or "모름" in str(time_str) or str(time_str).strip() == "-":
    return None, 0, True

  s = str(time_str)
  if "자시" in s:
    return 0, 0, False
  elif "축시" in s:
    return 2, 30, False
  elif "인시" in s:
    return 4, 30, False
  elif "묘시" in s:
    return 6, 30, False
  elif "진시" in s:
    return 8, 30, False
  elif "사시" in s:
    return 10, 30, False
  elif "오시" in s:
    return 12, 30, False
  elif "미시" in s:
    return 14, 30, False
  elif "신시" in s:
    return 16, 30, False
  elif "유시" in s:
    return 18, 30, False
  elif "술시" in s:
    return 20, 30, False
  elif "해시" in s:
    return 22, 30, False

  try:
    parts = s.split(":")
    return int(parts[0]), int(parts), False
  except Exception:
    return 12, 0, False


# -----------------------------------------------------------------------------
# 4. 상단 네비게이션
# -----------------------------------------------------------------------------
with st.sidebar:
  st.markdown("### 🔮 답답명쾌 사주해답소")
  st.caption("사주 접수 & 관리 통합 시스템")
  st.divider()
  app_mode = st.radio(
      "화면 모드 전환",
      ["📝 사주 상담 신청서 (고객용)", "🔐 사장님 관리자 모드"],
      index=0,
  )
  st.divider()
  st.caption("고객에게 전달 시: '사주 상담 신청서'가 기본으로 보입니다.")


# =============================================================================
# [화면 1] 고객용 사주 심층 상담 신청서
# =============================================================================
if app_mode == "📝 사주 상담 신청서 (고객용)":
  st.markdown(
      """
    <div class="banner-box">
        <div class="banner-badge">✨ 정통 명리학 맞춤 사주 감정</div>
        <div class="banner-title">사주 심층 상담 신청서</div>
        <div class="banner-desc">고객님의 생년월일시와 상담 고민을 남겨주시면, 정밀 사주원국을 분석하여 심층 풀이 및 맞춤형 PDF 보고서를 카카오톡으로 발송해 드립니다.</div>
    </div>
    """,
      unsafe_allow_html=True,
  )

  with st.container():
    # 1. 신청자 기본 정보
    st.markdown(
        '<div class="section-title">👤 신청자 기본 정보 <span'
        ' style="font-size:12px;color:#dc2626;font-weight:normal;">* 필수'
        " 항목</span></div>",
        unsafe_allow_html=True,
    )
    name = st.text_input("성명 (이름) *", placeholder="예: 홍길동")
    gender = st.radio(
        "성별 *", ["남성 (乾命)", "여성 (坤命)"], horizontal=True
    )

    # 2. 생년월일 및 출생시 (★ 100세까지 전수 선택 가능한 드롭다운 적용!)
    st.markdown(
        '<div class="section-title">📅 생년월일 및 출생시 <span'
        ' style="font-size:12px;color:#dc2626;font-weight:normal;">* 필수'
        " 항목</span></div>",
        unsafe_allow_html=True,
    )

    col_cal, col_city = st.columns(2)
    with col_cal:
      cal_type = st.selectbox(
          "양력 / 음력 구분 *", ["양력 (Solar)", "음력 (평달)", "음력 (윤달)"]
      )
    with col_city:
      city = st.selectbox(
          "출생도시 *",
          [
              "서울",
              "경기/인천",
              "부산",
              "대구",
              "대전",
              "광주",
              "울산",
              "강원",
              "충청",
              "전라",
              "경상",
              "제주",
              "해외",
          ],
      )

    st.markdown("**생년월일 (년 · 월 · 일)**")
    current_year = datetime.datetime.now().year  # 2026년
    # 2026년부터 100세 어르신(1925년생)까지 101개년 전수 선택 지원!
    year_options = [
        f"{y}년" for y in range(current_year, current_year - 101, -1)
    ]
    month_options = [f"{m}월" for m in range(1, 13)]
    day_options = [f"{d}일" for d in range(1, 32)]

    # ★ 오류 수정: st.columns(3) 으로 정직하게 3칸 분할 지정
    c_y, c_m, c_d = st.columns(3)
    with c_y:
      selected_year = st.selectbox(
          "출생년도",
          year_options,
          index=year_options.index("1990년"),
          label_visibility="collapsed",
      )
    with c_m:
      selected_month = st.selectbox(
          "출생월", month_options, index=0, label_visibility="collapsed"
      )
    with c_d:
      selected_day = st.selectbox(
          "출생일", day_options, index=0, label_visibility="collapsed"
      )

    y_val = int(selected_year.replace("년", ""))
    m_val = int(selected_month.replace("월", ""))
    d_val = int(selected_day.replace("일", ""))
    try:
      birth_date = datetime.date(y_val, m_val, d_val)
    except ValueError:
      last_day = calendar.monthrange(y_val, m_val)
      birth_date = datetime.date(y_val, m_val, min(d_val, last_day))

    time_unknown = st.checkbox("태어난 시간 모름 선택")
    if not time_unknown:
      time_options = [
          "자시(子時) 23:30 ~ 01:30",
          "축시(丑時) 01:30 ~ 03:30",
          "인시(寅時) 03:30 ~ 05:30",
          "묘시(卯時) 05:30 ~ 07:30",
          "진시(辰時) 07:30 ~ 09:30",
          "사시(巳時) 09:30 ~ 11:30",
          "오시(午時) 11:30 ~ 13:30",
          "미시(未時) 13:30 ~ 15:30",
          "신시(申時) 15:30 ~ 17:30",
          "유시(酉時) 17:30 ~ 19:30",
          "술시(戌時) 19:30 ~ 21:30",
          "해시(亥時) 21:30 ~ 23:30",
      ]
      selected_time = st.selectbox("태어난 시간 *", time_options, index=6)
      time_final = selected_time
    else:
      st.caption("시간을 모르실 경우 년·월·일(삼주)을 기반으로 정밀 풀이됩니다.")
      time_final = "모름 (시간미상)"

    # 3. 연락처 정보
    st.markdown(
        '<div class="section-title">📱 연락처 정보 (보고서 수신용) <span'
        ' style="font-size:12px;color:#dc2626;font-weight:normal;">* 필수'
        " 항목</span></div>",
        unsafe_allow_html=True,
    )
    phone = st.text_input(
        "📱 휴대폰 번호 * (카카오 알림톡/PDF 수신용)",
        placeholder="010-1234-5678",
    )
    email = st.text_input("✉️ 이메일 주소 (선택)", placeholder="example@naver.com")

    # 4. 상담 고민
    st.markdown(
        '<div class="section-title">💬 상담 고민 및 집중 질문 (선택)</div>',
        unsafe_allow_html=True,
    )
    concern = st.text_area(
        "가장 궁금한 점이나 고민을 적어주세요.",
        placeholder=(
            "예: 올해 이직운과 시험 합격운이 궁금합니다. 연애 및 결혼 시기, 재물운의 흐름을"
            " 알고 싶어요."
        ),
        height=100,
    )

    st.caption(
        "🔒 입력하신 개인정보는 1:1 맞춤 사주 감정서 작성 및 카카오톡 발송에만 안전하게"
        " 사용됩니다."
    )
    st.markdown("<br>", unsafe_allow_html=True)
    # ★ 사장님께서 변경 요청하신 문구: '사주풀이 신청하기' 반영
    if st.button(
        "🔮 사주풀이 신청하기", type="primary", use_container_width=True
    ):
      if not name.strip():
        st.error("성명을 입력해 주세요!")
      elif not phone.strip():
        st.error("휴대폰 번호를 입력해 주세요!")
      else:
        with st.spinner("구글 시트로 안전하게 접수 중입니다..."):
          gender_clean = "남" if "남성" in gender else "여"
          cal_clean = (
              "양력"
              if "양력" in cal_type
              else ("음력(윤달)" if "윤달" in cal_type else "음력")
          )

          payload = {
              "action": "new_application",
              "이름": name.strip(),
              "성별": gender_clean,
              "양음력": cal_clean,
              "생년월일": birth_date.strftime("%Y-%m-%d"),
              "태어난시간": time_final,
              "출생도시": city,
              "휴대폰": phone.strip(),
              "이메일": email.strip(),
              "고객고민": (
                  concern.strip()
                  if concern.strip()
                  else "전반적인 인생 운세 및 직업/재물운"
              ),
          }
          try:
            res = requests.post(WEB_APP_URL, json=payload, timeout=15)
            if res.status_code == 200:
              st.success(
                  f"🎉 {name}님, 사주 상담 접수가 완료되었습니다! 확인 후 정밀"
                  " 감정서가 카카오톡으로 발송됩니다."
              )
              st.balloons()
            else:
              st.error("접수 전송에 실패했습니다. 잠시 후 다시 시도해 주세요.")
          except Exception as e:
            st.error(f"접수 통신 중 오류가 발생했습니다: {e}")


# =============================================================================
# [화면 2] 사장님 전용 관리자 모드 (모바일 카드 뷰 최적화)
# =============================================================================
elif app_mode == "🔐 사장님 관리자 모드":
  st.markdown("### 🔐 사장님 전용 접수 관리 센터")
  st.caption("고객 정보 보호를 위해 비밀번호를 입력해 주세요.")

  admin_pw = st.text_input(
      "관리자 비밀번호", type="password", placeholder="기본 비밀번호: 1234"
  )

  if admin_pw == ADMIN_PASSWORD:
    st.success("관리자 모드가 활성화되었습니다.")

    if st.button("🔄 시트 데이터 즉시 새로고침", use_container_width=True):
      st.rerun()

    with st.spinner("구글 스프레드시트에서 접수 목록을 조회하는 중..."):
      raw_data = fetch_applicants()

    if not raw_data:
      st.info("현재 접수된 고객 데이터가 없습니다.")
    else:
      df = pd.DataFrame(raw_data)

      total_count = len(df)
      pending_count = len(df[df["처리상태"].isin(["대기중", "", None])])
      analyzed_count = len(df[df["처리상태"] == "분석완료"])
      sent_count = len(df[df["처리상태"] == "발송완료"])

      c1, c2 = st.columns(2)
      c1.metric("총 접수", f"{total_count}명")
      c2.metric(
          "대기중",
          f"{pending_count}명",
          delta=f"{pending_count}건",
          delta_color="inverse",
      )

      st.divider()

      filter_val = st.selectbox(
          "상태별 목록 필터",
          [
              "전체 목록",
              "대기중 (분석 대기)",
              "분석완료 (PDF 제작됨)",
              "발송완료 (알림톡 전송)",
              "상담종료 (보관)",
          ],
      )

      if "대기중" in filter_val:
        filtered_df = df[df["처리상태"].isin(["대기중", "", None])]
      elif "분석완료" in filter_val:
        filtered_df = df[df["처리상태"] == "분석완료"]
      elif "발송완료" in filter_val:
        filtered_df = df[df["처리상태"] == "발송완료"]
      elif "상담종료" in filter_val:
        filtered_df = df[df["처리상태"] == "상담종료"]
      else:
        filtered_df = df

      st.caption(f"총 {len(filtered_df)}건의 접수 내역이 있습니다.")

      for idx, row in filtered_df.iterrows():
        row_idx = row.get("row_index", idx + 2)
        c_name = row.get("이름", "무명")
        status = row.get("처리상태", "대기중")
        if not status:
          status = "대기중"

        badge_class = "badge-pending"
        if status == "분석완료":
          badge_class = "badge-analyzed"
        elif status == "발송완료":
          badge_class = "badge-sent"
        elif status == "상담종료":
          badge_class = "badge-closed"

        raw_phone = str(row.get("휴대폰", ""))
        clean_phone = "".join(c for c in raw_phone if c.isdigit())

        # 모바일 카드 디자인
        with st.container():
          st.markdown(
              f"""
                    <div style="background:#fcfcfc; border:1px solid #e2e2e8; border-radius:12px; padding:14px; margin-bottom:12px;">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                            <span style="font-size:17px; font-weight:800; color:#18181b;">{c_name} 님</span>
                            <span class='status-badge {badge_class}'>{status}</span>
                        </div>
                        <div style="font-size:12px; color:#52525b; line-height:1.6; margin-bottom:8px;">
                            • 성별/양음력: {row.get('성별','-')} | {row.get('양음력','-')}<br/>
                            • 생년월일: {str(row.get('생년월일','-')).split('T')[0]} ({row.get('태어난시간','-')})<br/>
                            • 출생도시: {row.get('출생도시','-')}<br/>
                            • 연락처: <strong>{row.get('휴대폰','-')}</strong>
                        </div>
                        <div style="font-size:12px; color:#27272a; background:#f4f4f5; padding:8px 10px; border-radius:6px; margin-bottom:12px;">
                            💬 <em>"{row.get('고객고민', '고민 미작성')}"</em>
                        </div>
                    </div>
                    """,
              unsafe_allow_html=True,
          )

          # ★ [분석 시작] 원클릭 실행 버튼
          if st.button(
              "분석 시작",
              key=f"btn_run_{row_idx}",
              type="primary",
              use_container_width=True,
          ):
            with st.status(
                f"🔮 [{c_name}] 님 사주 분석 및 리포트 자동 생성 중...",
                expanded=True,
            ) as status_box:
              try:
                status_box.write("1️⃣ 고객 정보 및 음양력/출생시 파싱 중...")
                gender_internal = (
                    "남성" if "남" in str(row.get("성별", "남")) else "여성"
                )
                cal_type_str = str(row.get("양음력", "양력"))
                is_lunar = "음력" in cal_type_str
                is_leap = "윤달" in cal_type_str

                b_raw = (
                    str(row.get("생년월일", "1990-01-01")).split("T")[0].strip()
                )
                b_parts = [int(p) for p in b_raw.split("-")]
                birth_date_obj = datetime.date(
                    b_parts[0], b_parts, b_parts
                )

                b_hour, b_minute, time_unknown = parse_time_from_string(
                    row.get("태어난시간", "")
                )
                city_str = str(row.get("출생도시", "서울"))
                region_offset = ADMIN_CITY_OFFSETS.get(city_str, -32)

                dst_offset = 0
                if not time_unknown and not is_lunar:
                  auto_dst = get_dst_offset_minutes(
                      birth_date_obj.year,
                      birth_date_obj.month,
                      birth_date_obj.day,
                      b_hour,
                      b_minute,
                  )
                  dst_offset = 60 if auto_dst > 0 else 0

                status_box.write("2️⃣ 정밀 만세력 및 오행·용신 계산 중...")
                (
                    year_p,
                    month_p,
                    day_p,
                    hour_p,
                    daewoon_num,
                    daewoon_pillars,
                    is_forward,
                    lst_dt,
                ) = convert_to_pillars(
                    birth_date_obj.year,
                    birth_date_obj.month,
                    birth_date_obj.day,
                    b_hour,
                    b_minute,
                    is_lunar,
                    is_leap,
                    gender_internal,
                    "표준 자시(기본)",
                    region_offset,
                    dst_offset,
                )

                analyzer = AdvancedSajuAnalyzer(
                    c_name,
                    gender_internal,
                    year_p,
                    month_p,
                    day_p,
                    hour_p,
                    daewoon_num,
                    daewoon_pillars,
                    birth_date=lst_dt.date(),
                    profile={"deep_question": row.get("고객고민")},
                )
                saju_data = analyzer.compute_all()
                contact_info = {
                    "phone": clean_phone,
                    "email": str(row.get("이메일", "")),
                }
                saju_data["contact"] = contact_info

                status_box.write(
                    "3️⃣ 클로드 AI 19개 챕터 감정서 작성 중 (약 1분 소요)..."
                )
                report_md = generate_saju_report(saju_data)

                status_box.write("4️⃣ 프리미엄 감정서 PDF 파일 렌더링 중...")
                now = datetime.datetime.now()
                pdf_filename = (
                    f"{c_name}_{clean_phone}.pdf"
                    if clean_phone
                    else f"{c_name}_{now.strftime('%Y%m%d%H%M')}.pdf"
                )

                pdf_ok = render_saju_report_pdf(
                    saju_data, report_md, pdf_filename
                )
                if not pdf_ok:
                  raise RuntimeError(
                      "PDF 렌더링에 실패했습니다. packages.txt 설정을 확인해"
                      " 주세요."
                  )

                status_box.write(
                    "5️⃣ 구글 드라이브 날짜별 폴더로 PDF 업로드 중..."
                )
                upload_res = gdrive_uploader.upload_pdf_to_date_folder(
                    file_content=pdf_filename,
                    filename=pdf_filename,
                    date_obj=now,
                    contact_info=contact_info,
                )

                if os.path.exists(pdf_filename):
                  os.remove(pdf_filename)

                status_box.write(
                    "6️⃣ 카카오 알림톡 3시간 뒤 자동 예약 등록 중..."
                )
                file_id = upload_res.get("id", "")
                if clean_phone and file_id:
                  schedule_saju_alimtalk_3hours_later(
                      c_name, clean_phone, file_id
                  )

                status_box.write(
                    "7️⃣ 구글 시트 상태를 '발송완료'로 업데이트 중..."
                )
                update_status_in_sheet(row_idx, "발송완료", c_name)

                status_box.update(
                    label=f"✅ [{c_name}] 님 사주 분석 및 알림톡 발송 완료!",
                    state="complete",
                )
                st.success(
                    f"🎉 [{c_name}] 님 리포트 제작 및 3시간 뒤 알림톡 예약"
                    " 완료!"
                )
                time.sleep(1.5)
                st.rerun()

              except Exception as run_err:
                status_box.update(
                    label=f"❌ 오류 발생: {run_err}", state="error"
                )
                st.error(f"분석 실행 중 실패: {run_err}")

          # 보조 관리 버튼 (상담종료 / 대기중 복원)
          b_col1, b_col2 = st.columns(2)
          with b_col1:
            if status != "상담종료":
              if st.button(
                  "상담종료", key=f"btn_close_{row_idx}", use_container_width=True
              ):
                with st.spinner("상태 변경 중..."):
                  if update_status_in_sheet(row_idx, "상담종료", c_name):
                    st.rerun()
            else:
              if st.button(
                  "대기중 복원",
                  key=f"btn_revert_{row_idx}",
                  use_container_width=True,
              ):
                with st.spinner("복원 중..."):
                  if update_status_in_sheet(row_idx, "대기중", c_name):
                    st.rerun()
          with b_col2:
            st.caption(f"접수번호 #{row_idx}")

          st.markdown("---")

  elif admin_pw:
    st.error("비밀번호가 일치하지 않습니다. 다시 입력해 주세요.")