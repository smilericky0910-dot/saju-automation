# -*- coding: utf-8 -*-
"""
사주분석 엔진 확장 모듈 (V8 Enhanced)
사주_프로그램_V8_Enhanced_Complete.py 가 import 하여 사용하는 공용 엔진 모듈입니다.
- 納音五行(납음오행) - 60갑자 전체
- 形(형)/害(해) 관계 분석
- 公望(공망) 계산
- 月令(월령) 득령/실령 판정
- 格局(격국) 자동 판별
- 인생영역별 분석 (배우자운, 재운, 직업운)
- 주요 신살 (도화살, 양인살, 괴강살, 천을귀인, 문창귀인, 원진살)
"""

STEMS_LIST = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']
BRANCHES_LIST = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']

GANJI_60 = []
for _i in range(60):
    GANJI_60.append(STEMS_LIST[_i % 10] + BRANCHES_LIST[_i % 12])

# ============================================================================
# [1] 納音五行 (납음오행) - 60갑자 전체를 30개 짝으로 완전 매핑
# ============================================================================
_NAEUM_PAIRS = [
    ('海中金', '해중금', '金', '바다 속 깊이 잠긴 금, 신비롭고 잠재력을 품은 기운'),
    ('爐中火', '노중화', '火', '용광로 속 뜨거운 불, 강렬한 추진력과 변화의 기운'),
    ('大林木', '대림목', '木', '울창한 숲의 큰 나무, 풍성한 성장과 포용의 기운'),
    ('路旁土', '노방토', '土', '길가에 놓인 흙, 만인이 딛고 지나는 소박하고 실용적인 기운'),
    ('劍鋒金', '검봉금', '金', '칼끝의 예리한 금, 결단력 있고 강인한 기운'),
    ('山頭火', '산두화', '火', '산꼭대기를 밝히는 불, 높이 드러나는 화려한 기운'),
    ('澗下水', '간하수', '水', '산골짜기를 흐르는 물, 맑고 겸손하게 흐르는 기운'),
    ('城頭土', '성두토', '土', '성벽 위의 흙, 견고하게 지키고 보호하는 기운'),
    ('白蠟金', '백랍금', '金', '밀랍처럼 부드러운 금, 온화하면서도 단단한 기운'),
    ('楊柳木', '양류목', '木', '바람에 휘는 버드나무, 유연하고 적응력이 뛰어난 기운'),
    ('泉中水', '천중수', '水', '샘 속에서 솟아나는 물, 맑고 끊임없이 이어지는 기운'),
    ('屋上土', '옥상토', '土', '지붕 위의 흙, 높은 곳에서 안정을 지키는 기운'),
    ('霹靂火', '벽력화', '火', '벼락처럼 순간적으로 터지는 불, 급격하고 강렬한 기운'),
    ('松柏木', '송백목', '木', '소나무와 잣나무, 사철 푸르고 지조 있는 기운'),
    ('長流水', '장류수', '水', '끊임없이 흐르는 긴 강물, 지속적이고 풍요로운 기운'),
    ('沙中金', '사중금', '金', '모래 속에 숨은 금, 겉으로 드러나지 않는 잠재된 가치의 기운'),
    ('山下火', '산하화', '火', '산 아래를 비추는 불, 은근하고 따스하게 퍼지는 기운'),
    ('平地木', '평지목', '木', '평지에 뿌리내린 나무, 안정되고 실속 있게 자라는 기운'),
    ('壁上土', '벽상토', '土', '벽 위에 발린 흙, 구조를 지탱하는 견고한 기운'),
    ('金箔金', '금박금', '金', '얇게 편 금박, 화려하고 눈에 띄는 기운'),
    ('覆燈火', '복등화', '火', '등불을 덮어 은은히 비추는 불, 절제되고 온화한 기운'),
    ('天河水', '천하수', '水', '은하수처럼 광대한 물, 크고 깊은 스케일의 기운'),
    ('大驛土', '대역토', '土', '많은 사람이 오가는 역참의 흙, 분주하고 변화가 많은 기운'),
    ('釵釧金', '채천금', '金', '비녀와 팔찌 같은 장신구의 금, 섬세하고 화려한 기운'),
    ('桑柘木', '상자목', '木', '뽕나무, 부지런히 결실을 맺어가는 실용적인 기운'),
    ('大溪水', '대계수', '水', '큰 시냇물, 힘차게 흐르며 나아가는 기운'),
    ('沙中土', '사중토', '土', '모래 속에 섞인 흙, 은근하지만 단단하게 다져지는 기운'),
    ('天上火', '천상화', '火', '하늘 위에서 빛나는 불, 밝고 강렬하게 비추는 기운'),
    ('石榴木', '석류목', '木', '석류나무, 알알이 결실을 맺는 다산과 풍요의 기운'),
    ('大海水', '대해수', '水', '모든 것을 품는 큰 바다, 깊고 넓은 포용력의 기운'),
]

