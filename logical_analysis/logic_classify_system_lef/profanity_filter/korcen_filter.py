"""
Korcen 기반 욕설 필터 (경량화 버전)

전화 상담 맥락에 최적화된 Korcen 필터 구현 (HEAD 기반)
단어 단위 패턴 매칭을 통한 빠른 욕설 감지 (logic 기능 통합)
- 레벨-카테고리 매핑
- Baseline 규칙과 통합 (위협 표현 감지)
"""

import re
from typing import Tuple, Optional, Dict, List
import logging

from .baseline_rules import ProfanityBaselineRules
from ..data.data_structures import ProfanityResult

logger = logging.getLogger(__name__)

# ============================================================================
# 텍스트 정규화 맵 (핵심만 추출)
# ============================================================================

SINGLE_CHAR_NORMALIZATION_MAP = {
    # s 변형
    '𝗌': 's', '𝘴': 's', '𝙨': 's', '𝚜': 's', '𝐬': 's', '𝑠': 's', '𝒔': 's', '𝓈': 's', 
    '𝓼': 's', '𝔰': 's', '𝖘': 's', '𝕤': 's', 'ｓ': 's', 'ş': 's', '$': 's',
    # e 변형
    '𝖾': 'e', '𝘦': 'e', '𝙚': 'e', '𝚎': 'e', '𝐞': 'e', '𝑒': 'e', '𝒆': 'e', 'ℯ': 'e',
    'ｅ': 'e', '3': 'e', '€': 'e',
    # x 변형
    '𝗑': 'x', '𝘹': 'x', '𝙭': 'x', '𝚡': 'x', '𝐱': 'x', '𝑥': 'x', '𝒙': 'x', '𝓍': 'x',
    'ｘ': 'x', '*': 'x', '✕': 'x', '✖': 'x', '❌': 'x',
    # 한글 자모 변형
    'ㅗ': 'ㅗ', '┻': 'ㅗ', '┴': 'ㅗ', '⊥': 'ㅗ', '†': 'ㅗ',
    '^': 'ㅅ', '人': 'ㅅ', '∧': 'ㅅ', 'Λ': 'ㅅ',
    '甘': 'ㅂ', '廿': 'ㅂ', '田': 'ㅂ', '口': 'ㅂ', '日': 'ㅂ', '目': 'ㅂ',
    '己': 'ㄹ', '乙': 'ㄹ', '已': 'ㄹ', '巳': 'ㄹ',
    '卜': 'ㅏ', 'r': 'ㅏ', 'F': 'ㅏ', '|': 'ㅏ', '/': 'ㅏ',
    'l': 'ㅣ', '1': 'ㅣ', 'I': 'ㅣ', '!': 'ㅣ',
    'H': 'ㅐ', 'ㅖ': 'ㅐ', 'ㅒ': 'ㅐ',
    '0': 'ㅇ', 'O': 'ㅇ', 'o': 'ㅇ', '◯': 'ㅇ', '⭕': 'ㅇ', '○': 'ㅇ',
    # 이모지 변형
    '🐦': '새', '🐔': '새', '🦅': '새',
    '🐕': '개', '🐶': '개', '🐺': '개',
}

MULTI_CHAR_REPLACEMENTS = {
    '_ㅣ_': 'ㅗ', '_/_': 'ㅗ', '_|\_': 'ㅗ',
    '／＼': 'ㅅ', '/＼': 'ㅅ',
    '77': 'ㄲ',
    'ㅇl=스': '섹스',
    'ㅇㅣ-ㅣ': '애',
    'lㅣ': '니',
    'ㅁㅣ': '미',
}

NORMALIZATION_TABLE = str.maketrans(SINGLE_CHAR_NORMALIZATION_MAP)
URL_REGEX = re.compile(r'https?:\/\/\S+|www\.\S+')
MULTI_CHAR_REPLACEMENT_REGEX = re.compile(
    '|'.join(map(re.escape, sorted(MULTI_CHAR_REPLACEMENTS.keys(), key=len, reverse=True)))
)

# ============================================================================
# False Positive 패턴 (전화 상담 맥락에 맞게 축소)
# ============================================================================

