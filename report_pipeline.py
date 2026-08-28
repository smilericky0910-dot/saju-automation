"""
2단계: 지침 문서(system prompt) + compute_all() JSON(user message)을 Claude API에 넘겨
실제 사주풀이 리포트를 생성하는 파이프라인.

1단계(원국 계산/JSON 출력)와 분리된 모듈로 둬서, 메인 앱은 이 모듈의 함수만 호출한다.
"""
import json
import os

import anthropic

GUIDELINE_PATH = os.path.join(os.path.dirname(__file__), "프리미엄 종합 사주 · 인생 전략 리포트 분석 지침.txt")
MODEL_ID = "claude-opus-5"
MAX_TOKENS = 64000

OPUS5_INPUT_PER_MTOK = 5.00
OPUS5_OUTPUT_PER_MTOK = 25.00
# 프롬프트 캐싱 단가. 캐시 "기록" 단가는 TTL에 따라 다르다 - 5분 TTL은 1.25배, 우리가
# 쓰는 1시간 TTL은 2배. 캐시 "적중" 단가는 TTL과 무관하게 0.1배(90% 할인)로 동일하다.
OPUS5_CACHE_WRITE_PER_MTOK = OPUS5_INPUT_PER_MTOK * 2.0  # 1시간 TTL 기준
OPUS5_CACHE_READ_PER_MTOK = OPUS5_INPUT_PER_MTOK * 0.1


def load_guideline() -> str:
    with open(GUIDELINE_PATH, "r", encoding="utf-8") as f:
        return f.read()


def resolve_api_key(session_key: str | None) -> str | None:
    """세션에 입력된 키 > 환경변수 > streamlit secrets 순으로 확인."""
    if session_key:
        return session_key
    env_key = os.environ.get("ANTHROPIC_API_KEY")
    if env_key:
        return env_key
    try:
        import streamlit as st
        return st.secrets.get("ANTHROPIC_API_KEY")
    except Exception:
        return None


def build_user_message(saju_data: dict) -> str:
    json_text = json.dumps(saju_data, ensure_ascii=False, indent=2)
    return (
        "아래는 사주 계산 프로그램이 산출한 고객의 사주 데이터(JSON)입니다. "
        "이 JSON 안의 `profile.deep_question`과 `compatibility.requested` 값을 직접 확인해서 "
        "어떤 부가 모드를 함께 적용해야 하는지 스스로 판단하고, 시스템 지침에 따라 리포트를 작성해주세요.\n\n"
        f"```json\n{json_text}\n```"
    )


def estimate_cost(usage) -> float:
    input_cost = (usage.input_tokens / 1_000_000) * OPUS5_INPUT_PER_MTOK
    cache_write_tokens = getattr(usage, "cache_creation_input_tokens", 0) or 0
    cache_read_tokens = getattr(usage, "cache_read_input_tokens", 0) or 0
    cache_write_cost = (cache_write_tokens / 1_000_000) * OPUS5_CACHE_WRITE_PER_MTOK
    cache_read_cost = (cache_read_tokens / 1_000_000) * OPUS5_CACHE_READ_PER_MTOK
    output_cost = (usage.output_tokens / 1_000_000) * OPUS5_OUTPUT_PER_MTOK
    return input_cost + cache_write_cost + cache_read_cost + output_cost


def usage_caption(usage) -> str:
    """화면에 보여줄 토큰/비용 요약 한 줄. 캐시 기록/적중 여부를 함께 표시한다.
    주의: `usage.input_tokens`는 캐시로 처리된 부분(지침 전체)을 포함하지 않는다 -
    캐시 기록분은 cache_creation_input_tokens, 캐시 적중분은 cache_read_input_tokens에
    별도로 잡히므로, 이 셋을 다 더해야 실제로 처리된 입력 전체 크기가 된다."""
    cost = estimate_cost(usage)
    cache_write_tokens = getattr(usage, "cache_creation_input_tokens", 0) or 0
    cache_read_tokens = getattr(usage, "cache_read_input_tokens", 0) or 0
    parts = [
        f"입력 {usage.input_tokens:,} 토큰",
    ]
    if cache_write_tokens:
        parts.append(f"캐시 기록 {cache_write_tokens:,} 토큰(신규, 1.25배 단가)")
    if cache_read_tokens:
        parts.append(f"캐시 적중 {cache_read_tokens:,} 토큰(90% 할인)")
    parts.append(f"출력 {usage.output_tokens:,} 토큰")
    parts.append(f"예상 비용 ${cost:.3f}")
    return " · ".join(parts)


