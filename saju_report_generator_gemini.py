# -*- coding: utf-8 -*-
"""
구글 젬나이 2.0 Flash 기반 사주풀이 AI 리포트 생성 엔진
- 클로드 버전과 동일한 챕터 구조 및 검증 로직 유지
- 젬나이 2.0 Flash의 빠른 속도와 넉넉한 출력 토큰 활용
"""
import os, json, re
from typing import Dict, Any, Callable, Optional, Tuple
import google.generativeai as genai

DEFAULT_GUIDELINE_FILENAME = "프리미엄_종합_사주_분석_지침_v5.0.md"

# 챕터 설정은 클로드 버전과 동일하게 유지
from saju_report_generator import CHAPTERS_CONFIG, load_guideline_content, verify_chapter_output

def get_gemini_api_key() -> Optional[str]:
    try:
        import streamlit as st
        if "GEMINI_API_KEY" in st.secrets:
            return st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass
    return os.environ.get("GEMINI_API_KEY")

def verify_and_correct_report_chunk(
    chunk_text: str, 
    saju_data: Dict[str, Any], 
    model: Any
) -> str:
    """
    완성된 텍스트 청크를 원본 사주 데이터와 대조하여 팩트 오류를 수정합니다.
    """
    saju_json_str = json.dumps(
        saju_data,
        default=lambda x: list(x) if isinstance(x, (set, frozenset)) else str(x),
        ensure_ascii=False,
        indent=2
    )
    
    prompt = (
        "당신은 사주 명리학 전문 팩트 체커입니다.\n"
        "다음은 생성된 사주 리포트의 일부입니다.\n"
        "원본 사주 데이터(JSON)와 텍스트를 대조하여 명백한 팩트 오류(나이, 대운, 용신, 세운 연도, 오행 등)가 있는지 검사하세요.\n"
        "오류가 있다면 해당 내용만 수정하고, 문체, 어조, 문장 구조, 분량은 절대로 변경하지 마세요.\n"
        "오류가 없다면 원문 그대로 출력하세요.\n"
        "수정된 최종 마크다운 텍스트만 출력하세요 (부연 설명 금지).\n\n"
        f"[원본 사주 데이터]\n```json\n{saju_json_str}\n```\n\n"
        f"[생성된 리포트 텍스트]\n{chunk_text}"
    )
    
    generation_config = genai.types.GenerationConfig(
        temperature=0.1,  # 팩트 체크는 창의성 최소화
    )
    
    try:
        response = model.generate_content(prompt, generation_config=generation_config)
        return response.text.strip()
    except Exception as e:
        print(f"[Gemini Verification ERROR] {type(e).__name__}: {e}", flush=True)
        return chunk_text  # 에러 시 원본 반환