FALSE_POSITIVE_PATTERNS_GENERAL = [
    'ㅗ먹어', '오ㅗ', '해ㅗ', '호ㅗ', '로ㅗ', '옹ㅗ', '롤ㅗ', '요ㅗ', '우ㅗ', '하ㅗ',
    '8분', '8시', '8시발',
    '발닦', '다시방', '시발음', '시발택시', '시발자동차', '정치발', '시발점', '시발유',
    '시발역', '아저씨바', '아저씨발', '오리발', '발끝', '다시바', '다시팔',
    '발사', '무시발언', '일시불', '우리', '혹시', '아저씨', '바로', '저거시',
    '피시방', '피씨방', '방장', '엠씨방', '빨리', '벌금', '시방향', '불법', '발표', '방송', '역시',
    '있지', '없지', '하지', '알았지', '몰랐지', '근데',
    '새로', '세끼먹', '고양이새끼', '호랑이새끼', '키보드', '새끼손',
    '0개', '1개', '2개', '3개', '4개', '5개', '6개', '7개', '8개', '9개',
    '1년', '2년', '3년', '4년', '5년', '6년', '7년', '8년', '9년',
    '재밌게놈', '년생', '무지개색', '떠돌이개', '에게', '넘는', '소개', '생긴게', '날개같다',
]

FALSE_POSITIVE_PATTERNS_MINOR = [
    '거미', '친구', '개미', '이미친', '미친증', '동그라미',
    '뒤져봐야', '뒤질뻔', '뒤져보다', '뒤져보는', '뒤져보고', '뒤져간다', '뒤져서',
]

FALSE_POSITIVE_PATTERNS_SEXUAL = [
    '보지도못', '보지도않', '인가보지', '면접보지', '영화보지', '애니보지', '만화보지', '사진보지',
    '보지마', '보지말', '안보지만', '정보', '지팡이', '행보', '바보지', '물어보지',
    '언제자지', '잠자지', '자지말자고', '지급', '남자지', '여자지', '감자지',
    '개발자', '관리자', '약탈자', '혼자', '자지원', '사용자', '경력자', '지식', '자지마',
    '야스오', '크시야', '카구야', '스파이', '말이야', '스티브', '스쿼드',
]

FALSE_POSITIVE_PATTERNS_BELITTLE = [
    '려운지', '무서운지', '라운지', '운지법', '싸운지', '운지버섯', '운지린다', '깔보다',
    '1년', '2년', '3년', '4년', '5년', '6년', '7년', '8년', '9년', '0년',
]

FALSE_POSITIVE_PATTERNS_RACE = ['흑형님']
FALSE_POSITIVE_PATTERNS_PARENT = ['ㄴㄴ', '미국', '엄창못']
FALSE_POSITIVE_PATTERNS_POLITICS = [
    '카카오톡', '카톡', '카페', '하다가', '먹다가', '카와이', '카츠', '카레',
    '니가', '내가', '너가', '우리가', '너희가', '카카오', '카드',
]

# False Positive 정규식 컴파일
FP_REGEX_GENERAL = re.compile('|'.join(map(re.escape, FALSE_POSITIVE_PATTERNS_GENERAL)))
FP_REGEX_MINOR = re.compile('|'.join(map(re.escape, FALSE_POSITIVE_PATTERNS_MINOR)))
FP_REGEX_SEXUAL = re.compile('|'.join(map(re.escape, FALSE_POSITIVE_PATTERNS_SEXUAL)))
FP_REGEX_BELITTLE = re.compile('|'.join(map(re.escape, FALSE_POSITIVE_PATTERNS_BELITTLE)))
FP_REGEX_RACE = re.compile('|'.join(map(re.escape, FALSE_POSITIVE_PATTERNS_RACE)))
FP_REGEX_PARENT = re.compile('|'.join(map(re.escape, FALSE_POSITIVE_PATTERNS_PARENT)))
FP_REGEX_POLITICS = re.compile('|'.join(map(re.escape, FALSE_POSITIVE_PATTERNS_POLITICS)))

# ============================================================================
# 욕설 패턴 (핵심만 추출)
# ============================================================================

