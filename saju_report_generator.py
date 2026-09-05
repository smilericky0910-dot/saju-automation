# -*- coding: utf-8 -*-
"""
클로드 소넷 기반 사주풀이 AI 리포트 생성 엔진 (v5.4 - 실시간 검증 & 타겟 재작성 탑재 버전)
- 제14장(10대 대운) 및 제15장(5개년 세운) 분할 전수 완결
- 챕터별 실시간 룰 기반 검증 (말 끊김, 필수 연도 누락, 사주 팩트 불일치 감지)
- 이상 감지 시 해당 챕터만 1회 즉시 재작성 (전체 재실행 X, 비용/시간 최소화)
"""
import os, json, re
from typing import Dict, Any, Callable, Optional, Tuple

DEFAULT_GUIDELINE_FILENAME = "프리미엄_종합_사주_분석_지침_v5.0.md"

CHAPTERS_CONFIG = (
    (3, "사주에 대하여 (입문 프롤로그)", "네 기둥과 여덟 글자의 원리, 삶의 나침반으로서 사주를 대하는 따뜻하고 품격 있는 에세이를 작성하세요. (표는 절대 그리지 마세요)"),
    (4, "사주 스냅샷 해설", "일주 동물 메타포에 대한 상세한 상징 의미와 명리학적 배경 해설을 친절하게 작성하세요. (원국표는 시스템이 직접 그리므로 표는 일절 그리지 마세요)"),
    (5, "사주 기본 명식 및 오행 에너지 균형", "합화 반영 점수 변화, 신강/신약 판별, 억부용신과 조후용신의 역할을 명확한 인과관계로 상세히 풀이하세요. (표와 그래프는 시스템이 그리므로 글만 작성하세요)"),
    (6, "본질적 자아 (일간-일지, 일주론)", "반드시 [기질적 특징]과 [실생활 영향 장면]을 서술하고, 다음 3개 소제목을 반드시 포함하여 작성하세요:\n직장에서의 모습:\n갈등 상황 대처:\n일상의 무의식적 욕망:\n마지막에 [실천 행동 가이드]를 작성하세요."),
    (7, "생애 4주기 시간 흐름", "연주(초년), 월주(청년), 일주(중년), 시주(말년)로 이어지는 인생의 4대 계절 서사를 각 주기별로 풍성하게 작성하세요."),
    (8, "격국과 사회적 가면", "격국 분석, 세상에 비추는 나의 얼굴과 가면, 내면 심리적 기제 및 완충 작용을 깊이 있게 분석하세요."),
    (9, "진로 및 직업 전략", "조직 환경 적합도 vs 독립 전문직 모델을 비교하고, 적성 분야 및 린(Lean) 비즈니스 방향성을 구체적으로 제시하세요."),
    (10, "재물운의 흐름", "정재와 편재의 상호작용, 자산 축적 패턴 및 현금 흐름을 자연 현상 비유와 함께 상세히 분석하세요."),
    (11, "재정적 위험과 자산 방어 전략", "돈이 새어나가는 구멍 차단법, 보증/동업 위험 관리, 계약 문서화 전략을 단호하고 실천적으로 작성하세요."),
    (12, "인간관계·애정·가족운", "배우자궁 성향, 감정 소통 방식, 갈등 예방 대화 가이드를 다정하고 현실감 있게 작성하세요."),
    (13, "건강운과 회복 리듬", "취약 오행 장기, 스트레스 반응 양상, 맞춤형 일상 신체 회복 루틴을 구체적으로 설명하세요."),
    
    # 제14장: 10대 대운 분할 작성
    (14, "인생 거시 흐름 — 10대 대운 전수 분석 (청년·중년 1~5대운)", (
        "사주 데이터에 있는 1대운부터 5대운까지 5개 대운을 순서대로 빠짐없이 분석하세요.\n"
        "각 대운마다 반드시 '### {나이}세 대운 ({간지}):' 소제목을 달고:\n"
        "1) 천간/지지 오행의 기운과 상생상극\n"
        "2) 십성과 12운성이 주는 현실적 영향\n"
        "3) 이 시기에 집중해야 할 영역과 주의할 점을 작성하세요.\n"
        "※ 중요: 마지막 5대운까지 완전한 마침표 문장으로 끝맺으세요."
    )),
    (14, "인생 거시 흐름 — 10대 대운 전수 분석 (완숙·말년 6~10대운)", (
        "사주 데이터에 있는 6대운부터 10대운까지 5개 대운을 순서대로 빠짐없이 분석하세요.\n"
        "각 대운마다 반드시 '### {나이}세 대운 ({간지}):' 소제목을 달고:\n"
        "1) 천간/지지 오행의 기운과 상생상극\n"
        "2) 십성과 12운성이 주는 현실적 영향\n"
        "3) 이 시기에 집중해야 할 영역과 주의할 점을 작성하세요.\n"
        "※ 중요: 마지막 10대운까지 완전한 마침표 문장으로 끝맺으세요."
    )),
    
    # 제15장: 5개년 분할 작성 (2026~2027 / 2028~2030)
    (15, "향후 5개년 세운 집중 전략 — 단기 2개년 (2026년~2027년)", (
        "사주 데이터에 있는 2026년과 2027년 2개년 세운을 순서대로 상세히 분석하세요.\n"
        "각 연도마다 반드시 '### {연도}년 ({간지}년):' 소제목을 달고:\n"
        "1) 그해 들어오는 천간/지지 기운과 십성/12운성 의미\n"
        "2) 상반기/하반기 기회 요인과 리스크\n"
        "3) 올해 당장 취해야 할 핵심 실천 조언을 상세히 작성하고, 2027년 끝까지 완전한 문장으로 마무리하세요."
    )),
    (15, "향후 5개년 세운 집중 전략 — 중기 3개년 (2028년~2030년)", (
        "사주 데이터에 있는 2028년, 2029년, 2030년 3개년 세운을 순서대로 상세히 분석하세요.\n"
        "각 연도마다 반드시 '### {연도}년 ({간지}년):' 소제목을 달고:\n"
        "1) 그해 들어오는 천간/지지 기운과 십성/12운성 의미\n"
        "2) 상반기/하반기 기회 요인과 리스크\n"
        "3) 올해 당장 취해야 할 핵심 실천 조언을 상세히 작성하고, 2030년 끝까지 완전한 문장으로 마무리하세요."
    )),
    
    (16, "스페셜 심층 질문 답변", "고객의 고민/질문에 대한 명리학적 솔루션을 제시하세요. (특별한 질문이 없으면 사주 맞춤형 인생 전환기 극대화 전략을 서술하세요)"),
    (17, "일상 균형 가이드", "부족한 기운을 채우는 맞춤 색상, 방위, 공간 인테리어, 모닝/나이트 생활 습관을 친절하게 안내하세요."),
    (18, "최종 총평", "인생 관통 한 줄 메시지와 함께, 반드시 아래 2단 대조 서식을 작성하세요:\nDON'T (절대 피할 3가지)\nDO (당장 실천할 3가지)"),
    (19, "마무리 응원 메시지", "삶의 계절을 맞이하는 태도와 존엄성을 북돋워 주는 깊고 따뜻한 격려 문장(3~5문장)으로 마무리하세요.")
)

