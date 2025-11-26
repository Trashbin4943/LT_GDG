"""
테스트 데이터
Phase 7 테스트에 사용할 고정 테스트 케이스
"""

TEST_CASES = {
    'normal_inquiry': {
        'text': '안녕하세요. 상품 문의가 있어서 전화드렸습니다.',
        'expected_intensity': 0.0,
        'expected_label_type': 'NORMAL',
        'expected_intensity_level': 'LOW',
        'expected_is_immoral': False
    },
    'profanity_high': {
        'text': '시발놈아! 이게 뭐야? 죽여버릴거야!',
        'expected_intensity': 2.5,
        'expected_label_type': 'SPECIAL',
        'expected_intensity_level': 'HIGH',
        'expected_is_immoral': True
    },
    'complaint_medium': {
        'text': '서비스가 너무 불만족스럽습니다. 환불해주세요.',
        'expected_intensity': 1.5,
        'expected_label_type': 'SPECIAL',
        'expected_intensity_level': 'MEDIUM',
        'expected_is_immoral': True
    },
    'threat_high': {
        'text': '찾아가서 끝장낼거야! 참교육 해줄거야!',
        'expected_intensity': 2.5,
        'expected_label_type': 'SPECIAL',
        'expected_intensity_level': 'HIGH',
        'expected_is_immoral': True
    },
    'unreasonable_demand': {
        'text': '지금 당장 환불해줘! FBI를 불러줘!',
        'expected_intensity': 1.5,
        'expected_label_type': 'SPECIAL',
        'expected_intensity_level': 'MEDIUM',
        'expected_is_immoral': True
    },
    'normal_thanks': {
        'text': '감사합니다. 좋은 서비스였어요.',
        'expected_intensity': 0.0,
        'expected_label_type': 'NORMAL',
        'expected_intensity_level': 'LOW',
        'expected_is_immoral': False
    }
}

# Turn 단위 테스트용 STT 데이터
STT_TEST_DATA = {
    'normal_session': {
        'session_id': 'test_normal_001',
        'segments': [
            {'speaker': 'customer', 'text': '안녕하세요. 상품 문의가 있어서 전화드렸습니다.'},
            {'speaker': 'agent', 'text': '네 고객님, 무엇을 도와드릴까요?'},
            {'speaker': 'customer', 'text': '이 상품의 배송 일정을 알려주세요.'},
            {'speaker': 'agent', 'text': '네 배송은 보통 2-3일 소요됩니다.'}
        ]
    },
    'profanity_session': {
        'session_id': 'test_profanity_001',
        'segments': [
            {'speaker': 'customer', 'text': '시발놈아! 이게 뭐야?'},
            {'speaker': 'agent', 'text': '죄송합니다. 어떤 불편이 있으셨나요?'}
        ]
    },
    'complaint_session': {
        'session_id': 'test_complaint_001',
        'segments': [
            {'speaker': 'customer', 'text': '서비스가 너무 불만족스럽습니다. 보상해주세요.'},
            {'speaker': 'agent', 'text': '불편을 드려 죄송합니다. 구체적으로 어떤 문제가 있었는지 말씀해주시겠어요?'}
        ]
    }
}

# Turn Scores 계산 테스트용 데이터
# 주의: customer_problem_score는 intensity 정보가 반영된 후의 값입니다.
# 실제 계산: profanity_score * intensity_multiplier + intensity_score
TURN_SCORES_TEST_CASES = {
    'high_customer_problem_good_agent': {
        'customer_problem_score': 0.8,  # profanity_score
        'agent_response_quality_score': 0.9,
        'intensity_level': 'MEDIUM',
        'intensity': 2.0,
        # 계산: profanity_score=0.8, MEDIUM이므로 0.8*1.1=0.88, intensity=2.0/3.0*0.8=0.533
        # customer_problem_score = max(0.88, 0.533) = 0.88
        # adjusted_risk = 0.88 - 0.9*0.3 = 0.61
        # turn_risk_score = 0.61 * 1.05 = 0.6405
        'expected_turn_risk_score': 0.6405
    },
    'high_customer_problem_no_agent': {
        'customer_problem_score': 0.8,  # profanity_score
        'agent_response_quality_score': 0.0,
        'intensity_level': 'HIGH',
        'intensity': 2.5,
        # 계산: profanity_score=0.8, HIGH이므로 0.8*1.2=0.96, intensity=2.5/3.0=0.833
        # customer_problem_score = max(0.96, 0.833) = 0.96
        # adjusted_risk = 0.96 (상담원 대응 없음)
        # turn_risk_score = min(0.96 * 1.15, 1.0) = 1.0
        'expected_turn_risk_score': 1.0
    },
    'low_customer_problem_poor_agent': {
        'customer_problem_score': 0.3,  # profanity_score
        'agent_response_quality_score': 0.2,
        'intensity_level': 'LOW',
        'intensity': 1.0,
        # 계산: profanity_score=0.3, LOW이므로 intensity만 추가: 1.0/3.0*0.5=0.167
        # customer_problem_score = max(0.3, 0.167) = 0.3
        # adjusted_risk = 0.3 - 0.2*0.3 = 0.24
        # turn_risk_score = 0.24 * 1.0 = 0.24
        'expected_turn_risk_score': 0.24
    },
    'medium_customer_problem_medium_agent': {
        'customer_problem_score': 0.6,  # profanity_score
        'agent_response_quality_score': 0.5,
        'intensity_level': 'MEDIUM',
        'intensity': 2.0,
        # 계산: profanity_score=0.6, MEDIUM이므로 0.6*1.1=0.66, intensity=2.0/3.0*0.8=0.533
        # customer_problem_score = max(0.66, 0.533) = 0.66
        # adjusted_risk = 0.66 - 0.5*0.3 = 0.51
        # turn_risk_score = 0.51 * 1.05 = 0.5355
        'expected_turn_risk_score': 0.5355
    }
}