GENERAL_PROFANITY_PATTERNS = [
    'ㅗ', '씨8', '18아', '18놈', 'tㅂ', 't발', 'ㅆㅍ', 'sibal', 'sival', 'sibar', 'sibak', 'sipal',
    'tlbal', 'tlval', 'tlbar', 'tlbak', 'tlpal', 'tlqk', '시발', '시val', '시bar',
    '시bak', '시pal', '시qk', 'si바', 'si발', 'si불', 'si빨', 'si팔', 'tl바', 'tl발', 'tl불', 'tl빨', 'tl팔',
    'siba', 'tlba', 'siva', 'tlva', 'tlqkf', '10발놈', '10발년', 'tlqkd', 'si8', '10r놈', '시8', '십8',
    's1bal', 'sib알', '씨x', 'siㅂ', '丨발', '丨벌', '丨바', 'ㅅ1', '시ㅣ', '씨ㅣ', '8시발',
    'ㅆ발', 'ㅅ발', 'ㅅㅂ', 'ㅆㅂ', 'ㅆ바', 'ㅅ바', '시ㅂㅏ', 'ㅅㅂㅏ', '시ㅏㄹ', '씨ㅏㄹ',
    'ㅅ불', 'ㅆ불', 'ㅅ쁠', 'ㅆ뿔', 'ㅆㅣ발', 'ㅅㅟ발', 'ㅅㅣㅂㅏ', 'ㅣ바알', 'ㅅ벌',
    'ㅆ삐라', '씨ㅃ', '^^/발', '시봘', '씨봘', '씨바', '시바', '샤발', '씌발', '씹발', '시벌',
    '시팔', '싯팔', '씨빨', '씨랼', '씨파', '띠발', '띡발', '띸발', '싸발', '십발', '슈발',
    '야발', '씨불', '씨랄', '쉬발', '쓰발', '쓔발', '쌰발', '쒸발', '씨팔',
    'wlfkf', 'g랄', 'g럴', 'g롤', 'g뢀', 'giral', 'zi랄', 'ji랄', 'ㅈㄹ', '지ㄹ', 'ㅈ랄', 'ㅈ라',
    '지랄', '찌랄', '지럴', '지롤', '랄지', '쥐랄', '쮜랄', '지뢀', '띄랄',
    'ㅄ', 'ㅂㅅ', '병ㅅ', 'ㅂ신', 'ㅕㅇ신', 'ㅂㅇ신', '뷰신', '병신', '병딱', '벼신', '붱신',
    '뼝신', '뿽신', '삥신', '병시니', '병형신', '뵹신', '병긴', '비응신',
    '염병', '엠병', '옘병', '얨병', '옘뼝',
    '꺼져',
    '엿같', '엿가튼', '엿먹어', '뭣같은',
    'rotorl', 'rotprl', 'sib새', 'ah끼', 'sㅐ끼', 'x끼',
    'ㅅㄲ', 'ㅅ끼', 'ㅆ끼', '색ㄲㅣ', 'ㅆㅐㄲㅑ', 'ㅆㅐㄲㅣ', '새끼', '쉐리', '쌔끼', '썌끼',
    '쎼끼', '쌬끼', '샠끼', '세끼', '샊', '쌖', '섺', '쎆', '십새', '새키', '씹색', '새까',
    '새꺄', '샛끼', '새뀌', '새끠', '새캬', '색꺄', '색끼', '섹히', '셁기', '셁끼', '셐기',
    '셰끼', '셰리', '쉐꺄', '십색꺄', '십떼끼', '십데꺄', '십때끼', '십새꺄', '십새캬', '쉑히',
    '씹새기', '고아새기', '샠기', '애새기', '이새기', '느그새기', '장애새기',
    'w같은', 'ㅈ같', 'ㅈ망', 'ㅈ까', 'ㅈ경', 'ㅈ가튼', '좆', '촟', '조까', '좈', '쫒', '졷',
    '좃', '줮', '좋같', '좃같', '좃물', '좃밥', '줫', '좋밥', '좋물', '좇',
    '썅', '씨앙', '씨양', '샤앙', '쌰앙',
    '뻑유', '뻐킹', '뻐큐', '빡큐', '뿩큐', '뻑큐', '빡유', '뻒큐',
    '닥쳐', '닭쳐', '닥치라', '아가리해',
    'dog새', '개ㅐ색',
    '개같', '개가튼', '개쉑', '개스키', '개세끼', '개색히', '개가뇬', '개새기', '개쌔기', '개쌔끼',
    '개소리', '개년', '개드립', '개돼지', '개씹창', '개간나', '개스끼', '개섹기',
    '개자식', '개때꺄', '개때끼', '개발남아', '개샛끼', '개가든', '개가뜬', '개가턴', '개가툰',
    '개갇은', '개갈보', '개걸레', '개너마', '개너므', '개넌', '개넘', '개녀나',
    '개노마', '개노무새끼', '개논', '개놈', '개뇨나', '개뇬', '개뇸', '개뇽', '개눔', '개느마',
    '개늠', '개랙기', '개련', '개발남아', '개발뇬', '개색', '개색기',
    '개색끼', '개샛키', '개샛킹', '개샛히', '개샜끼', '개생키', '개샠', '개샤끼', '개샤킥',
    '개지랄', '개지럴', '개창년', '개허러', '개허벌년', '개호러', '개호로', '개후랄', '개후레',
    '개후로', '개후장', '게가튼', '게같은', '게년', '게놈', '게새끼', '게색', '게색기', '게색끼',
]

