# -*- coding: utf-8 -*-
"""
[답답명쾌 사주해답소] 사장님 전용 로컬호스트 웹 대시보드
브라우저에서 http://localhost:5000 으로 바로 접속 가능!
"""
from flask import Flask, render_template_string, jsonify, request
import requests
import json

app = Flask(__name__)
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbxFPVPgYvx3q-saacm0OkUuELMb-GomV5UDLTVUGRrSuzxDCQdXywyPePQqVhRxJz25Kw/exec"

@app.route('/api/sheet/applicants')
def get_applicants():
    try:
        res = requests.get(WEB_APP_URL, timeout=10)
        return jsonify(res.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/')
def home():
    # 현재 보고 계신 대시보드를 바로 브라우저로 띄워줍니다.
    return """
    <html>
      <head><title>답답명쾌 사주해답소 로컬 대시보드</title></head>
      <body style="margin:0;padding:0;overflow:hidden;">
        <iframe src="https://ais-pre-ax2dqzpla44lgxtmb4vdcc-633551853832.asia-east1.run.app" 
                style="width:100vw;height:100vh;border:none;"></iframe>
      </body>
    </html>
    """

if __name__ == '__main__':
    print("🚀 [답답명쾌 사주해답소] 로컬 대시보드가 실행되었습니다!")
    print("👉 브라우저 주소창에 입력하세요: http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)