def _stream_call(user_message: str, api_key: str, model: str, max_tokens: int, effort: str,
                  system: str | None = None, result_holder: dict | None = None):
    """공용 스트리밍 호출. yield: 텍스트 조각(str). result_holder를 넘기면 스트리밍이 끝난 뒤
    result_holder['final_message']에 최종 Message(usage, stop_reason 포함)가 채워진다
    (st.write_stream은 텍스트만 소비하므로 반환값 대신 이 방식으로 부가 정보를 꺼낸다)."""
    client = anthropic.Anthropic(api_key=api_key)
    kwargs = {}
    if system is not None:
        # 지침 문서는 매 호출마다 토씨 하나 안 바뀌는 긴 고정 텍스트라 프롬프트 캐싱 대상으로
        # 표시해둔다. 리포트 한 편이 3만 토큰을 넘게 나올 때가 많아서(생성 호출 하나만으로도
        # 몇 분씩 걸림) 기본 5분 TTL로는 "생성 -> 검수 -> 수정" 흐름 안에서도 캐시가 만료되는
        # 경우가 실측으로 확인됨 -> 1시간 TTL로 지정해 같은 세션 안에서는 확실히 재사용되게 함.
        kwargs["system"] = [{
            "type": "text",
            "text": system,
            "cache_control": {"type": "ephemeral", "ttl": "1h"},
        }]

    with client.messages.stream(
        model=model,
        max_tokens=max_tokens,
        thinking={"type": "adaptive"},
        output_config={"effort": effort},
        messages=[{"role": "user", "content": user_message}],
        **kwargs,
    ) as stream:
        for text in stream.text_stream:
            yield text
        final_message = stream.get_final_message()

    if result_holder is not None:
        result_holder['final_message'] = final_message


def stream_report(saju_data: dict, api_key: str, model: str = MODEL_ID, result_holder: dict | None = None):
    """지침(system prompt) + saju_data(user message)로 리포트를 스트리밍 생성한다."""
    guideline = load_guideline()
    user_message = build_user_message(saju_data)
    yield from _stream_call(user_message, api_key, model, MAX_TOKENS, "high",
                             system=guideline, result_holder=result_holder)


def build_verification_message(report_text: str, saju_data: dict) -> str:
    json_text = json.dumps(saju_data, ensure_ascii=False, indent=2)
    return (
        "아래는 완성된 사주 풀이 리포트와, 그 근거가 된 원본 사주 데이터(JSON)입니다. "
        "리포트를 처음부터 다시 쓰지 말고, 아래 기준으로만 검수해주세요.\n\n"
        "1. 사주 스냅샷·각 챕터·최종 총평·마지막 응원 페이지 등 필수 섹션이 빠짐없이 있는지\n"
        "2. 리포트에 언급된 간지·오행 수치·격국·용신·대운·세운 등이 JSON 데이터와 정확히 일치하는지 (수치나 명칭 오류 여부)\n"
        "3. \"프로그램이 계산한\", \"프로그램 연산 결과\" 같은 금지 표현이 등장하는지\n"
        "4. 검증되지 않은 과거 사건을 사실처럼 단정하거나(사건 창작), 확정적 예언을 하는 부분이 있는지\n"
        "5. 별점이나 표(table)를 사용한 부분이 있는지\n"
        "6. 특정 챕터가 다른 챕터에 비해 지나치게 얇거나 깊이가 부족한지\n\n"
        "위 기준에 문제가 없으면 정확히 \"이상 없음\"이라고만 답하세요. "
        "문제가 있으면 어떤 기준의 어느 부분이 문제인지 짧고 구체적으로 목록으로 알려주세요.\n\n"
        f"[사주 데이터 JSON]\n```json\n{json_text}\n```\n\n"
        f"[검수할 리포트]\n{report_text}"
    )


def stream_verification(report_text: str, saju_data: dict, api_key: str, model: str = MODEL_ID,
                         result_holder: dict | None = None):
    """생성된 리포트를 원본 JSON·지침 기준으로 검수하는 스트리밍 제너레이터.
    max_tokens가 너무 낮으면(과거 4000) adaptive thinking이 그 예산을 다 써버려서 정작
    본문(텍스트)이 한 글자도 안 나오고 잘리는 사고가 실제로 발생했다 - 리포트 분량이
    32,000자를 넘는 긴 문서라 "이상 없음"인지 판단하는 데도 사고 과정이 길어질 수 있어서,
    생성과 동일하게 여유 있는 예산을 준다."""
    user_message = build_verification_message(report_text, saju_data)
    yield from _stream_call(user_message, api_key, model, 16000, "high", result_holder=result_holder)


def is_clean_verification(verification_text: str) -> bool:
    return verification_text.strip().startswith("이상 없음")


def build_revision_message(report_text: str, saju_data: dict, issues_text: str) -> str:
    json_text = json.dumps(saju_data, ensure_ascii=False, indent=2)
    return (
        "아래는 기존에 작성한 사주 풀이 리포트와, 검수에서 발견된 문제점입니다. "
        "문제점을 반영해서 리포트 전체를 처음부터 완성된 형태로 다시 작성해주세요. "
        "지적되지 않은 부분은 그대로 유지하고, 지적된 부분만 고치되 리포트 전체를 빠짐없이 다시 출력합니다.\n\n"
        f"[검수에서 발견된 문제]\n{issues_text}\n\n"
        f"[사주 데이터 JSON]\n```json\n{json_text}\n```\n\n"
        f"[기존 리포트]\n{report_text}"
    )


def stream_revision(report_text: str, saju_data: dict, issues_text: str, api_key: str, model: str = MODEL_ID,
                     result_holder: dict | None = None):
    """검수에서 발견된 문제를 반영해 리포트를 다시 작성하는 스트리밍 제너레이터."""
    guideline = load_guideline()
    user_message = build_revision_message(report_text, saju_data, issues_text)
    yield from _stream_call(user_message, api_key, model, MAX_TOKENS, "high",
                             system=guideline, result_holder=result_holder)