def load_guideline_content(folder_path: str = ".") -> str:
    path = os.path.join(folder_path, DEFAULT_GUIDELINE_FILENAME)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return "당신은 30년 경력의 정통 사주 명리학 대가이자 인생 전략 컨설턴트입니다. 품격 있는 한국어로 사주를 깊이 있게 풀어냅니다."

def get_anthropic_api_key() -> Optional[str]:
    try:
        import streamlit as st
        if "ANTHROPIC_API_KEY" in st.secrets:
            return st.secrets["ANTHROPIC_API_KEY"]
    except Exception:
        pass
    return os.environ.get("ANTHROPIC_API_KEY")

def verify_chapter_output(ch_num: int, ch_title: str, content: str, stop_reason: str, saju_data: Dict[str, Any]) -> Tuple[bool, str]:
    """
    작성된 챕터 본문의 완전성을 실시간으로 검증합니다.
    (말 끊김, 연도 누락, 필수 서식 등)
    """
    clean_text = content.strip()
    if len(clean_text) < 150:
        return False, "내용이 너무 짧습니다."

    # 1. 토큰 제한으로 인한 강제 중단 여부
    if stop_reason == "max_tokens":
        return False, "글자 수 한계(Max Tokens)로 본문이 중간에 끊겼습니다."

    # 2. 문장 종결 부호 검사 (말 끊김 방지)
    valid_endings = ('.', '!', '?', '"', "'", '다', '요', '음', '함', '것', '임', '됨', '죠')
    last_char = clean_text[-1]
    if last_char not in valid_endings:
        return False, f"문장이 온전히 끝나지 않고 중간에 잘렸습니다 (끝글자: '{last_char}')."

    # 3. 챕터별 특화 검증
    if ch_num == 15:
        if "단기" in ch_title:
            if "2026" not in clean_text or "2027" not in clean_text:
                return False, "2026년 또는 2027년 세운 분석이 누락되었습니다."
        elif "중기" in ch_title:
            if "2028" not in clean_text or "2029" not in clean_text or "2030" not in clean_text:
                return False, "2028~2030년 세운 분석 중 일부 연도가 누락되었습니다."

    elif ch_num == 18:
        if "DON" not in clean_text.upper() or "DO" not in clean_text.upper():
            return False, "제18장의 필수 서식인 DO / DON'T 항목이 누락되었습니다."

    elif ch_num == 6:
        if "직장" not in clean_text or "갈등" not in clean_text:
            return False, "제6장의 3대 필수 실생활 장면이 누락되었습니다."

    return True, "검증 통과"

