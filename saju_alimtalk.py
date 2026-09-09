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
TEMPLATE_ID = "KA01TP260905091348759MllkxYD7567"


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


def send_saju_alimtalk_immediately(
    customer_name: str, phone_number: str, file_id: str
):
  """구글 드라이브 파일 ID를 받아 즉시 알림톡(카톡 미설치시 대체 문자)을 발송합니다."""

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
              "disableSms": False,  # 대체 문자 발송 사용 (카톡 미설치시 문자로 전송)
          },
      }
  }

  try:
    res = requests.post(url, headers=headers, data=json.dumps(payload))
    res_data = res.json()

    if res.status_code == 200:
      print(f"✅ [{customer_name}]님 카카오 알림톡 즉시 발송 성공!")
      print(f"   - 수신 번호: {clean_phone}")
      return True
    else:
      print(f"❌ 발송 실패: {res_data}")
      return False
  except Exception as e:
    print(f"⚠️ 요청 중 에러 발생: {e}")
    return False