def generate_saju_report_gemini(
    saju_data: Dict[str, Any],
    api_key: Optional[str] = None,
    guideline_folder: str = ".",
    model_name: str = "gemini-3.6-flash",
    progress_callback: Optional[Callable[[float, str], None]] = None
) -> str:
    key = api_key or get_gemini_api_key()
    if not key:
        raise ValueError("Gemini API 키를 찾을 수 없습니다. secrets.toml 또는 환경변수를 확인해주세요.")

    genai.configure(api_key=key)
    model = genai.GenerativeModel(model_name)

    guideline_text = load_guideline_content(guideline_folder)

    saju_json_str = json.dumps(
        saju_data,
        default=lambda x: list(x) if isinstance(x, (set, frozenset)) else str(x),
        ensure_ascii=False,
        indent=2
    )

    # 시스템 프롬프트 (지침서 + 사주 JSON 데이터)
    system_prompt = (
        f"{guideline_text}\n\n"
        f"---\n"
        f"분석 대상자의 정밀 사주 연산 데이터(JSON)는 다음과 같습니다:\n"
        f"```json\n{saju_json_str}\n```\n"
        f"이 데이터만을 유일한 팩트로 삼아 지침서의 모든 규칙을 엄격히 준수하여 풀이를 작성하세요."
    )

    generation_config = genai.types.GenerationConfig(
        temperature=0.9,
    )

    full_report_parts = [
        "# 제1장. 표지\n(표지는 시스템에서 자동 생성됩니다)",
        "# 제2장. 목차\n(목차는 시스템에서 자동 생성됩니다)"
    ]

    active_chapters = list(CHAPTERS_CONFIG)
    if saju_data.get('compatibility', {}).get('requested', False):
        insert_idx = len(active_chapters)
        for i, (c_num, c_title, _) in enumerate(active_chapters):
            if c_num == 18:
                insert_idx = i
                break
        active_chapters.insert(insert_idx, (20, "두 사람의 인연과 정밀 궁합 분석", "상대방의 데이터(partner_saju)를 바탕으로 지침서의 [조건부 확장] 모듈에 따라 두 사람의 시너지와 갈등 요인을 심층 분석하세요. 우열을 판정하지 말고 상호작용의 지도를 그려주세요. (반드시 독립된 챕터로 작성)"))

    total_calls = len(active_chapters)

    for idx, (ch_num, ch_title, ch_inst) in enumerate(active_chapters):
        pct = (idx + 1) / total_calls
        msg = f"제{ch_num}장 {ch_title[:15]}... ({idx + 1}/{total_calls})"
        if progress_callback:
            progress_callback(pct, msg)

        user_prompt = (
            f"지침서에 정의된 톤앤매너에 맞추어, **제{ch_num}장. {ch_title}** 내용을 풍성하고 완전하게 작성해 주세요.\n\n"
            f"세부 지침:\n{ch_inst}\n\n"
            f"규칙:\n"
            f"- 반드시 '# 제{ch_num}장. {ch_title}' 제목으로 시작하세요.\n"
            f"- 중간에 말을 흐리거나 요약하지 말고 완전한 문장으로 깊이 있게 마무리하세요.\n"
            f"- 마크다운 표는 절대 그리지 마세요."
        )

        final_content = ""

        # 최대 3회 시도 (이어서 쓰기 또는 누락 내용 보완)
        chat = model.start_chat(history=[])
        # 첫 메시지에 시스템 프롬프트 포함
        full_first_prompt = f"{system_prompt}\n\n---\n\n{user_prompt}"

        for attempt in range(3):
            try:
                if attempt == 0:
                    print(f"[Gemini] 제{ch_num}장 작성 시도 중...", flush=True)
                    response = chat.send_message(
                        full_first_prompt,
                        generation_config=generation_config
                    )
                    print(f"[Gemini] 제{ch_num}장 응답 수신 완료", flush=True)
                else:
                    # 이어서 쓰기 또는 보완 요청
                    if "max_tokens" in last_stop_reason or "문장이 온전히 끝나지 않고" in last_reason:
                        if progress_callback:
                            progress_callback(pct, f"제{ch_num}장 이어서 작성 중... ({last_reason})")
                        continue_prompt = "글자 수 제한으로 인해 내용이 중간에 끊겼습니다. 내용이 중복되지 않게, 방금 끊긴 부분부터 문맥을 자연스럽게 유지하여 계속 이어서 끝까지 작성해주세요."
                    else:
                        if progress_callback:
                            progress_callback(pct, f"제{ch_num}장 보완 내용 추가 중... ({last_reason})")
                        continue_prompt = f"작성된 내용 중 다음 사항이 누락되거나 부족합니다: {last_reason}\n이 부분을 보완하여 내용을 추가로 이어서 작성해주세요."
                    response = chat.send_message(continue_prompt, generation_config=generation_config)

                content_text = response.text
                final_content += content_text

                # 젬나이는 finish_reason으로 중단 이유 확인
                finish_reason = "stop"
                if response.candidates and response.candidates[0].finish_reason:
                    fr = response.candidates[0].finish_reason
                    # finish_reason 2 = MAX_TOKENS
                    if str(fr) in ("2", "MAX_TOKENS", "FinishReason.MAX_TOKENS"):
                        finish_reason = "max_tokens"

                is_valid, reason = verify_chapter_output(ch_num, ch_title, final_content, finish_reason, saju_data)

                if is_valid:
                    final_content = final_content.strip()
                    break
                else:
                    last_stop_reason = finish_reason
                    last_reason = reason
                    if attempt == 2:
                        final_content = final_content.strip()

            except Exception as e:
                print(f"[Gemini ERROR] 제{ch_num}장 오류: {type(e).__name__}: {e}", flush=True)
                final_content = final_content.strip() if final_content else f"[제{ch_num}장 생성 중 오류 발생: {e}]"
                break

        full_report_parts.append(final_content)

    # --- 2단계: 최종 일괄 검증 및 교정 (Self-Correction) ---
    if progress_callback:
        progress_callback(0.9, "글쓰기 완료! 전반부 팩트 교정 중...")
    
    # 표지(index 0), 목차(index 1)는 제외하고 본문만 합침
    # 전반부 (제3장 ~ 제11장)
    first_half_idx = min(11, len(full_report_parts))
    first_half_text = "\n\n".join(full_report_parts[2:first_half_idx])
    corrected_first_half = verify_and_correct_report_chunk(first_half_text, saju_data, model)
    
    if progress_callback:
        progress_callback(0.95, "전반부 교정 완료! 후반부 팩트 교정 중...")
        
    # 후반부 (제12장 ~ 끝장)
    second_half_text = "\n\n".join(full_report_parts[first_half_idx:])
    corrected_second_half = verify_and_correct_report_chunk(second_half_text, saju_data, model)
    
    if progress_callback:
        progress_callback(1.0, f"{total_calls}개 챕터 팩트 검증 완료! PDF 조립 중...")

    # 조립: 표지 + 목차 + 교정된 전반부 + 교정된 후반부
    final_report = [
        full_report_parts[0],
        full_report_parts[1],
        corrected_first_half,
        corrected_second_half
    ]

    return "\n\n".join(final_report)