MINOR_PROFANITY_PATTERNS = [
    'ㅁㅊ', 'ㅁ친', 'ㅁ쳤', 'aㅣ친', 'me친', '미ㅊ', 'di친',
    '미친놈', '미친새끼',
    '꼽냐', '꼽니', '꼽나',
    '뒤져', '뒈져', '뒈진', '뒈질', '디져라', '디진다', '디질래', '뒤질',
]

SEXUAL_PROFANITY_PATTERNS = [
    'ⓑⓞⓩⓘ', 'bozi', '보ㅈㅣ', '보지', '버지물', '버짓물', '보짓', '개보즤', '개보지',
    'ja지', 'ㅈㅈ빨', '자ㅈ', 'ㅈ지빨', '자지', '자짓', '잦이', '쟈지',
    'sex', 's스', 'x스', 'se스', 'ㅅㅔㅅㄱ', '이=스', '섹ㅅ', '세ㄱㅅ', '섹스', '섻', '쉑스', '섿스',
    '꼬3', '꼬툭튀', '꼬톡튀', '불알', '부랄', '뽕알', '뿅알', '뿌랄', '뿔알', '개부달', '개부랄',
    '오나홍', '오나홀', 'ㅇㄴ홀', '텐가', '바이브레이터', '씹하다', '매춘부', '성노예',
    '딸딸이', '질싸', '자위남', '자위녀', '폰섹', '포르노', '폰세엑', '폰쉑', '폰쎅',
    'g스팟', '지스팟', '크리토리스', '클리토리스', '페니스', '애널', '젖까', '젖가튼',
    'ja위', '자위', '고자새끼', '고츄', '꺼추', '꼬추',
]

BELITTLE_PROFANITY_PATTERNS = [
    '10련', '따까리', '장애년', '찐따년', '싸가지', '창년', '썅년', '버러지', '고아년', '개간년',
    '창녀', '머저리', '씹쓰래기', '씹쓰레기', '씹장생', '씹자식', '운지', '급식충', '틀딱충',
    '한남충', '정신병자', '중생아', '돌팔이', '김치녀', '폰팔이', '틀딱년', '같은년', '개돼중',
    '빡대가리', '더러운년', '돌아이', '또라이', '장애려', '샹놈', '김치남', '김치녀',
]

RACE_PROFANITY_PATTERNS = [
    '깜둥이', '흑형', '조센진', '짱개', '짱깨', '짱께', '짱게', '쪽바리', '쪽파리', '빨갱이',
    '니그로', '코쟁이', '칭총', '칭챙총', '섬숭이', '왜놈', '짱꼴라', '섬짱깨',
]

PARENT_PROFANITY_PATTERNS = [
    'ㄴ1ㄱ', 'ㄴ1ㅁ', '느금ㅁ', 'ㄴㄱ마', 'ㄴㄱ빠', 'ㄴ금빠', 'ㅇH미', 'ㄴ1에미', '늬애미',
    'ㄴㄱㅁ', 'ㄴ금마', '늬금마',
    '느금마', '느그엄마', '늑엄마', '늑금마', '느그애미', '넉엄마', '느그부모', '느그애비',
    '느금빠', '느그메', '느그빠', '니미씨', '니미씹',
    '느그마', '니엄마', '엄창', '엠창', '니미럴', '누굼마', '느금',
]

POLITICS_PROFANITY_PATTERNS = [
    "노시개", "노알라", "뇌사모", "뇌물현", "응디시티",
    "귀걸이아빠", "달창", "대깨문", "문재앙", "문죄앙", "문죄인", "문크예거", "훠훠훠", "문빠",
    "근혜어", "길라임", "나대블츠", "닭근혜", "댓통령", "레이디가카", "바쁜벌꿀",
    "가카", "이명박근혜",
]