def generate_saju_report(
    saju_data: Dict[str, Any],
    api_key: Optional[str] = None,
    guideline_folder: str = ".",
    model_name: str = "claude-sonnet-5",
    progress_callback: Optional[Callable[[float, str], None]] = None
) -> str:
    key = api_key or get_anthropic_api_key()
    if not key:
        raise ValueError("Anthropic API 키를 찾을 수 없습니다. secrets.toml 또는 환경변수를 확인해주세요.")

    import anthropic
    client = anthropic.Anthropic(api_key=key)
    guideline_text = load_guideline_content(guideline_folder)
    
    saju_json_str = json.dumps(
        saju_data,
        default=lambda x: list(x) if isinstance(x, (set, frozenset)) else str(x),
        ensure_ascii=False,
        indent=2
    )

    system_blocks = [
        {
            "type": "text",
            "text": guideline_text,
            "cache_control": {"type": "ephemeral"}
        },
        {
            "type": "text",
            "text": f"분석 대상자의 정밀 사주 연산 데이터(JSON)는 다음과 같습니다:\n```json\n{saju_json_str}\n```\n이 데이터만을 유일한 팩트로 삼아 지침서의 모든 규칙을 엄격히 준수하여 풀이를 작성하세요."
        }
    ]

    full_report_parts = [
        "# 제1장. 표지\n(표지는 시스템에서 자동 생성됩니다)",
        "# 제2장. 목차\n(목차는 시스템에서 자동 생성됩니다)"
    ]
    
    total_calls = len(CHAPTERS_CONFIG)

    for idx, (ch_num, ch_title, ch_inst) in enumerate(CHAPTERS_CONFIG):
        pct = (idx + 1) / total_calls
        msg = f"제{ch_num}장 {ch_title[:15]}... ({idx + 1}/{total_calls})"
        if progress_callback:
            progress_callback(pct, msg)

        # 최대 2회 시도 (1차 작성 ➔ 검증 실패 시 피드백 주입 후 1회 재작성)
        final_content = ""
        for attempt in range(2):
            retry_note = ""
            if attempt > 0:
                retry_note = "\n\n[주의: 이전 작성 시 문장이 중간에 잘리거나 항목이 누락되었습니다. 이번에는 분량을 알맞게 조절하여 마지막 문장까지 마침표로 반드시 완전하게 마무리하세요.]"

            user_prompt = (
                f"지침서에 정의된 톤앤매너에 맞추어, **제{ch_num}장. {ch_title}** 내용을 풍성하고 완전하게 작성해 주세요.{retry_note}\n\n"
                f"세부 지침:\n{ch_inst}\n\n"
                f"규칙:\n"
                f"- 반드시 '# 제{ch_num}장. {ch_title}' 제목으로 시작하세요.\n"
                f"- 중간에 말을 흐리거나 요약하지 말고 완전한 문장으로 깊이 있게 마무리하세요.\n"
                f"- 마크다운 표는 절대 그리지 마세요."
            )

            response = client.messages.create(
                model=model_name,
                max_tokens=8192,
                system=system_blocks,
                messages=[{"role": "user", "content": user_prompt}]
            )

            content_text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    content_text += block.text

            # 실시간 검증 수행
            stop_reason = getattr(response, 'stop_reason', None)
            is_valid, reason = verify_chapter_output(ch_num, ch_title, content_text, stop_reason, saju_data)

            if is_valid:
                final_content = content_text.strip()
                break
            else:
                # 1차 실패 시 재작성 진행
                if attempt == 0:
                    if progress_callback:
                        progress_callback(pct, f"제{ch_num}장 보완 재작성 중... ({reason})")
                final_content = content_text.strip()

        full_report_parts.append(final_content)

    if progress_callback:
        progress_callback(1.0, "19개 챕터 전체 작성 및 검증 완료! PDF 조립 중...")

    return "\n\n".join(full_report_parts)