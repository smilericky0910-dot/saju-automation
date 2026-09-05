import io
import os
from datetime import datetime
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaFileUpload

# 구글 드라이브 권한 범위
SCOPES = ['https://www.googleapis.com/auth/drive']

# 지정하신 루트 폴더 ID (고객사주 PDF 폴더)
ROOT_FOLDER_ID = "17TNn1c_P4EJDZyL7Ks5irB6P3DFXVHUZ"


def get_drive_service():
    """구글 드라이브 API 인증 및 서비스 빌드"""
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('client_secrets.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return build('drive', 'v3', credentials=creds)


def get_or_create_folder(service, folder_name: str, parent_id: str) -> str:
    """
    부모 폴더 내에 folder_name 폴더가 존재하면 해당 ID 반환,
    없으면 새로 생성 후 ID 반환
    """
    query = (
        f"name = '{folder_name}' and "
        f"'{parent_id}' in parents and "
        f"mimeType = 'application/vnd.google-apps.folder' and "
        f"trashed = false"
    )
    results = service.files().list(
        q=query,
        spaces='drive',
        fields='files(id, name)'
    ).execute()
    items = results.get('files', [])

    if items:
        return items[0]['id']
    else:
        folder_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent_id]
        }
        folder = service.files().create(
            body=folder_metadata,
            fields='id'
        ).execute()
        return folder.get('id')


def upload_pdf_to_date_folder(file_content, filename: str, date_obj=None, contact_info: dict = None) -> dict:
    """
    구글 드라이브의 고객사주 PDF > YYYY-MM > YYYY-MM-DD 폴더에 PDF를 업로드합니다.
    연락처(휴대폰, 이메일)는 드라이브 파일의 description과 properties 메타데이터에 기록되어
    추후 발송 자동화(n8n 등)에서 파일 자체를 열지 않고도 바로 읽을 수 있습니다.
    """
    service = get_drive_service()

    if date_obj is None:
        date_obj = datetime.now()

    if contact_info is None:
        contact_info = {}

    phone = contact_info.get('phone', '')
    email = contact_info.get('email', '')

    month_folder_name = date_obj.strftime("%Y-%m")      # 예: 2026-09
    date_folder_name = date_obj.strftime("%Y-%m-%d")    # 예: 2026-09-05

    # 1. 월별 폴더 확인 및 생성
    month_folder_id = get_or_create_folder(service, month_folder_name, ROOT_FOLDER_ID)

    # 2. 일별 폴더 확인 및 생성
    target_folder_id = get_or_create_folder(service, date_folder_name, month_folder_id)

    # 3. 파일 메타데이터 정의 (연락처를 properties와 description에 박아둠)
    file_metadata = {
        'name': filename,
        'parents': [target_folder_id],
        'description': f"고객 연락처\n- 휴대폰: {phone}\n- 이메일: {email}",
        'properties': {
            'phone': phone,
            'email': email,
            'sendStatus': 'pending'  # 발송 상태 플래그
        }
    }

    # 4. 메모리 스트림 또는 로컬 파일 준비
    if isinstance(file_content, (bytes, bytearray)):
        media = MediaIoBaseUpload(io.BytesIO(file_content), mimetype='application/pdf', resumable=True)
    elif isinstance(file_content, io.BytesIO):
        file_content.seek(0)
        media = MediaIoBaseUpload(file_content, mimetype='application/pdf', resumable=True)
    elif isinstance(file_content, str) and os.path.exists(file_content):
        media = MediaFileUpload(file_content, mimetype='application/pdf', resumable=True)
    else:
        raise ValueError("유효한 PDF 바이트 또는 파일 경로가 아닙니다.")

    # 5. 구글 드라이브 업로드 실행
    uploaded_file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id, name, webViewLink, webContentLink, properties, description'
    ).execute()

    return uploaded_file