NAEUM_OHAENG = {}
for _i, _ganji in enumerate(GANJI_60):
    _hanja, _kname, _elem, _desc = _NAEUM_PAIRS[_i // 2]
    NAEUM_OHAENG[_ganji] = {'ohaeng': _elem, 'name': f'{_hanja}({_kname})', 'desc': _desc}


def get_naeum_ohaeng(ganji):
    """납음오행 조회 (60갑자 전체 지원)"""
    return NAEUM_OHAENG.get(ganji, {'ohaeng': '미상', 'name': '불명', 'desc': '납음오행 정보 없음'})


# ============================================================================
# [2] 形(형) / 害(해) 관계 - 지지 간 형/해를 하나의 표로 통합 (양방향 매칭)
# ============================================================================
_XING_HAE_PAIRS = [
    ('子', '卯', '형', '자묘형(子卯形)', '자와 묘가 만나면 서로를 상처입히는 무례지형(無禮之刑)의 기운'),
    ('丑', '戌', '형', '축술형(丑戌形)', '축과 술이 만나면 서로를 다치게 하는 지세지형(持勢之刑)의 기운'),
    ('寅', '巳', '형', '인사형(寅巳形)', '인과 사가 만나면 은혜를 원수로 갚는 무은지형(無恩之刑)의 기운'),
    ('申', '亥', '형', '신해형(申亥形)', '신과 해가 만나면 상호 모순되는 기운'),
    ('子', '未', '해', '자미해(子未害)', '자와 미가 만나면 서로 해롭게 하는 기운'),
    ('丑', '午', '해', '축오해(丑午害)', '축과 오가 만나면 불편하고 막히는 기운'),
    ('卯', '辰', '해', '묘진해(卯辰害)', '묘와 진이 만나면 제약과 방해가 따르는 기운'),
    ('午', '未', '해', '오미해(午未害)', '오와 미가 만나면 번거로운 일이 잦아지는 기운'),
    ('酉', '戌', '해', '유술해(酉戌害)', '유와 술이 만나면 매사에 걸리적거리는 기운'),
]

BRANCH_XING_HAE = {}
for _b1, _b2, _type, _name, _desc in _XING_HAE_PAIRS:
    BRANCH_XING_HAE[(_b1, _b2)] = (_type, _name, _desc)
    BRANCH_XING_HAE[(_b2, _b1)] = (_type, _name, _desc)


def check_xing_hae(branch1, branch2):
    """형/해 관계 확인 (순서에 상관없이 매칭)"""
    pair = BRANCH_XING_HAE.get((branch1, branch2))
    if pair:
        type_, name, desc = pair
        return {'type': type_, 'name': name, 'desc': desc, 'exists': True}
    return {'exists': False}


# ============================================================================
# [3] 格局(격국) 판별은 사주_프로그램_V8_Enhanced_Complete.py 의
# determine_guckguk_by_wolji() 에서 처리합니다 (월지 지장간 정기 기준, 정통 방식).
# 여기서는 지장간 원본 데이터(BRANCH_INFO)를 쓰기 때문에 메인 파일에 둡니다.
# ============================================================================

# ============================================================================
# [4] 公望(공망) 계산 - 일주(日柱) 기준 순(旬)의 공망 지지를 정확히 산출
# ============================================================================
def calculate_gongmang(day_stem, day_branch):
    """
    공망(空亡) 계산
    60갑자를 10개씩 6개의 순(旬)으로 나눌 때, 각 순에서 짝을 이루지 못하는
    2개의 지지가 그 순의 공망이 됩니다. (예: 갑자순의 공망은 술·해)
    """
    ganji = day_stem + day_branch
    if ganji not in GANJI_60:
        return {'branches': (), 'sun_name': '', 'desc': '공망 판별 불가'}

    idx = GANJI_60.index(ganji)
    group = idx // 10
    branch_start = (group * 10) % 12
    b1 = BRANCHES_LIST[(branch_start + 10) % 12]
    b2 = BRANCHES_LIST[(branch_start + 11) % 12]
    sun_name = GANJI_60[group * 10] + '순(旬)'

    return {
        'branches': (b1, b2),
        'sun_name': sun_name,
        'desc': f'일주 {ganji}는 {sun_name}에 속하며, 이 순의 공망은 {b1}·{b2}입니다. 원국이나 대운에 {b1} 또는 {b2}가 오면 그 기운의 효력이 감소합니다.'
    }


# ============================================================================
# [5] 月令(월령) 득령/실령 판정 - 일간의 월지 12운성을 기준으로 판정
# ============================================================================
def classify_deukryeong(unseong_name):
    """월지에서의 12운성을 기준으로 득령/반득령/실령을 판정"""
    if unseong_name in ('건록', '제왕'):
        return {'status': '득령(得令)', 'desc': '일간이 태어난 달(월지)에서 가장 왕성한 힘을 얻어, 원국의 기본 체력이 강한 편입니다.'}
    elif unseong_name in ('장생', '관대', '양'):
        return {'status': '반득령(半得令)', 'desc': '일간이 월지에서 어느 정도 힘을 받아, 무난하게 세력을 유지하는 편입니다.'}
    else:
        return {'status': '실령(失令)', 'desc': '일간이 태어난 달(월지)에서 힘을 얻지 못해, 다른 오행(비겁·인성 등)의 도움이 더욱 중요해집니다.'}


# ============================================================================
# [5-1] 월령(月令) 왕상휴수사(旺相休囚死) - 계절에 따른 오행별 강약 배율
# ============================================================================
_GENERATION = {'木': '火', '火': '土', '土': '金', '金': '水', '水': '木'}
_OVERCOME = {'木': '土', '火': '金', '土': '水', '金': '木', '水': '火'}
_REV_GENERATION = {v: k for k, v in _GENERATION.items()}
_REV_OVERCOME = {v: k for k, v in _OVERCOME.items()}

WANGSANG_MULTIPLIER = {'왕': 1.4, '상': 1.15, '휴': 0.9, '수': 0.7, '사': 0.5}

_BRANCH_ELEMENT = {
    '寅': '木', '卯': '木', '辰': '土', '巳': '火', '午': '火', '未': '土',
    '申': '金', '酉': '金', '戌': '土', '亥': '水', '子': '水', '丑': '土',
}


def get_season_multipliers(month_branch):
    """
    월지(月支)의 오행을 기준으로 한 왕상휴수사(旺相休囚死) - 오행별 강약 배율.
    - 왕(旺): 월지와 같은 오행 → 가장 왕성
    - 상(相): 월지 오행이 생(生)하는 오행 → 상승세
    - 휴(休): 월지 오행을 생(生)하는 오행(월지의 '어머니') → 한숨 돌리는 상태
    - 수(囚): 월지 오행이 극(剋)하는 오행 → 억눌린 상태
    - 사(死): 월지 오행을 극(剋)하는 오행 → 가장 쇠약
    신강/신약 판정 시 원국 오행 점수에 이 배율을 곱해 계절 영향을 반영한다.
    """
    season_elem = _BRANCH_ELEMENT.get(month_branch, '土')
    status_by_element = {
        season_elem: '왕',
        _GENERATION[season_elem]: '상',
        _REV_GENERATION[season_elem]: '휴',
        _OVERCOME[season_elem]: '수',
        _REV_OVERCOME[season_elem]: '사',
    }
    multipliers = {elem: WANGSANG_MULTIPLIER[status] for elem, status in status_by_element.items()}
    return {
        'season_element': season_elem,
        'status_by_element': status_by_element,
        'multipliers': multipliers,
    }


# ============================================================================
# [5-2] 용신(用神) 교차검증 - 조후용신(調候用神) / 통관용신(通關用神)
# ============================================================================
_COLD_MONTHS = {'亥', '子', '丑'}   # 겨울 - 한랭(寒冷)
_HOT_MONTHS = {'巳', '午', '未'}    # 여름 - 조열(燥熱)


def analyze_johu_yongshin(month_branch, adj_scores):
    """
    조후용신(調候用神) - 태어난 계절의 한난조습(寒暖燥濕)을 보정하는 데 필요한 오행.
    정통 궁통보감의 일간×월지 세부 조견표 대신, 계절의 한랭/조열 여부와 원국 내
    화(火)·수(水) 기운의 실제 잔여량을 함께 보는 실용적 방식을 사용한다.
    """
    if month_branch in _COLD_MONTHS:
        need_elem = '火'
        reason = '겨울(亥子丑月)에 태어나 원국이 한랭해지기 쉬운데'
    elif month_branch in _HOT_MONTHS:
        need_elem = '水'
        reason = '여름(巳午未月)에 태어나 원국이 조열해지기 쉬운데'
    else:
        return {
            'needed': False, 'element': None,
            'desc': '태어난 계절(봄/가을)은 한난조습이 극단적이지 않아 조후 문제가 두드러지지 않습니다.'
        }

    total = sum(adj_scores.values()) or 1
    ratio = adj_scores.get(need_elem, 0) / total * 100

    if ratio < 12:
        return {
            'needed': True, 'element': need_elem, 'urgent': True, 'ratio': ratio,
            'desc': f'{reason}, 원국에 {need_elem} 기운이 {ratio:.1f}%로 부족합니다. 조후상 {need_elem} 기운을 보완하는 것이 시급합니다.'
        }
    return {
        'needed': True, 'element': need_elem, 'urgent': False, 'ratio': ratio,
        'desc': f'{reason}, 원국에 {need_elem} 기운이 {ratio:.1f}%로 어느 정도 갖춰져 있어 조후 문제는 심각하지 않습니다.'
    }


def analyze_tonggwan_yongshin(adj_scores):
    """
    통관용신(通關用神) - 원국 내 가장 강한 두 오행이 상극(相剋) 관계로 팽팽히 맞설 때,
    그 사이를 생(生)으로 이어주는 중재 오행을 찾는다.
    """
    sorted_elems = sorted(adj_scores.items(), key=lambda x: -x[1])
    top1, top1_score = sorted_elems[0]
    top2, top2_score = sorted_elems[1]
    total = sum(adj_scores.values()) or 1

    if top1_score <= 0 or top2_score <= 0:
        return {'needed': False}

    if _OVERCOME.get(top1) == top2:
        attacker, defender = top1, top2
    elif _OVERCOME.get(top2) == top1:
        attacker, defender = top2, top1
    else:
        return {'needed': False}

    # 둘 다 상당한 비중을 차지하고, 세력 차이가 크지 않을 때만 통관이 의미있다
    if (top1_score / total * 100) < 18 or (top2_score / total * 100) < 18:
        return {'needed': False}
    if min(top1_score, top2_score) / max(top1_score, top2_score) < 0.55:
        return {'needed': False}

    bridge = _GENERATION[attacker]
    return {
        'needed': True, 'element': bridge,
        'desc': f'{attacker}과(와) {defender}이(가) 원국 내에서 강하게 상극하며 맞서고 있습니다({attacker}剋{defender}). '
                f'{bridge} 기운이 둘 사이를 이어주면({attacker}生{bridge}生{defender}) 충돌이 순환으로 바뀌어 도움이 됩니다.'
    }


# ============================================================================
# [6] 인생영역별 분석 - 배우자운 / 재운 / 직업운
# ============================================================================
def analyze_marriage_luck(month_deity, adj_scores, sex):
    """
    배우자운 분석
    - 남성 사주: 아내를 나타내는 재성(정재/편재) 기준
    - 여성 사주: 남편을 나타내는 관성(정관/편관) 기준
    """
    if sex == "남성":
        if '정재' in month_deity:
            return {'type': '정재배우자', 'strength': '안정적',
                    'desc': '정재로 나타나는 배우자운으로, 아내(배우자)를 통해 안정적인 결혼 생활을 기대할 수 있습니다.',
                    'partner_desc': '현실적이고 알뜰하며 신용 있는 배우자 예상'}
        elif '편재' in month_deity:
            return {'type': '편재배우자', 'strength': '활동적',
                    'desc': '편재로 나타나는 배우자운으로, 자유롭고 활동적인 성향의 배우자와 인연이 있습니다.',
                    'partner_desc': '사교적이고 수완이 좋은 배우자 예상, 다만 이성 관계에 신중함이 필요'}
        else:
            return {'type': '미정', 'strength': '약함',
                    'desc': '월주에 재성이 뚜렷하지 않아 배우자 기운이 명확하지 않습니다.',
                    'partner_desc': '결혼 시기가 다소 늦어지거나 인연을 신중히 살펴야 할 수 있습니다.'}
    else:
        if '정관' in month_deity:
            return {'type': '정관배우자', 'strength': '안정적' if adj_scores.get('金', 0) > 15 else '약함',
                    'desc': '정관으로 나타나는 안정적인 배우자운입니다.',
                    'partner_desc': '자존심 있고 위엄 있는 배우자 예상'}
        elif '편관' in month_deity:
            return {'type': '편관배우자', 'strength': '강함',
                    'desc': '편관으로 나타나는 지배적인 배우자운입니다.',
                    'partner_desc': '지배적이고 강한 에너지의 배우자 예상, 관계의 주도권 조율이 필요'}
        else:
            return {'type': '미정', 'strength': '약함',
                    'desc': '월주에 관성이 뚜렷하지 않아 배우자 기운이 명확하지 않습니다.',
                    'partner_desc': '결혼 시기가 늦어질 수 있습니다.'}


_WEALTH_ELEM_MAP = {'木': '土', '火': '金', '土': '水', '金': '木', '水': '火'}


def analyze_wealth_luck(day_stem, adj_scores, strength_label=None):
    """재운 분석 - 금전운 및 재물 기운 평가 (신강/신약 여부를 함께 반영)"""
    stem_elem_map = {'甲': '木', '乙': '木', '丙': '火', '丁': '火', '戊': '土',
                      '己': '土', '庚': '金', '辛': '金', '壬': '水', '癸': '水'}
    daymaster_elem = stem_elem_map.get(day_stem, '')
    wealth_elem = _WEALTH_ELEM_MAP.get(daymaster_elem, '')
    wealth_score = adj_scores.get(wealth_elem, 0)

    is_weak = strength_label is not None and '신약' in strength_label

    if is_weak and wealth_score > 25:
        return {'score': wealth_score, 'level': '재다신약(財多身弱) 주의',
                'desc': f'{wealth_elem} 재성은 매우 강하지만 일간이 약해 재물을 감당하기 벅찬 상태입니다. 과욕보다는 안정적인 수입 구조와 동업·협력이 유리합니다.'}
    elif wealth_score > 20:
        return {'score': wealth_score, 'level': '우수',
                'desc': f'{wealth_elem} 재성이 강해서 금전 운세가 우수합니다. 적극적인 재물 추구가 길합니다.'}
    elif wealth_score > 10:
        return {'score': wealth_score, 'level': '보통',
                'desc': f'{wealth_elem} 재성이 중간이므로 꾸준한 노력이 필요합니다.'}
    else:
        return {'score': wealth_score, 'level': '약함',
                'desc': f'{wealth_elem} 재성이 약해서 협력과 인맥이 중요합니다.'}


_JOB_MAP = {
    '木': ['공무원', '교사', '판사', '변호사', '교수', '신문·출판'],
    '火': ['의사', '배우', '화학자', '전기·전자공학자', '에너지산업'],
    '土': ['건설', '부동산', '금융', '농업', '은행'],
    '金': ['광산·금속', '군인', '경찰', '정부기관', '엔지니어'],
    '水': ['무역', '운송', '해운', '유통', '마케팅', '심리·상담']
}


def analyze_career_luck(day_stem, adj_scores):
    """직업운 분석 - 직업 적성 및 진로 가이드"""
    stem_elem_map = {'甲': '木', '乙': '木', '丙': '火', '丁': '火', '戊': '土',
                      '己': '土', '庚': '金', '辛': '金', '壬': '水', '癸': '水'}
    daymaster_elem = stem_elem_map.get(day_stem, '')

    suitable_jobs = _JOB_MAP.get(daymaster_elem, [])
    score = adj_scores.get(daymaster_elem, 0)
    strength = '강함' if score > 15 else ('중간' if score > 8 else '약함')

    return {
        'elem': daymaster_elem,
        'suitable_jobs': suitable_jobs,
        'strength': strength,
        'desc': f'{daymaster_elem} 기운으로 위 분야에서의 성공이 예상됩니다.'
    }


# ============================================================================
# [7] 주요 신살(神殺) 확충 - 도화살 / 양인살 / 괴강살 / 천을귀인 / 문창귀인 / 원진살
# ============================================================================
_DOHWA_MAP = {  # 기준 지지(보통 일지)의 삼합 그룹별 도화(桃花) 지지
    frozenset(['申', '子', '辰']): '酉',
    frozenset(['亥', '卯', '未']): '子',
    frozenset(['寅', '午', '戌']): '卯',
    frozenset(['巳', '酉', '丑']): '午',
}


def check_dohwasal(base_branch, all_branches):
    """도화살(桃花殺, 함지살) - 기준 지지(보통 일지)의 삼합 그룹에서 도화 지지를 찾고,
    원국에 실제로 그 지지가 있는지 확인한다."""
    for group, dohwa in _DOHWA_MAP.items():
        if base_branch in group:
            if dohwa in all_branches:
                return {'exists': True, 'branch': dohwa,
                        'desc': f'{base_branch} 기준 도화 지지는 {dohwa}이며, 원국에 실제로 존재합니다. 이성에게 매력적이고 인기가 많은 기운이나 이성 관계에 신중함이 필요합니다.'}
            return {'exists': False, 'branch': dohwa,
                    'desc': f'{base_branch} 기준 도화 지지는 {dohwa}이나, 원국에는 없습니다.'}
    return {'exists': False, 'branch': None, 'desc': '판별 불가'}


_YANGIN_STEMS = {'甲', '丙', '戊', '庚', '壬'}  # 양간(陽干)만 해당


def check_yanginsal(day_master, unseong_map, all_branches):
    """양인살(陽刃殺) - 양간 일간이 자신의 12운성 제왕(帝旺) 지지를 원국에 가졌는지 확인한다."""
    if day_master not in _YANGIN_STEMS:
        return {'exists': False, 'branch': None, 'desc': '양인살은 양간(甲丙戊庚壬) 일간에만 해당합니다.'}

    yangin_branch = next((b for b, u in unseong_map[day_master].items() if u == '제왕'), None)
    if yangin_branch and yangin_branch in all_branches:
        return {'exists': True, 'branch': yangin_branch,
                'desc': f'일간의 양인 지지 {yangin_branch}이(가) 원국에 있습니다. 강한 추진력과 결단력을 지녔으나 극단적 선택이나 다툼에 주의가 필요합니다.'}
    return {'exists': False, 'branch': yangin_branch,
            'desc': f'일간의 양인 지지({yangin_branch})가 원국에 없어 양인살은 해당하지 않습니다.'}


_GOEGANG_PILLARS = {'庚辰', '庚戌', '壬辰', '戊戌'}


def check_goegangsal(day_ganji):
    """괴강살(魁罡殺) - 일주가 4대 괴강(庚辰·庚戌·壬辰·戊戌) 중 하나인지 확인한다."""
    if day_ganji in _GOEGANG_PILLARS:
        return {'exists': True,
                'desc': f'일주가 괴강({day_ganji})에 해당합니다. 총명하고 결단력이 뛰어나며 극단적인 카리스마를 지녔으나, 인생의 부침이 크고 고집이 셀 수 있습니다.'}
    return {'exists': False, 'desc': '일주가 괴강에 해당하지 않습니다.'}


_CHEONEUL_MAP = {
    '甲': ('丑', '未'), '戊': ('丑', '未'), '庚': ('丑', '未'),
    '乙': ('子', '申'), '己': ('子', '申'),
    '丙': ('亥', '酉'), '丁': ('亥', '酉'),
    '壬': ('卯', '巳'), '癸': ('卯', '巳'),
    '辛': ('午', '寅'),
}


def check_cheoneul_gwiin(day_master, all_branches):
    """천을귀인(天乙貴人) - 일간 기준 하늘이 돕는 귀인 지지가 원국에 있는지 확인한다."""
    targets = _CHEONEUL_MAP.get(day_master, ())
    hits = [b for b in targets if b in all_branches]
    if hits:
        return {'exists': True, 'branches': hits,
                'desc': f'천을귀인({"·".join(targets)}) 중 {"·".join(hits)}이(가) 원국에 있습니다. 어려울 때 귀인의 도움을 받는 대표적인 길신입니다.'}
    return {'exists': False, 'branches': [], 'desc': f'천을귀인({"·".join(targets)})이 원국에 없습니다.'}


_MUNCHANG_MAP = {
    '甲': '巳', '乙': '午', '丙': '申', '丁': '酉', '戊': '申',
    '己': '酉', '庚': '亥', '辛': '子', '壬': '寅', '癸': '卯',
}


def check_munchang_gwiin(day_master, all_branches):
    """문창귀인(文昌貴人) - 일간 기준 학문·총명함을 나타내는 지지가 원국에 있는지 확인한다."""
    target = _MUNCHANG_MAP.get(day_master)
    if target and target in all_branches:
        return {'exists': True, 'branch': target,
                'desc': f'문창귀인({target})이 원국에 있습니다. 총명하고 학문·문서 관련 운이 좋습니다.'}
    return {'exists': False, 'branch': target, 'desc': f'문창귀인({target})이 원국에 없습니다.'}


_WONJIN_PAIRS = {
    frozenset(['子', '未']): '자미원진', frozenset(['丑', '午']): '축오원진',
    frozenset(['寅', '酉']): '인유원진', frozenset(['卯', '申']): '묘신원진',
    frozenset(['辰', '亥']): '진해원진', frozenset(['巳', '戌']): '사술원진',
}


def check_wonjinsal(all_branches):
    """원진살(怨嗔殺) - 원국 지지들 사이에 원진 관계가 있는지 확인한다."""
    found = []
    branch_set = set(all_branches)
    for pair, name in _WONJIN_PAIRS.items():
        if pair.issubset(branch_set):
            b1, b2 = tuple(pair)
            found.append({
                'pair': (b1, b2), 'name': name,
                'desc': f'{b1}·{b2}이(가) 원진 관계로 원국에 함께 있어, 서로 이유 없이 꺼려지거나 애증이 교차하는 기운이 있습니다.'
            })
    return found
