# -*- coding: utf-8 -*-
import os
import json
import requests

def load_quick_guideline():
    path = "퀵사주 풀이 지침.txt"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return "당신은 사주 명리학 대가입니다."

def generate_quick_report(saju_data, deep_question, api_key):
    system_prompt = load_quick_guideline()

    saju_json_str = json.dumps(
        saju_data,
        default=lambda x: list(x) if isinstance(x, (set, frozenset)) else str(x),
        ensure_ascii=False,
        indent=2
    )

    question_text = deep_question if deep_question and str(deep_question).strip() not in ("", "없음", "None") \
        else "특별한 고민/질문 없음 (사주의 전반적인 핵심 기운과 강점 위주로 설명해주세요)"

    prompt = (
        f"고객의 정밀 사주 연산 데이터(JSON)는 다음과 같습니다:\n"
        f"```json\n{saju_json_str}\n```\n\n"
        f"고객의 단품 질문(고민): {question_text}\n\n"
        f"이 사주 데이터와 고객의 질문을 바탕으로, 시스템 지침서의 [PART 1]과 [PART 2] 형식을 엄격히 지켜서 답변을 작성해주세요."
    )

    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }

    payload = {
        "model": "claude-haiku-4-5",
        "max_tokens": 2500,
        "system": system_prompt,
        "messages": [{"role": "user", "content": prompt}]
    }

    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers=headers,
        json=payload,
        timeout=60
    )

    if response.status_code != 200:
        raise Exception(f"API 오류 ({response.status_code}): {response.text}")

    return response.json()["content"][0]["text"]

