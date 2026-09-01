import sys
import os

# 현재 디렉토리를 경로에 추가하여 모듈을 찾을 수 있게 함
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import gdrive_uploader

print("OAuth 2.0 연동 테스트를 시작합니다...")
print("브라우저 창이 열리면 로그인 및 권한 허용을 진행해주세요.")

try:
    folder_id = "17TNn1c_P4EJDZyL7Ks5irB6P3DFXVHUZ"
    dummy_data = {"meta": {"name": "테스트"}, "result": "이것은 OAuth 테스트 사주 데이터입니다."}
    
    success, res = gdrive_uploader.upload_saju_data("테스트고객", "19900101", dummy_data, folder_id)
    if success:
        print(f"\n[성공] 구글 드라이브에 파일이 정상적으로 생성되었습니다! File ID: {res}")
    else:
        print(f"\n[실패] 오류 발생: {res}")
except Exception as e:
    print(f"\n[오류] 예상치 못한 문제 발생: {e}")
