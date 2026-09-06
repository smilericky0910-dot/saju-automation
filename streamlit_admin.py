# -*- coding: utf-8 -*-
"""[답답명쾌 사주해답소] 고객 신청서 & 사장님 전용 원클릭 자동화 관리 시스템"""

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
# 1. 페이지 기본 설정
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="답답명쾌 사주해답소 | 사주 심층 상담",
    page_icon="🔮",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# 구글 앱스 스크립트 웹 앱 URL (secrets.toml에서 불러오기)
WEB_APP_URL = st.secrets.get("GOOGLE_APPS_SCRIPT_URL", "")

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
# 2. 스타일 CSS
# -----------------------------------------------------------------------------
st.markdown(
    """
<style>
    .banner-box {
        background: linear-gradient(135deg, #1c1917 0%, #292524 100%);
        color: #fafaf9;
        padding: 24px 22px;
        border-radius: 12px;
        margin-bottom: 24px;
        border-left: 5px solid #d97706;
    }
    .banner-badge {
        font-size: 13px;
        font-weight: 600;
        color: #f59e0b;
        margin-bottom: 6px;
    }
    .banner-title {
        font-size: 26px;
        font-weight: 700;
        color: #ffffff;
        margin-bottom: 8px;
        font-family: 'Noto Serif KR', serif;
    }
    .banner-desc {
        font-size: 13px;
        color: #d6d3d1;
        line-height: 1.5;
    }
    .section-title {
        font-size: 16px;
        font-weight: 700;
        color: #292524;
        margin-top: 18px;
        margin-bottom: 12px;
    }
    .status-badge {
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 12px;
        font-weight: 600;
        display: inline-block;
    }
    .badge-pending { background-color: #fef3c7; color: #92400e; border: 1px solid #fde68a; }
    .badge-analyzed { background-color: #dbeafe; color: #1e40af; border: 1px solid #bfdbfe; }
    .badge-sent { background-color: #d1fae5; color: #065f46; border: 1px solid #a7f3d0; }
    .badge-closed { background-color: #f3f4f6; color: #4b5563; border: 1px solid #e5e7eb; }
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
        <div class="banner-badge">✨ 정통 명리학 기반 맞춤 사주 감정</div>
        <div class="banner-title">사주 심층 상담 신청서</div>
        <div class="banner-desc">고객님의 생년월일시와 상담 고민을 남겨주시면, 정밀 사주원국을 분석하여 심층 풀이 및 맞춤형 PDF 보고서를 카카오톡으로 발송해 드립니다.</div>
    </div>
    """,
      unsafe_allow_html=True,
  )

  with st.container():
    st.markdown(
        '<div class="section-title">👤 신청자 기본 정보 <span'
        ' style="font-size:12px;color:#dc2626;font-weight:normal;">* 필수'
        " 항목</span></div>",
        unsafe_allow_html=True,
    )
    col_name, col_gender = st.columns(2)
    with col_name:
      name = st.text_input("성명 (이름) * (필수)", placeholder="예: 홍길동")
    with col_gender:
      gender = st.radio("성별 * (필수)", ["남성 (乾命)", "여성 (坤命)"], horizontal=True)

    st.markdown(
        '<div class="section-title">📅 생년월일 및 출생시 (사주 원국 산출) <span'
        ' style="font-size:12px;color:#dc2626;font-weight:normal;">* 필수'
        " 항목</span></div>",
        unsafe_allow_html=True,
    )
    col_cal, col_date, col_city = st.columns(3)
    with col_cal:
      cal_type = st.selectbox(
          "양력 / 음력 구분 * (필수)", ["양력 (Solar)", "음력 (평달)", "음력 (윤달)"]
      )
    with col_date:
      birth_date = st.date_input(
          "생년월일 * (필수)",
          value=datetime.date(1995, 6, 15),
          min_value=datetime.date(1930, 1, 1),
      )
    with col_city:
      city = st.selectbox(
          "출생도시 (태어난 지역) * (필수)",
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
      selected_time = st.selectbox("태어난 시간 * (필수)", time_options, index=6)
      time_final = selected_time
    else:
      st.caption("시간을 모르실 경우 년·월·일(삼주)을 기반으로 정밀 풀이됩니다.")
      time_final = "모름 (시간미상)"

    st.markdown(
        '<div class="section-title">📱 연락처 정보 (보고서 수신용) <span'
        ' style="font-size:12px;color:#dc2626;font-weight:normal;">* 필수'
        " 항목</span></div>",
        unsafe_allow_html=True,
    )
    col_phone, col_email = st.columns(2)
    with col_phone:
      phone = st.text_input(
          "휴대폰 번호 * (필수 - 카카오 알림톡/PDF 수신용)",
          placeholder="예: 010-1234-5678",
      )
    with col_email:
      email = st.text_input(
          "이메일 주소 (선택사항)", placeholder="예: example@naver.com"
      )

    st.markdown(
        '<div class="section-title">💬 상담 고민 및 집중 질문 (선택)</div>',
        unsafe_allow_html=True,
    )
    concern = st.text_area(
        "풀고 싶은 가장 큰 답답함이나 궁금한 점을 적어주세요.",
        placeholder=(
            "예: 올해 이직운과 시험 합격운이 궁금합니다. 연애 및 결혼 시기, 재물운의 흐름을"
            " 알고 싶어요."
        ),
        height=110,
    )

    st.caption(
        "🔒 입력하신 개인정보는 1:1 맞춤 사주 감정서 작성 및 카카오톡 발송에만 안전하게"
        " 사용됩니다."
    )
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button(
        "🔮 사주 심층 상담 신청하기", type="primary", use_container_width=True
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
                  f"🎉 {name}님, 사주 상담 접수가 성공적으로 완료되었습니다! 확인 후 정밀"
                  " 감정서가 카카오톡으로 발송됩니다."
              )
              st.balloons()
            else:
              st.error("접수 전송에 실패했습니다. 잠시 후 다시 시도해 주세요.")
          except Exception as e:
            st.error(f"접수 통신 중 오류가 발생했습니다: {e}")


# =============================================================================
# [화면 2] 사장님 전용 관리자 모드
# =============================================================================
elif app_mode == "🔐 사장님 관리자 모드":
  st.markdown("### 🔐 사장님 전용 접수 관리 센터")
  st.caption("고객 정보 보호를 위해 관리자 인증 후 이용하실 수 있습니다.")

  admin_pw = st.text_input(
      "관리자 비밀번호를 입력하세요", type="password", placeholder="기본 비밀번호: 1234"
  )

  if admin_pw == ADMIN_PASSWORD:
    st.success("인증 완료: 관리자 모드가 활성화되었습니다.")

    ctrl_col1, ctrl_col2 = st.columns()
    with ctrl_col1:
      if st.button("🔄 시트 데이터 즉시 새로고침", use_container_width=True):
        st.rerun()

    with st.spinner("구글 스프레드시트에서 접수 목록을 조회하는 중..."):
      raw_data = fetch_applicants()

    if not raw_data:
      st.info("현재 구글 시트에 접수된 고객 데이터가 없습니다.")
    else:
      df = pd.DataFrame(raw_data)

      total_count = len(df)
      pending_count = len(df[df["처리상태"].isin(["대기중", "", None])])
      analyzed_count = len(df[df["처리상태"] == "분석완료"])
      sent_count = len(df[df["처리상태"] == "발송완료"])
      closed_count = len(df[df["처리상태"] == "상담종료"])

      c1, c2, c3, c4 = st.columns(4)
      c1.metric("총 접수", f"{total_count}명")
      c2.metric(
          "대기중 (처리 필요)",
          f"{pending_count}명",
          delta=f"{pending_count}건",
          delta_color="inverse",
      )
      c3.metric("발송완료 (전송됨)", f"{sent_count}명")
      c4.metric("상담종료 (보관)", f"{closed_count}명")

      st.divider()

      filter_val = st.radio(
          "상태별 목록 필터링",
          [
              "전체 목록",
              "대기중 (입금/분석 대기)",
              "분석완료 (PDF 제작됨)",
              "발송완료 (알림톡 전송)",
              "상담종료 (완료된 건)",
          ],
          horizontal=True,
      )

      if filter_val == "대기중 (입금/분석 대기)":
        filtered_df = df[df["처리상태"].isin(["대기중", "", None])]
      elif filter_val == "분석완료 (PDF 제작됨)":
        filtered_df = df[df["처리상태"] == "분석완료"]
      elif filter_val == "발송완료 (알림톡 전송)":
        filtered_df = df[df["처리상태"] == "발송완료"]
      elif filter_val == "상담종료 (완료된 건)":
        filtered_df = df[df["처리상태"] == "상담종료"]
      else:
        filtered_df = df

      st.subheader(f"📋 {filter_val} ({len(filtered_df)}건)")

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

        with st.container():
          card_col1, card_col2, card_col3 = st.columns()

          with card_col1:
            st.markdown(
                f"### **{c_name}** 님  <span class='status-badge"
                f" {badge_class}'>{status}</span>",
                unsafe_allow_html=True,
            )
            st.caption(
                f"성별: {row.get('성별','-')} | {row.get('양음력','-')} | 생년월일:"
                f" {str(row.get('생년월일','-')).split('T')[0]}"
            )
            st.caption(
                f"시간: {row.get('태어난시간','-')} | 출생지:"
                f" {row.get('출생도시','-')}"
            )

          with card_col2:
            st.markdown(
                f"**📞 연락처:** `{row.get('휴대폰','-')}` |"
                f" `{row.get('이메일','-')}`"
            )
            st.markdown(
                f"**💬 고객 고민:** *\"{row.get('고객고민', '작성된 고민 없음')}\"*"
            )

          with card_col3:
            st.markdown("**⚡ 분석 및 상태 관리**")

            # ★ [분석 시작] 버튼
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
                  # 1. 시트 고객 정보 파싱
                  status_box.write("1️⃣ 고객 접수 정보 해석 중...")
                  gender_internal = (
                      "남성" if "남" in str(row.get("성별", "남")) else "여성"
                  )
                  cal_type_str = str(row.get("양음력", "양력"))
                  is_lunar = "음력" in cal_type_str
                  is_leap = "윤달" in cal_type_str

                  # 생년월일 추출
                  b_raw = (
                      str(row.get("생년월일", "1990-01-01"))
                      .split("T")[0]
                      .strip()
                  )
                  b_parts = [int(p) for p in b_raw.split("-")]
                  birth_date_obj = datetime.date(
                      b_parts[0], b_parts, b_parts
                  )

                  # 태어난 시간 추출
                  b_hour, b_minute, time_unknown = parse_time_from_string(
                      row.get("태어난시간", "")
                  )

                  # 도시 보정값
                  city_str = str(row.get("출생도시", "서울"))
                  region_offset = ADMIN_CITY_OFFSETS.get(city_str, -32)

                  # 서머타임 보정
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

                  # 2. 사주 명식 연산
                  status_box.write("2️⃣ 정밀 만세력 및 오행·대운 계산 중...")
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

                  raw_phone = str(row.get("휴대폰", ""))
                  clean_phone = "".join(c for c in raw_phone if c.isdigit())
                  contact_info = {
                      "phone": clean_phone,
                      "email": str(row.get("이메일", "")),
                  }
                  saju_data["contact"] = contact_info

                  # 3. 클로드 AI 사주 해설서 19개 챕터 작성
                  status_box.write(
                      "3️⃣ 클로드 AI 19개 챕터 감정서 작성 중 (약 1분"
                      " 소요)..."
                  )
                  report_md = generate_saju_report(saju_data)

                  # 4. PDF 조립 및 렌더링
                  status_box.write("4️⃣ 프리미엄 감정서 PDF 파일 렌더링 중...")
                  now = datetime.datetime.now()
                  if clean_phone:
                    pdf_filename = f"{c_name}_{clean_phone}.pdf"
                  else:
                    pdf_filename = (
                        f"{c_name}_{now.strftime('%Y%m%d%H%M')}.pdf"
                    )

                  pdf_ok = render_saju_report_pdf(
                      saju_data, report_md, pdf_filename
                  )
                  if not pdf_ok:
                    raise RuntimeError(
                        "PDF 렌더링에 실패했습니다. packages.txt 설정을"
                        " 확인해 주세요."
                    )

                  # 5. 구글 드라이브 업로드
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

                  # 6. 솔라피 카카오 알림톡 3시간 뒤 예약
                  status_box.write(
                      "6️⃣ 카카오 알림톡 3시간 뒤 자동 예약 등록 중..."
                  )
                  file_id = upload_res.get("id", "")
                  if clean_phone and file_id:
                    schedule_saju_alimtalk_3hours_later(
                        c_name, clean_phone, file_id
                    )

                  # 7. 구글 시트 상태 '발송완료' 갱신
                  status_box.write(
                      "7️⃣ 구글 시트 상태를 '발송완료'로 업데이트 중..."
                  )
                  update_status_in_sheet(row_idx, "발송완료", c_name)

                  status_box.update(
                      label=f"✅ [{c_name}] 님 사주 분석 및 알림톡 발송 완료!",
                      state="complete",
                  )
                  st.success(
                      f"🎉 [{c_name}] 님 리포트가 성공적으로 생성되어 드라이브에"
                      " 저장되었고, 3시간 뒤 알림톡 예약이 접수되었습니다!"
                  )
                  time.sleep(1.5)
                  st.rerun()

                except Exception as run_err:
                  status_box.update(
                      label=f"❌ 오류 발생: {run_err}", state="error"
                  )
                  st.error(f"분석 실행 중 실패: {run_err}")

            # 상태 수동 관리 버튼 (상담종료 / 복원)
            if status != "상담종료":
              if st.button(
                  "✅ 상담종료 처리",
                  key=f"btn_close_{row_idx}",
                  use_container_width=True,
              ):
                with st.spinner("시트 상태 변경 중..."):
                  if update_status_in_sheet(row_idx, "상담종료", c_name):
                    st.success("상담종료 완료!")
                    time.sleep(0.5)
                    st.rerun()
            else:
              if st.button(
                  "↩️ 대기중 복원",
                  key=f"btn_revert_{row_idx}",
                  use_container_width=True,
              ):
                with st.spinner("시트 상태 복원 중..."):
                  if update_status_in_sheet(row_idx, "대기중", c_name):
                    st.success("대기중 복원 완료!")
                    time.sleep(0.5)
                    st.rerun()

          st.divider()

  elif admin_pw:
    st.error("비밀번호가 일치하지 않습니다. 다시 입력해 주세요.")