SPECIAL_PROFANITY_PATTERNS = ["🖕🏻", "👌🏻👈🏻", "👉🏻👌🏻", "🤏🏻", "🖕", "🖕🏼", "🖕🏽", "🖕🏾", "🖕🏿"]

# 정규식 컴파일
P_REGEX_GENERAL = re.compile('|'.join(map(re.escape, GENERAL_PROFANITY_PATTERNS)))
P_REGEX_MINOR = re.compile('|'.join(map(re.escape, MINOR_PROFANITY_PATTERNS)))
P_REGEX_SEXUAL = re.compile('|'.join(map(re.escape, SEXUAL_PROFANITY_PATTERNS)))
P_REGEX_BELITTLE = re.compile('|'.join(map(re.escape, BELITTLE_PROFANITY_PATTERNS)))
P_REGEX_RACE = re.compile('|'.join(map(re.escape, RACE_PROFANITY_PATTERNS)))
P_REGEX_PARENT = re.compile('|'.join(map(re.escape, PARENT_PROFANITY_PATTERNS)))
P_REGEX_POLITICS = re.compile('|'.join(map(re.escape, POLITICS_PROFANITY_PATTERNS)))
P_REGEX_SPECIAL = re.compile('|'.join(map(re.escape, SPECIAL_PROFANITY_PATTERNS)))

EXACT_MATCH_PROFANITY = {'tq', 'qt'}

# ============================================================================
# 유틸리티 함수
# ============================================================================

def apply_multi_char_replacements(text: str) -> str:
    """다중 문자 치환 적용"""
    def replace_match(match):
        return MULTI_CHAR_REPLACEMENTS[match.group(0)]
    return MULTI_CHAR_REPLACEMENT_REGEX.sub(replace_match, text)

def preprocess_text(text: str, level: str) -> str:
    """텍스트 전처리 (정규화)"""
    processed_text = text.lower()
    processed_text = processed_text.translate(NORMALIZATION_TABLE)
    processed_text = apply_multi_char_replacements(processed_text)
    processed_text = re.sub(r'\s+', '', processed_text)
    
    if level == 'minor':
        processed_text = re.sub('년', '놈', processed_text)
        processed_text = re.sub('련', '놈', processed_text)
    elif level == 'belittle':
        processed_text = re.sub('뇬', '련', processed_text)
        processed_text = re.sub('놈', '련', processed_text)
        processed_text = re.sub('넘', '련', processed_text)
        processed_text = re.sub('련', '년', processed_text)
    elif level == 'sexual' and '보g' in processed_text:
        processed_text = re.sub('보g', '보지', processed_text)
    
    return processed_text

def get_false_positive_regex(level: str):
    """레벨별 False Positive 정규식 반환"""
    level_map = {
        'general': FP_REGEX_GENERAL,
        'minor': FP_REGEX_MINOR,
        'sexual': FP_REGEX_SEXUAL,
        'belittle': FP_REGEX_BELITTLE,
        'race': FP_REGEX_RACE,
        'parent': FP_REGEX_PARENT,
        'politics': FP_REGEX_POLITICS,
    }
    return level_map.get(level)

def get_profanity_regex(level: str):
    """레벨별 욕설 정규식 반환"""
    level_map = {
        'general': P_REGEX_GENERAL,
        'minor': P_REGEX_MINOR,
        'sexual': P_REGEX_SEXUAL,
        'belittle': P_REGEX_BELITTLE,
        'race': P_REGEX_RACE,
        'parent': P_REGEX_PARENT,
        'politics': P_REGEX_POLITICS,
        'special': P_REGEX_SPECIAL,
    }
    return level_map.get(level)

def get_final_filter_regex_str(level: str) -> str:
    """레벨별 최종 필터 정규식 문자열 반환"""
    if level in ['general', 'sexual', 'parent', 'special', 'politics']:
        return r'[^a-z0-9ㄱ-ㅎㅏ-ㅣ가-힣ㅗ@=\-_]+'
    elif level in ['minor', 'belittle', 'race']:
        return r'[^ㄱ-ㅎㅏ-ㅣ가-힣]+'
    return r'[^a-zA-Z0-9ㄱ-ㅎㅏ-ㅣ가-힣\s]+'

