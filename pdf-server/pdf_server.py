# -*- coding: utf-8 -*-
"""
사주 리포트 PDF 생성 서버 (n8n "PDF 생성" 노드가 호출하는 웹 서비스)
Cloud Run에 배포되어, POST /generate-pdf 로 사주 데이터를 받아 PDF 바이너리를 반환한다.
구글드라이브 업로드는 이 서버가 하지 않는다 — n8n의 다음 노드("구글드라이브 저장")가 담당한다.

실제 렌더링은 pdf_report.py(= "사주 리포트 PDF 자동 조립 및 렌더링 엔진 규칙서" v5.0을
그대로 구현한 모듈, headless Chromium/Playwright 기반)가 전담한다. 이 파일은 그 위에
얹은 얇은 HTTP 래퍼일 뿐이며 렌더링 로직에는 관여하지 않는다.
"""
import os
from datetime import datetime
from urllib.parse import quote

from flask import Flask, request, Response, jsonify

import pdf_report

app = Flask(__name__)


@app.route('/healthz', methods=['GET'])
def healthz():
    return jsonify({'status': 'ok'})


@app.route('/generate-pdf', methods=['POST'])
def generate_pdf_endpoint():
    data = request.get_json(force=True, silent=True) or {}
    saju_data = dict(data.get('saju_data') or {})
    meta = saju_data.get('meta') or {}

    customer_name = data.get('name') or data.get('customer_name') or meta.get('name') or '고객'

    report_markdown = data.get('report_markdown') or saju_data.get('ai_report_markdown')
    if not report_markdown:
        return jsonify({'error': 'report_markdown이 전달되지 않았습니다.'}), 400

    try:
        pdf_bytes = pdf_report.build_pdf(str(report_markdown), saju_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{customer_name}_{timestamp}.pdf"
    return Response(
        pdf_bytes,
        mimetype='application/pdf',
        headers={'Content-Disposition': f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
