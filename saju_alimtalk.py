# -*- coding: utf-8 -*-
"""사주 분석 리포트 카카오 알림톡 3시간 뒤 예약 발송 모듈"""

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import secrets
import requests

# ==========================================
# 1. 솔라피 및 카카오 채널 연동 정보
# ==========================================
SOLAPI_API_KEY = "NCSTGOZCT8T2RA1E"
SOLAPI_API_SECRET = "XI74TLN77XM8K0PSVTZCQLICUPWZSH8B"
KAKAO_PF_ID = "KA01PF260905085546550ANXKNTJ0de2"

# ★ 카카오 템플릿 검수가 승인되면 여기에 템플릿 ID를 넣어주세요.
TEMPLATE_ID = "승인후_발급받을_템플릿ID"


def get_solapi_auth_header(api_key: str, api_secret: str) -> str:
  """솔라피 v4 HMAC-SHA256 인증 헤더 생성"""
  date = datetime.now(timezone.utc).isoformat()[:23] + "Z"
  salt = secrets.token_hex(16)
  combined = date + salt
  signature = hmac.new(
      api_secret.encode("utf-8"), combined.encode("utf-8"), hashlib.sha256
  ).hexdigest()
  return (
      f"HMAC-SHA256 apiKey={api_key}, date={date}, salt={salt},"
      f" signature={signature}"
  )


def schedule_saju_alimtalk_3hours_later(
    customer_name: str, phone_number: str, file_id: str
):
  """구글 드라이브 파일 ID를 받아 3시간 뒤에 알림톡이 발송되도록 솔라피에 예약 등록합니다."""

  # 1. 3시간 뒤 발송 시각 계산 (ISO 8601 UTC 형식)
  send_time_utc = datetime.now(timezone.utc) + timedelta(hours=3)
  scheduled_date_str = send_time_utc.strftime("%Y-%m-%dT%H:%M:%SZ")

  # 한국 시간 기준 확인용
  kst_send_time = datetime.now() + timedelta(hours=3)
  clean_phone = "".join(c for c in phone_number if c.isdigit())

  url = "https://api.solapi.com/messages/v4/send"
  headers = {
      "Authorization": get_solapi_auth_header(
          SOLAPI_API_KEY, SOLAPI_API_SECRET
      ),
      "Content-Type": "application/json; charset=utf-8",
  }

  # 2. 신청하신 템플릿 문구와 100% 동일한 메시지 본문
  payload = {
      "message": {
          "to": clean_phone,
          "scheduledDate": scheduled_date_str,  # ★ 3시간 뒤 자동 예약
          "text": f"""신청하신
분석이 완료되었습니다.

{customer_name}님, 😄
신청하신 프리미엄 사주 해답지가
완료되었습니다.

아래 버튼을 눌러 확인해 주세~ 😄""",
          "kakaoOptions": {
              "pfId": KAKAO_PF_ID,
              "templateId": TEMPLATE_ID,
              "variables": {
                  "#{이름}": customer_name,
                  "#{파일ID}": file_id,
              },
              "disableSms": True,  # 대체 문자 발송 미사용
          },
      }
  }

  try:
    res = requests.post(url, headers=headers, data=json.dumps(payload))
    res_data = res.json()

    if res.status_code == 200:
      print(f"✅ [{customer_name}]님 카카오 알림톡 3시간 뒤 예약 성공!")
      print(f"   - 수신 번호: {clean_phone}")
      print(
          f"   - 발송 예정 시각: {kst_send_time.strftime('%Y-%m-%d %H:%M:%S')}"
      )
      return True
    else:
      print(f"❌ 예약 실패: {res_data}")
      return False
  except Exception as e:
    print(f"⚠️ 요청 중 에러 발생: {e}")
    return False