def check_and_report_profanity_pattern(text: str, level: str = 'general') -> Optional[str]:
    """
    특정 레벨에서 욕설 패턴 감지
    
    Returns:
        감지된 욕설 패턴 문자열 또는 None
    """
    text_no_urls = URL_REGEX.sub('', text)
    processed_text = preprocess_text(text_no_urls, level)
    
    # False Positive 제거
    fp_regex = get_false_positive_regex(level)
    text_after_fp = fp_regex.sub('', processed_text) if fp_regex else processed_text
    
    # 최종 필터 적용
    if level == 'special':
        final_processed_text = text_after_fp
    else:
        final_filter_regex_str = get_final_filter_regex_str(level)
        final_processed_text = re.sub(final_filter_regex_str, '', text_after_fp)
    
    # 욕설 패턴 매칭
    profanity_regex = get_profanity_regex(level)
    if profanity_regex:
        match = profanity_regex.search(final_processed_text)
        if match:
            return match.group(0)
    
    # 정확한 매칭 (general 레벨만)
    if processed_text in EXACT_MATCH_PROFANITY and level == 'general':
        return processed_text
    
    return None

# ============================================================================
# 레벨-카테고리 매핑 (전화 상담 맥락)
# ============================================================================

KORCEN_TO_CATEGORY_MAP: Dict[str, str] = {
    'general': 'PROFANITY',        # 일반 욕설 → PROFANITY
    'minor': 'PROFANITY',          # 경미한 욕설 → PROFANITY
    'sexual': 'SEXUAL_HARASSMENT', # 성적 욕설 → SEXUAL_HARASSMENT
    'belittle': 'INSULT',          # 비하 표현 → INSULT
    'race': 'HATE_SPEECH',         # 인종 차별 → HATE_SPEECH
    'parent': 'INSULT',            # 부모 관련 욕설 → INSULT
    'politics': 'HATE_SPEECH',     # 정치 관련 → HATE_SPEECH
    'special': 'PROFANITY',        # 특수 문자 → PROFANITY
}

# 레벨별 신뢰도 가중치
LEVEL_CONFIDENCE_WEIGHTS: Dict[str, float] = {
    'general': 0.8,      # 높은 신뢰도
    'minor': 0.6,       # 중간 신뢰도
    'sexual': 0.9,      # 매우 높은 신뢰도 (CRITICAL)
    'belittle': 0.5,    # 중간 신뢰도
    'race': 0.7,        # 높은 신뢰도
    'parent': 0.6,      # 중간 신뢰도
    'politics': 0.5,    # 낮은 신뢰도 (맥락 의존적)
    'special': 0.7,     # 높은 신뢰도
}

# logic: Korcen 힌트 매핑
HINT_MAPPING = {
    "general": "PROFANITY_DETECTED",
    "sexual": "SEXUAL_DETECTED",
    "race": "HATE_DETECTED",
    "special": "VIOLENCE_THREAT"
}

# ============================================================================
# KorcenFilter 클래스
# ============================================================================

