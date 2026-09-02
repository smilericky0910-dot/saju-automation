import os
import io
import json
from datetime import datetime
import requests
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

SCOPES = ['https://www.googleapis.com/auth/drive.file', 'https://www.googleapis.com/auth/drive']
CLIENT_SECRET_FILE = 'client_secrets.json'
TOKEN_FILE = 'token.json'

def get_drive_service():
    """Authenticate via OAuth and return the Google Drive API service."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    creds_path = os.path.join(base_dir, CLIENT_SECRET_FILE)
    token_path = os.path.join(base_dir, TOKEN_FILE)
    
    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(creds_path):
                raise FileNotFoundError(f"{CLIENT_SECRET_FILE} 파일이 없습니다. OAuth 클라이언트 ID를 다운로드 해주세요.")
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            # This will open a browser window for the user to login
            creds = flow.run_local_server(port=0)
            
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
            
    service = build('drive', 'v3', credentials=creds)
    return service

def get_or_create_folder(service, folder_name, parent_id):
    """Find a folder by name inside parent_id, create it if it doesn't exist."""
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and '{parent_id}' in parents and trashed=false"
    results = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    items = results.get('files', [])
    
    if items:
        return items[0]['id']
    else:
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent_id]
        }
        folder = service.files().create(body=file_metadata, fields='id').execute()
        return folder.get('id')

def format_saju_data_to_json(saju_data):
    """분석엔진(compute_all())의 결과 dict를 그대로, 필드 누락 없이 순수 JSON 텍스트로 직렬화한다.
    풀이 AI가 마크다운 코드펜스를 벗겨낼 필요 없이 바로 파싱할 수 있도록 원시 JSON만 담는다."""
    return json.dumps(
        saju_data, ensure_ascii=False, indent=2,
        default=lambda x: list(x) if isinstance(x, (set, frozenset)) else str(x),
    )

def _safe_str(value):
    return str(value).replace("/", "").replace("-", "").strip()

def _upload_text_file(service, day_folder_id, file_name, text_content):
    # 노트북LM의 "드라이브에서 추가" 소스 선택창이 .json을 지원 파일 목록에 안 보여줘서
    # 소스로 추가가 안 되는 문제가 있었음 — 내용은 그대로 완전한 JSON, 확장자/마임타입만
    # 텍스트 파일로 바꿔서 노트북LM이 소스로 인식할 수 있게 한다.
    media = MediaIoBaseUpload(io.BytesIO(text_content.encode('utf-8')), mimetype='text/plain', resumable=True)
    file = service.files().create(body={'name': file_name, 'parents': [day_folder_id]}, media_body=media, fields='id').execute()
    return file.get('id')

def upload_saju_data(customer_name, customer_birth_str, saju_data, root_folder_id):
    """신청인의 사주 분석 결과를 구글 드라이브에 저장한다.
    궁합 분석이 함께 신청되어 상대방 사주(compatibility.partner_saju)가 계산되어 있으면,
    두 사람의 분석을 한 파일에 합치지 않고 완전히 별도의 파일 두 개로 나눠서 저장한다
    (이 프로그램은 두 사람 각각의 원본 분석값만 만들고, 궁합 풀이·조합 판단은 하지 않는다).
    반환값: (True, {'customer': 신청인_file_id, 'partner': 상대방_file_id 또는 없으면 생략}) / (False, 에러메시지)
    """
    try:
        service = get_drive_service()

        now = datetime.now()
        month_folder_id = get_or_create_folder(service, now.strftime("%Y-%m"), root_folder_id)
        day_folder_id = get_or_create_folder(service, now.strftime("%Y-%m-%d"), month_folder_id)

        # 신청인 파일: compatibility에서 partner_saju(상대방 전체 분석)는 빼고,
        # 상대방이 누구인지 식별할 수 있는 정보(이름/성별/유형 등)만 남긴다 — 실제 상대방 분석은 별도 파일로 저장.
        compat = dict(saju_data.get('compatibility') or {})
        partner_saju = compat.pop('partner_saju', None)
        customer_data = dict(saju_data)
        customer_data['compatibility'] = compat

        safe_birth_str = _safe_str(customer_birth_str)
        customer_file_name = f"{customer_name}_{safe_birth_str}_사주분석결과.txt"
        customer_content = format_saju_data_to_json(customer_data)
        file_ids = {'customer': _upload_text_file(service, day_folder_id, customer_file_name, customer_content)}

        if compat.get('requested') and partner_saju:
            partner_name = compat.get('partner_name') or "상대방"
            partner_birth = (partner_saju.get('meta') or {}).get('birth_date') or "생년월일미상"
            partner_file_name = f"{partner_name}_{_safe_str(partner_birth)}_사주분석결과(궁합상대방).txt"
            partner_content = format_saju_data_to_json(partner_saju)
            file_ids['partner'] = _upload_text_file(service, day_folder_id, partner_file_name, partner_content)

        return True, file_ids

    except Exception as e:
        return False, str(e)


def send_to_n8n_webhook(customer_name, customer_birth_str, saju_data, webhook_url, webhook_secret):
    """신청인(및 궁합 상대방이 있으면 상대방도 별도로) 사주 분석 결과를 n8n 웹훅으로 전송해서
    풀이(해석) 파이프라인을 바로 트리거한다. 드라이브 저장과 별개의 경로로, 저장이 실패해도
    이 전송은 독립적으로 시도된다.
    반환값: (True, None) / (False, 에러메시지)
    """
    try:
        compat = dict(saju_data.get('compatibility') or {})
        partner_saju = compat.pop('partner_saju', None)
        customer_data = dict(saju_data)
        customer_data['compatibility'] = compat

        headers = {'X-Webhook-Secret': webhook_secret, 'Content-Type': 'application/json'}

        payload = {'role': 'customer', 'name': customer_name, 'birth_date': customer_birth_str, 'saju_data': customer_data}
        resp = requests.post(webhook_url, headers=headers, data=format_saju_data_to_json(payload), timeout=30)
        resp.raise_for_status()

        if compat.get('requested') and partner_saju:
            partner_name = compat.get('partner_name') or "상대방"
            partner_birth = (partner_saju.get('meta') or {}).get('birth_date') or "생년월일미상"
            partner_payload = {'role': 'partner', 'name': partner_name, 'birth_date': partner_birth, 'saju_data': partner_saju}
            resp2 = requests.post(webhook_url, headers=headers, data=format_saju_data_to_json(partner_payload), timeout=30)
            resp2.raise_for_status()

        return True, None

    except Exception as e:
        return False, str(e)
