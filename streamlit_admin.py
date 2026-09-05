"""
[답답명쾌 사주해답소] 관리자 전용 스트림릿 대시보드 (streamlit_admin.py)
-------------------------------------------------------------------------------
실행 방법:
  1. 필수 라이브러리 설치: pip install streamlit requests pandas
  2. 로컬 실행: streamlit run streamlit_admin.py
  3. 스트림릿 클라우드 배포 시: GitHub에 올린 후 share.streamlit.io 에서 배포!
-------------------------------------------------------------------------------
"""

import streamlit as st
import requests
import pandas as pd
import datetime
import json
import time

# -----------------------------------------------------------------------------
# 기본 페이지 설정
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="답답명쾌 사주해답소 | 관리자 센터",
    page_icon="🔮",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 사장님의 구글 웹앱 URL (구글 시트 연동)
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbxFPVPgYvx3q-saacm0OkUuELMb-GomV5UDLTVUGRrSuzxDCQdXywyPePQqVhRxJz25Kw/exec"

# 커스텀 CSS 스타일링 (한옥 감성 프리미엄 톤)
st.markdown("""
<style>
    .main-title {
        font-family: 'Noto Serif KR', serif;
        font-size: 26px;
        font-weight: 700;
        color: #292524;
        margin-bottom: 4px;
    }
    .sub-title {
        font-size: 13px;
        color: #78716c;
        margin-bottom: 20px;
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
    .metric-card {
        background-color: #fbfbf9;
        border: 1px solid #e7e5e4;
        border-radius: 12px;
        padding: 16px;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# 구글 시트 통신 함수
# -----------------------------------------------------------------------------
def fetch_applicants():
    """구글 시트 웹앱에서 전체 접수 목록 가져오기"""
    try:
        res = requests.get(WEB_APP_URL, timeout=10)
        if res.status_code == 200:
            return res.json()
        return []
    except Exception as e:
        st.error(f"구글 시트 연동 오류: {e}")
        return []

def update_status_in_sheet(row_index, new_status, customer_name=""):
    """구글 시트의 처리상태 컬럼 변경"""
    try:
        payload = {
            "action": "update_status",
            "row_index": row_index,
            "status": new_status,
            "name": customer_name
        }
        res = requests.post(WEB_APP_URL, json=payload, timeout=10)
        return res.status_code == 200
    except Exception as e:
        st.error(f"상태 변경 통신 오류: {e}")
        return False


# -----------------------------------------------------------------------------
# 사이드바 (필터 및 제어 센터)
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 🔮 답답명쾌 사주해답소")
    st.caption("고객 접수 & PDF 발송 관리 시스템 v1.0")
    st.divider()

    st.subheader("📋 메일함 보기 필터")
    filter_option = st.radio(
        "상태별 보기 선택",
        ["전체 목록", "대기중 (입금/분석 대기)", "분석완료 (PDF 제작됨)", "발송완료 (알림톡 전송)", "상담종료 (완료된 건)"],
        index=0
    )
    
    st.divider()
    if st.button("🔄 시트 데이터 즉시 새로고침", use_container_width=True):
        st.rerun()

    st.caption("연동 웹앱: Google Apps Script")
    st.caption("데이터베이스: 사주_신청_접수부")


# -----------------------------------------------------------------------------
# 메인 헤더 & 통계 요약
# -----------------------------------------------------------------------------
st.markdown('<div class="main-title">사주 신청 고객 관리 및 처리 현황</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">구글 스프레드시트와 실시간 연동되어 입금 확인, 사주 분석, PDF 발송을 한눈에 관리합니다.</div>', unsafe_allow_html=True)

raw_data = fetch_applicants()
if not raw_data:
    st.info("현재 구글 시트에 접수된 데이터가 없거나 불러오는 중입니다.")
    st.stop()

df = pd.DataFrame(raw_data)

# 통계 지표 계산
total_count = len(df)
pending_count = len(df[df["처리상태"].isin(["대기중", "", None])])
analyzed_count = len(df[df["처리상태"] == "분석완료"])
sent_count = len(df[df["처리상태"] == "발송완료"])
closed_count = len(df[df["처리상태"] == "상담종료"])

col1, col2, col3, col4 = st.columns(4)
col1.metric("총 접수", f"{total_count}명")
col2.metric("대기중 (처리 필요)", f"{pending_count}명", delta=f"{pending_count}건", delta_color="inverse")
col3.metric("발송완료 (전송됨)", f"{sent_count}명")
col4.metric("상담종료 (보관)", f"{closed_count}명")

st.divider()

# 필터링 로직
if filter_option == "대기중 (입금/분석 대기)":
    filtered_df = df[df["처리상태"].isin(["대기중", "", None])]
elif filter_option == "분석완료 (PDF 제작됨)":
    filtered_df = df[df["처리상태"] == "분석완료"]
elif filter_option == "발송완료 (알림톡 전송)":
    filtered_df = df[df["처리상태"] == "발송완료"]
elif filter_option == "상담종료 (완료된 건)":
    filtered_df = df[df["처리상태"] == "상담종료"]
else:
    filtered_df = df

st.subheader(f"📋 {filter_option} ({len(filtered_df)}건)")

# -----------------------------------------------------------------------------
# 카드형 고객 리스트 & 원클릭 상태 변경
# -----------------------------------------------------------------------------
for idx, row in filtered_df.iterrows():
    row_idx = row.get("row_index", idx + 2)
    name = row.get("이름", "무명")
    status = row.get("처리상태", "대기중")
    if not status:
        status = "대기중"

    # 상태별 뱃지 스타일
    badge_class = "badge-pending"
    if status == "분석완료":
        badge_class = "badge-analyzed"
    elif status == "발송완료":
        badge_class = "badge-sent"
    elif status == "상담종료":
        badge_class = "badge-closed"

    with st.container():
        card_col1, card_col2, card_col3 = st.columns([3, 4, 3])
        
        with card_col1:
            st.markdown(f"### **{name}** 님  <span class='status-badge {badge_class}'>{status}</span>", unsafe_allow_html=True)
            st.caption(f"성별: {row.get('성별','-')} | {row.get('양음력','-')} | 생년월일: {str(row.get('생년월일','-')).split('T')[0]}")
            st.caption(f"시간: {row.get('태어난시간','-')} | 출생지: {row.get('출생도시','-')}")

        with card_col2:
            st.markdown(f"**📞 연락처:** `{row.get('휴대폰','-')}` | `{row.get('이메일','-')}`")
            question = row.get("고객고민", "작성된 고민 없음")
            st.markdown(f"**💬 고객 고민:** *\"{question}\"*")

        with card_col3:
            st.markdown("**⚡ 상태 변경 / 빠른 작업**")
            btn_col1, btn_col2 = st.columns(2)
            
            with btn_col1:
                if status != "상담종료":
                    if st.button("✅ 상담종료", key=f"close_{row_idx}", use_container_width=True):
                        with st.spinner("시트 상태 변경 중..."):
                            if update_status_in_sheet(row_idx, "상담종료", name):
                                st.success("상담종료 처리 완료!")
                                time.sleep(0.5)
                                st.rerun()
                else:
                    if st.button("↩️ 대기중 복원", key=f"revert_{row_idx}", use_container_width=True):
                        with st.spinner("시트 상태 복원 중..."):
                            if update_status_in_sheet(row_idx, "대기중", name):
                                st.success("대기중으로 복원 완료!")
                                time.sleep(0.5)
                                st.rerun()

            with btn_col2:
                if status == "대기중":
                    if st.button("🚀 분석시작", key=f"analyze_{row_idx}", use_container_width=True):
                        st.info("로컬 auto_batch.py 또는 터미널을 통해 분석을 진행합니다.")

        st.divider()

# -----------------------------------------------------------------------------
# 하단 파이썬 배치 실행 안내
# -----------------------------------------------------------------------------
with st.expander("ℹ️ [auto_batch.py] 사주 분석 및 자동 발송 실행 가이드"):
    st.markdown("""
    **사장님 로컬 컴퓨터에서 입금 확인 후 실행하는 방법:**
    1. 입금이 확인되면 대기중 명단을 확인합니다.
    2. 바탕화면의 `사주실행.bat` 또는 터미널에서 `python auto_batch.py` 를 실행합니다.
    3. 만세력 계산 ➔ 클로드 19개 챕터 ➔ PDF 생성 ➔ 구글 드라이브 업로드 ➔ 카카오 알림톡 3시간 뒤 예약이 자동으로 완료됩니다.
    4. 완료 후 시트 상태가 `발송완료`로 갱신되며, 이 대시보드에도 실시간 반영됩니다.
    """)