class KorcenFilter:
    """Korcen 기반 욕설 필터 (전화 상담 맥락 최적화) (HEAD 기반 + logic 기능 통합)"""
    
    # logic: Korcen 힌트 매핑
    HINT_MAPPING = HINT_MAPPING
    
    def __init__(self, use_korcen: bool = False):
        """
        Korcen 필터 초기화
        
        Args:
            use_korcen: Korcen 라이브러리 사용 여부 (logic: 추가)
        """
        # HEAD: Baseline 규칙 포함
        self.baseline_rules = ProfanityBaselineRules()
        
        # logic: Korcen 라이브러리 지원
        self.use_korcen = use_korcen
        self.korcen = None
        
        if use_korcen:
            try:
                import korcen
                self.korcen = korcen
                logger.info("Korcen 필터 로드 완료")
            except ImportError:
                logger.warning("Korcen 라이브러리를 찾을 수 없습니다. pip install korcen을 실행하세요.")
                self.use_korcen = False
                self.korcen = None
            except Exception as e:
                logger.warning(f"Korcen 필터 초기화 중 오류 발생: {e}")
                self.use_korcen = False
                self.korcen = None
    
    def check_profanity(self, text: str) -> Tuple[bool, Optional[str], float]:
        """
        욕설 감지 및 카테고리 매핑 (HEAD: 유지)
        
        Args:
            text: 분석할 텍스트
        
        Returns:
            (is_profanity, category, confidence)
            - is_profanity: 욕설 감지 여부
            - category: 감지된 카테고리 (PROFANITY, SEXUAL_HARASSMENT, HATE_SPEECH, INSULT)
            - confidence: 신뢰도 (0.0-1.0)
        """
        # 1. Baseline 규칙으로 위협 표현 감지 (최우선)
        is_threat, threat_category, threat_confidence = self.baseline_rules.detect_profanity(text)
        if is_threat and threat_category == "VIOLENCE_THREAT":
            return True, threat_category, threat_confidence
        
        # 2. Korcen 레벨별 감지
        detected_levels: List[Tuple[str, str]] = []  # (level, category)
        
        # 감지할 레벨 목록 (우선순위 순)
        check_levels = ['sexual', 'general', 'race', 'belittle', 'parent', 'minor', 'politics', 'special']
        
        for level in check_levels:
            detected_pattern = check_and_report_profanity_pattern(text, level)
            if detected_pattern:
                category = KORCEN_TO_CATEGORY_MAP.get(level, 'PROFANITY')
                detected_levels.append((level, category))
        
        # 3. 결과 처리
        if not detected_levels:
            return False, None, 0.0
        
        # 4. 가장 높은 우선순위 카테고리 선택
        # 우선순위: SEXUAL_HARASSMENT > VIOLENCE_THREAT > HATE_SPEECH > PROFANITY > INSULT
        priority_order = ['SEXUAL_HARASSMENT', 'VIOLENCE_THREAT', 'HATE_SPEECH', 'PROFANITY', 'INSULT']
        
        selected_category = None
        selected_level = None
        
        for priority_cat in priority_order:
            for level, category in detected_levels:
                if category == priority_cat:
                    selected_category = category
                    selected_level = level
                    break
            if selected_category:
                break
        
        # 기본값 (없으면 첫 번째)
        if not selected_category:
            selected_level, selected_category = detected_levels[0]
        
        # 5. 신뢰도 계산
        base_confidence = LEVEL_CONFIDENCE_WEIGHTS.get(selected_level, 0.6)
        # 여러 레벨에서 감지되면 신뢰도 증가
        if len(detected_levels) > 1:
            base_confidence = min(base_confidence + 0.1 * (len(detected_levels) - 1), 1.0)
        
        return True, selected_category, base_confidence
    
    def detect(self, text: str) -> Optional[ProfanityResult]:
        """
        Korcen으로 욕설 감지 (logic: 추가 메서드)
        
        Args:
            text: 분석할 텍스트
        
        Returns:
            ProfanityResult 또는 None (감지 실패 시)
        """
        # logic: Korcen 라이브러리 사용
        if self.use_korcen and self.korcen:
            try:
                # Korcen 감지 (예시 - 실제 API는 다를 수 있음)
                result = self.korcen.check(text)
                
                if result and result.get("is_profanity", False):
                    level = result.get("level", "general")
                    confidence = result.get("confidence", 0.80)
                    category = self.HINT_MAPPING.get(level, "PROFANITY_DETECTED")
                    
                    return ProfanityResult(
                        is_profanity=True,
                        category=category,
                        confidence=confidence,
                        method="korcen",
                        text=text
                    )
            except Exception as e:
                logger.error(f"Korcen 감지 실패: {e}")
                return None
        
        # HEAD: 패턴 매칭 방식으로 폴백
        is_prof, category, confidence = self.check_profanity(text)
        if is_prof:
            return ProfanityResult(
                is_profanity=True,
                category=category,
                confidence=confidence,
                method="baseline",
                text=text
            )
        
        return None
    
    def check_with_levels(self, text: str) -> Optional[Tuple[str, float]]:
        """
        레벨별 감지 (4개 레벨) (logic: 추가 메서드)
        
        Args:
            text: 분석할 텍스트
        
        Returns:
            (level, confidence) 또는 None
        """
        if self.use_korcen and self.korcen:
            try:
                result = self.korcen.check(text)
                
                if result and result.get("is_profanity", False):
                    level = result.get("level", "general")
                    confidence = result.get("confidence", 0.80)
                    return (level, confidence)
            except Exception as e:
                logger.error(f"Korcen 레벨 감지 실패: {e}")
                return None
        
        # HEAD: 패턴 매칭 방식으로 폴백
        is_prof, category, confidence = self.check_profanity(text)
        if is_prof:
            # category를 level로 변환
            level_map = {v: k for k, v in KORCEN_TO_CATEGORY_MAP.items()}
            level = level_map.get(category, "general")
            return (level, confidence)
        
        return None
