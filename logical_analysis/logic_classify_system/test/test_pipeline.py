"""
Turn 단위 분석 파이프라인 테스트

분석 프로세스가 정상적으로 작동하는지 테스트
"""

import sys
import os
from pathlib import Path

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from logical_analysis.logic_classify_system.pipeline.main_pipeline import MainPipeline
from logical_analysis.logic_classify_system.preprocessing.text_splitter import TurnSplitter, Turn


def print_separator(title: str):
    """구분선 출력"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def print_turn_result(turn_result, turn_index: int):
    """Turn 결과 출력"""
    print(f"Turn {turn_index} 분석 결과:")
    print(f"  [손님 발화] {turn_result.customer_result.text}")
    print(f"  [Label] {turn_result.customer_result.classification_result.label} ({turn_result.customer_result.classification_result.label_type})")
    print(f"  [신뢰도] {turn_result.customer_result.classification_result.confidence:.2f}")
    
    # 특징점 점수 출력
    print(f"\n  [특징점 점수]")
    feature_scores = turn_result.customer_result.feature_scores
    for key, value in feature_scores.items():
        if value > 0:
            print(f"    - {key}: {value:.2f}")
    
    # 추출된 특징점 출력
    extracted = turn_result.customer_result.extracted_features
    if extracted:
        print(f"\n  [추출된 특징점]")
        for key, value in extracted.items():
            if value:  # 비어있지 않은 경우만 출력
                print(f"    - {key}: {value}")
    
    # 상담원 발화 분석 결과
    if turn_result.agent_result:
        print(f"\n  [상담원 발화] {turn_result.agent_result.text}")
        print(f"  [매뉴얼 준수도] {turn_result.agent_result.manual_compliance_score:.2f}")
        agent_scores = turn_result.agent_result.feature_scores
        print(f"  [상담원 특징점 점수]")
        for key, value in agent_scores.items():
            if value > 0:
                print(f"    - {key}: {value:.2f}")
    
    # Turn 종합 점수
    print(f"\n  [Turn 종합 점수]")
    for key, value in turn_result.turn_scores.items():
        print(f"    - {key}: {value:.2f}")
    
    print()


def test_scenario_1_normal_inquiry():
    """시나리오 1: 정상적인 문의"""
    print_separator("시나리오 1: 정상적인 문의 (Normal Label)")
    
    pipeline = MainPipeline()
    
    stt_data = {
        "session_id": "test_001",
        "segments": [
            {"speaker": "customer", "text": "안녕하세요. 상품 문의가 있어서 전화드렸습니다."},
            {"speaker": "agent", "text": "네 고객님, 무엇을 도와드릴까요?"},
            {"speaker": "customer", "text": "이 상품의 배송 일정을 알려주세요."},
            {"speaker": "agent", "text": "네 배송은 보통 2-3일 소요됩니다."}
        ]
    }
    
    result = pipeline.process(stt_data)
    
    print(f"세션 ID: {result.session_id}")
    print(f"처리된 Turn 수: {len(result.turn_results)}\n")
    
    for turn_result in result.turn_results:
        print_turn_result(turn_result, turn_result.turn_index)
    
    return result


def test_scenario_2_profanity():
    """시나리오 2: 욕설 포함"""
    print_separator("시나리오 2: 욕설 포함 (Special Label - PROFANITY)")
    
    pipeline = MainPipeline()
    
    stt_data = {
        "session_id": "test_002",
        "segments": [
            {"speaker": "customer", "text": "시발놈아! 이게 뭐야?"},
            {"speaker": "agent", "text": "죄송합니다. 어떤 불편이 있으셨나요?"}
        ]
    }
    
    result = pipeline.process(stt_data)
    
    print(f"세션 ID: {result.session_id}")
    print(f"처리된 Turn 수: {len(result.turn_results)}\n")
    
    for turn_result in result.turn_results:
        print_turn_result(turn_result, turn_result.turn_index)
    
    return result


def test_scenario_3_unreasonable_demand():
    """시나리오 3: 무리한 요구"""
    print_separator("시나리오 3: 무리한 요구 (Special Label - UNREASONABLE_DEMAND)")
    
    pipeline = MainPipeline()
    
    stt_data = {
        "session_id": "test_003",
        "segments": [
            {"speaker": "customer", "text": "지금 당장 환불해줘! FBI를 불러줘!"},
            {"speaker": "agent", "text": "죄송합니다. 환불 절차를 안내해드리겠습니다."}
        ]
    }
    
    result = pipeline.process(stt_data)
    
    print(f"세션 ID: {result.session_id}")
    print(f"처리된 Turn 수: {len(result.turn_results)}\n")
    
    for turn_result in result.turn_results:
        print_turn_result(turn_result, turn_result.turn_index)
    
    return result


def test_scenario_4_complaint():
    """시나리오 4: 불만/민원"""
    print_separator("시나리오 4: 불만/민원 (Normal Label - COMPLAINT)")
    
    pipeline = MainPipeline()
    
    stt_data = {
        "session_id": "test_004",
        "segments": [
            {"speaker": "customer", "text": "서비스가 너무 불만족스럽습니다. 보상해주세요."},
            {"speaker": "agent", "text": "불편을 드려 죄송합니다. 구체적으로 어떤 문제가 있었는지 말씀해주시겠어요?"}
        ]
    }
    
    result = pipeline.process(stt_data)
    
    print(f"세션 ID: {result.session_id}")
    print(f"처리된 Turn 수: {len(result.turn_results)}\n")
    
    for turn_result in result.turn_results:
        print_turn_result(turn_result, turn_result.turn_index)
    
    return result


def test_scenario_5_repetition_keyword():
    """시나리오 5: 반복 표현 키워드"""
    print_separator("시나리오 5: 반복 표현 키워드 감지")
    
    pipeline = MainPipeline()
    
    stt_data = {
        "session_id": "test_005",
        "segments": [
            {"speaker": "customer", "text": "또 같은 말씀을 반복해서 말씀드리는데 환불해주세요."},
            {"speaker": "agent", "text": "네 이해했습니다. 환불 절차를 안내해드리겠습니다."}
        ]
    }
    
    result = pipeline.process(stt_data)
    
    print(f"세션 ID: {result.session_id}")
    print(f"처리된 Turn 수: {len(result.turn_results)}\n")
    
    for turn_result in result.turn_results:
        print_turn_result(turn_result, turn_result.turn_index)
    
    return result


def test_scenario_6_single_turn():
    """시나리오 6: 단일 Turn 처리"""
    print_separator("시나리오 6: 단일 Turn 처리")
    
    pipeline = MainPipeline()
    turn_splitter = TurnSplitter()
    
    # 간단한 텍스트로 Turn 분할
    text = "고객: 안녕하세요\n상담사: 네 안녕하세요\n고객: 환불해주세요"
    turns = turn_splitter.split_simple_text(text)
    
    print(f"분할된 Turn 수: {len(turns)}\n")
    
    for turn in turns:
        turn_result = pipeline.process_turn(turn, "test_006")
        print_turn_result(turn_result, turn.turn_index)


def test_scenario_7_threat():
    """시나리오 7: 위협 표현"""
    print_separator("시나리오 7: 위협 표현 (Special Label - VIOLENCE_THREAT)")
    
    pipeline = MainPipeline()
    
    stt_data = {
        "session_id": "test_007",
        "segments": [
            {"speaker": "customer", "text": "죽여버릴거야! 찾아가서 끝장낼거야!"},
            {"speaker": "agent", "text": "죄송합니다. 문제를 해결하도록 도와드리겠습니다."}
        ]
    }
    
    result = pipeline.process(stt_data)
    
    print(f"세션 ID: {result.session_id}")
    print(f"처리된 Turn 수: {len(result.turn_results)}\n")
    
    for turn_result in result.turn_results:
        print_turn_result(turn_result, turn_result.turn_index)
    
    return result


def run_all_tests():
    """모든 테스트 실행"""
    print_separator("Turn 단위 분석 파이프라인 전체 테스트 시작")
    
    try:
        test_scenario_1_normal_inquiry()
        test_scenario_2_profanity()
        test_scenario_3_unreasonable_demand()
        test_scenario_4_complaint()
        test_scenario_5_repetition_keyword()
        test_scenario_6_single_turn()
        test_scenario_7_threat()
        
        print_separator("✅ 모든 테스트 완료")
        print("모든 테스트가 성공적으로 완료되었습니다.")
        
    except Exception as e:
        print_separator("❌ 테스트 실패")
        print(f"오류 발생: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_all_tests()


