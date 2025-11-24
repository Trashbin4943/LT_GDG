"""
정답지 기반 검증 테스트

talksets 원본 데이터의 label과 윤리 score를 매핑한 정답지를 구성하여,
Special Label로 분류되어야 하지만 Normal Label로 분류된 케이스를 확인
"""

import sys
import json
import random
from pathlib import Path
from typing import Dict, List, Any, Tuple
from collections import Counter, defaultdict
from datetime import datetime

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from logical_analysis.logic_classify_system.pipeline.main_pipeline import MainPipeline
from logical_analysis.logic_classify_system.config.labels import NORMAL_LABELS, SPECIAL_LABELS
from logical_analysis.logic_classify_system.test.test_special_label_classification import (
    print_separator,
    load_stt_file,
    analyze_label_distribution
)


# talksets types를 우리 시스템의 SPECIAL_LABELS로 매핑
TYPES_TO_SPECIAL_LABEL = {
    "HATE": "HATE_SPEECH",
    "DISCRIMINATION": "HATE_SPEECH",  # 차별/혐오 표현
    "CENSURE": "PROFANITY",  # 비난/욕설로 간주
    "ABUSE": "PROFANITY",  # 학대/욕설
    "SEXUAL": "SEXUAL_HARASSMENT",
    "VIOLENCE": "VIOLENCE_THREAT",
    "CRIME": "VIOLENCE_THREAT",  # 범죄 관련 위협
    "THREAT": "VIOLENCE_THREAT",
    "UNREASONABLE": "UNREASONABLE_DEMAND",
    "REPETITION": "REPETITION",
}

# talksets types를 우리 시스템의 NORMAL_LABELS로 매핑 (일반적인 경우)
TYPES_TO_NORMAL_LABEL = {
    "IMMORAL_NONE": "INQUIRY",  # 기본값
    # 추가 매핑 필요시 확장
}


def map_talksets_types_to_label(types: List[str], is_immoral: bool, intensity: float) -> Tuple[str, str]:
    """
    talksets의 types를 우리 시스템의 Label로 매핑
    
    Args:
        types: talksets의 types 배열 (예: ["HATE", "CENSURE"])
        is_immoral: 윤리적 문제 여부
        intensity: 강도 점수
    
    Returns:
        (label, label_type) 튜플
    """
    # is_immoral이 True이고 intensity가 높으면 Special Label
    if is_immoral and intensity > 0:
        # types를 확인하여 특정 Special Label로 매핑
        for talkset_type in types:
            if talkset_type in TYPES_TO_SPECIAL_LABEL:
                return (TYPES_TO_SPECIAL_LABEL[talkset_type], "SPECIAL")
        
        # 매핑되지 않은 경우 기본 Special Label
        # intensity에 따라 결정
        if intensity >= 1.5:
            return ("VIOLENCE_THREAT", "SPECIAL")
        elif intensity >= 1.0:
            return ("PROFANITY", "SPECIAL")
        else:
            return ("UNREASONABLE_DEMAND", "SPECIAL")
    
    # Normal Label
    for talkset_type in types:
        if talkset_type in TYPES_TO_NORMAL_LABEL:
            return (TYPES_TO_NORMAL_LABEL[talkset_type], "NORMAL")
    
    # 기본값
    return ("INQUIRY", "NORMAL")


def create_ground_truth_dataset(
    talksets_file: Path,
    sample_size: int = 500,
    output_dir: Path = None
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    talksets 원본 데이터에서 샘플을 추출하여 STT 입력 양식과 정답지 구성
    
    Args:
        talksets_file: talksets 원본 JSON 파일 경로
        sample_size: 샘플 크기
        output_dir: 출력 디렉토리 (None이면 저장하지 않음)
    
    Returns:
        (stt_data_list, ground_truth_list) 튜플
        - stt_data_list: STT 입력 양식 리스트
        - ground_truth_list: 정답지 리스트 (각 segment별 정답 Label 정보)
    """
    print(f"talksets 파일 로드 중: {talksets_file.name}")
    
    # JSON 파일 읽기
    with open(talksets_file, 'r', encoding='utf-8') as f:
        talksets_data = json.load(f)
    
    # 리스트가 아닌 경우 리스트로 변환
    if not isinstance(talksets_data, list):
        talksets_data = [talksets_data]
    
    print(f"총 {len(talksets_data):,}개 대화 로드")
    
    # is_immoral이 True인 대화 우선 선택 (Special Label이 있을 가능성이 높음)
    immoral_conversations = [c for c in talksets_data if any(
        s.get('is_immoral', False) for s in c.get('sentences', [])
    )]
    
    normal_conversations = [c for c in talksets_data if not any(
        s.get('is_immoral', False) for s in c.get('sentences', [])
    )]
    
    print(f"윤리 문제 대화: {len(immoral_conversations):,}개")
    print(f"정상 대화: {len(normal_conversations):,}개")
    
    # 샘플링: immoral 대화 70%, normal 대화 30%
    immoral_sample_size = int(sample_size * 0.7)
    normal_sample_size = sample_size - immoral_sample_size
    
    if len(immoral_conversations) < immoral_sample_size:
        immoral_sample_size = len(immoral_conversations)
        normal_sample_size = sample_size - immoral_sample_size
    
    if len(normal_conversations) < normal_sample_size:
        normal_sample_size = len(normal_conversations)
        immoral_sample_size = sample_size - normal_sample_size
    
    selected_immoral = random.sample(immoral_conversations, immoral_sample_size) if immoral_conversations else []
    selected_normal = random.sample(normal_conversations, normal_sample_size) if normal_conversations else []
    
    selected_conversations = selected_immoral + selected_normal
    random.shuffle(selected_conversations)
    
    print(f"샘플링 완료: {len(selected_conversations)}개 대화 선택")
    print(f"  - 윤리 문제 대화: {len(selected_immoral)}개")
    print(f"  - 정상 대화: {len(selected_normal)}개")
    print()
    
    # STT 입력 양식과 정답지 생성
    stt_data_list = []
    ground_truth_list = []
    
    for talk_item in selected_conversations:
        talk_id = talk_item.get('id', f"talk_{len(stt_data_list)}")
        sentences = talk_item.get('sentences', [])
        
        if not sentences:
            continue
        
        # segments와 ground_truth 생성
        segments = []
        ground_truth_segments = []
        segment_index = 0
        
        for sentence in sentences:
            speaker_num = sentence.get('speaker', 1)
            text = sentence.get('text', '').strip()
            
            # 빈 텍스트 제외
            if not text:
                continue
            
            # speaker 번호를 화자 라벨로 변환
            speaker = "customer" if speaker_num == 1 else "agent"
            
            # 타임스탬프 생성
            start_time = segment_index * 2.0
            end_time = (segment_index + 1) * 2.0
            
            segments.append({
                "speaker": speaker,
                "text": text,
                "start": start_time,
                "end": end_time
            })
            
            # 정답지 생성 (customer 발화만)
            if speaker == "customer":
                types = sentence.get('types', [])
                is_immoral = sentence.get('is_immoral', False)
                intensity = sentence.get('intensity', 0.0)
                intensity_sum = sentence.get('intensity_sum', 0)
                
                # Label 매핑
                label, label_type = map_talksets_types_to_label(types, is_immoral, intensity)
                
                ground_truth_segments.append({
                    "segment_index": segment_index,
                    "text": text,
                    "ground_truth_label": label,
                    "ground_truth_label_type": label_type,
                    "talksets_types": types,
                    "is_immoral": is_immoral,
                    "intensity": intensity,
                    "intensity_sum": intensity_sum
                })
            
            segment_index += 1
        
        if not segments:
            continue
        
        # STT 표준 형식 생성
        session_id = f"session_{talk_id}"
        stt_data = {
            "session_id": session_id,
            "segments": segments,
            "metadata": {
                "source": "talksets-train",
                "talk_id": talk_id,
                "total_sentences": len(sentences),
                "immoral_count": sum(1 for s in sentences if s.get('is_immoral', False))
            }
        }
        
        stt_data_list.append(stt_data)
        
        # 정답지 생성
        ground_truth = {
            "session_id": session_id,
            "talk_id": talk_id,
            "segments": ground_truth_segments,
            "total_segments": len(ground_truth_segments),
            "immoral_segments": sum(1 for s in ground_truth_segments if s['is_immoral'])
        }
        
        ground_truth_list.append(ground_truth)
    
    # 파일 저장
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # STT 데이터 저장
        stt_output_dir = output_dir / 'stt_data'
        stt_output_dir.mkdir(parents=True, exist_ok=True)
        
        for stt_data in stt_data_list:
            talk_id = stt_data['session_id'].replace('session_', '')
            output_path = stt_output_dir / f"ground_truth_stt_{talk_id}.json"
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(stt_data, f, ensure_ascii=False, indent=2)
        
        # 정답지 저장
        ground_truth_path = output_dir / 'ground_truth.json'
        with open(ground_truth_path, 'w', encoding='utf-8') as f:
            json.dump(ground_truth_list, f, ensure_ascii=False, indent=2)
        
        print(f"\n[저장 완료]")
        print(f"  STT 데이터: {stt_output_dir} ({len(stt_data_list)}개 파일)")
        print(f"  정답지: {ground_truth_path}")
        print()
    
    return stt_data_list, ground_truth_list


def validate_with_ground_truth(
    stt_data_list: List[Dict[str, Any]],
    ground_truth_list: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    정답지와 비교하여 검증 결과 생성
    
    Args:
        stt_data_list: STT 입력 데이터 리스트
        ground_truth_list: 정답지 리스트
    
    Returns:
        검증 결과 통계
    """
    print_separator("정답지 기반 검증 시작")
    
    # MainPipeline 초기화
    pipeline = MainPipeline()
    
    # 검증 결과 저장
    validation_results = {
        'total_segments': 0,
        'correct_classifications': 0,
        'incorrect_classifications': 0,
        'false_negatives': [],  # Special로 분류되어야 하는데 Normal로 분류된 케이스
        'false_positives': [],  # Normal로 분류되어야 하는데 Special로 분류된 케이스
        'label_type_accuracy': {
            'NORMAL': {'correct': 0, 'total': 0},
            'SPECIAL': {'correct': 0, 'total': 0}
        },
        'label_accuracy': defaultdict(lambda: {'correct': 0, 'total': 0}),
        'confusion_matrix': defaultdict(lambda: defaultdict(int))
    }
    
    # 세션 ID로 정답지 매핑
    ground_truth_map = {gt['session_id']: gt for gt in ground_truth_list}
    
    print(f"총 {len(stt_data_list)}개 세션 처리 중...")
    
    for i, stt_data in enumerate(stt_data_list, 1):
        session_id = stt_data['session_id']
        ground_truth = ground_truth_map.get(session_id)
        
        if not ground_truth:
            continue
        
        try:
            # MainPipeline으로 처리
            result = pipeline.process(stt_data)
            
            # Turn 결과와 정답지 비교
            turn_results = result.turn_results if hasattr(result, 'turn_results') else []
            ground_truth_segments = ground_truth['segments']
            
            # Turn 결과를 segment_index로 매핑
            turn_map = {}
            for turn_result in turn_results:
                # turn_index를 segment_index로 간주 (실제로는 더 정확한 매핑 필요)
                turn_index = turn_result.turn_index if hasattr(turn_result, 'turn_index') else len(turn_map)
                turn_map[turn_index] = turn_result
            
            # 각 정답지 segment와 비교
            for gt_segment in ground_truth_segments:
                segment_index = gt_segment['segment_index']
                turn_result = turn_map.get(segment_index)
                
                if not turn_result:
                    continue
                
                customer_result = turn_result.customer_result
                predicted_label = customer_result.classification_result.label
                predicted_label_type = customer_result.classification_result.label_type
                predicted_confidence = customer_result.classification_result.confidence
                
                ground_truth_label = gt_segment['ground_truth_label']
                ground_truth_label_type = gt_segment['ground_truth_label_type']
                
                validation_results['total_segments'] += 1
                
                # Label 타입 정확도
                validation_results['label_type_accuracy'][ground_truth_label_type]['total'] += 1
                if predicted_label_type == ground_truth_label_type:
                    validation_results['label_type_accuracy'][ground_truth_label_type]['correct'] += 1
                    validation_results['correct_classifications'] += 1
                else:
                    validation_results['incorrect_classifications'] += 1
                    
                    # False Negative: Special로 분류되어야 하는데 Normal로 분류
                    if ground_truth_label_type == 'SPECIAL' and predicted_label_type == 'NORMAL':
                        validation_results['false_negatives'].append({
                            'session_id': session_id,
                            'segment_index': segment_index,
                            'text': gt_segment['text'],
                            'ground_truth_label': ground_truth_label,
                            'predicted_label': predicted_label,
                            'predicted_confidence': predicted_confidence,
                            'is_immoral': gt_segment['is_immoral'],
                            'intensity': gt_segment['intensity'],
                            'talksets_types': gt_segment['talksets_types']
                        })
                    
                    # False Positive: Normal로 분류되어야 하는데 Special로 분류
                    elif ground_truth_label_type == 'NORMAL' and predicted_label_type == 'SPECIAL':
                        validation_results['false_positives'].append({
                            'session_id': session_id,
                            'segment_index': segment_index,
                            'text': gt_segment['text'],
                            'ground_truth_label': ground_truth_label,
                            'predicted_label': predicted_label,
                            'predicted_confidence': predicted_confidence
                        })
                
                # Label 정확도
                validation_results['label_accuracy'][ground_truth_label]['total'] += 1
                if predicted_label == ground_truth_label:
                    validation_results['label_accuracy'][ground_truth_label]['correct'] += 1
                
                # Confusion Matrix
                validation_results['confusion_matrix'][ground_truth_label][predicted_label] += 1
            
            # 진행 상황 출력
            if i % 50 == 0:
                print(f"  진행 상황: {i}/{len(stt_data_list)} 세션 처리 완료")
        
        except Exception as e:
            print(f"  [오류] 세션 처리 실패 ({session_id}): {e}")
            continue
    
    return validation_results


def print_validation_results(results: Dict[str, Any]):
    """검증 결과 출력"""
    print_separator("검증 결과")
    
    total = results['total_segments']
    if total == 0:
        print("[오류] 검증할 segment가 없습니다.")
        return
    
    correct = results['correct_classifications']
    incorrect = results['incorrect_classifications']
    
    print(f"총 검증 Segment 수: {total:,}개")
    print(f"정확히 분류: {correct:,}개 ({correct / total * 100:.2f}%)")
    print(f"오분류: {incorrect:,}개 ({incorrect / total * 100:.2f}%)")
    print()
    
    # Label 타입별 정확도
    print("=" * 80)
    print("Label 타입별 정확도")
    print("=" * 80)
    for label_type in ['NORMAL', 'SPECIAL']:
        stats = results['label_type_accuracy'][label_type]
        if stats['total'] > 0:
            accuracy = stats['correct'] / stats['total'] * 100
            print(f"{label_type}: {stats['correct']}/{stats['total']} ({accuracy:.2f}%)")
    print()
    
    # False Negatives (Special로 분류되어야 하는데 Normal로 분류)
    false_negatives = results['false_negatives']
    print("=" * 80)
    print(f"False Negatives (Special → Normal 오분류): {len(false_negatives)}개")
    print("=" * 80)
    
    if false_negatives:
        print("\n[상위 10개 예시]")
        for i, fn in enumerate(false_negatives[:10], 1):
            print(f"\n{i}. {fn['text'][:100]}...")
            print(f"   정답: {fn['ground_truth_label']} (SPECIAL)")
            print(f"   예측: {fn['predicted_label']} (NORMAL)")
            print(f"   신뢰도: {fn['predicted_confidence']:.3f}")
            print(f"   윤리 점수: {fn['intensity']:.2f} (is_immoral: {fn['is_immoral']})")
            print(f"   talksets types: {fn['talksets_types']}")
    else:
        print("False Negative가 없습니다.")
    print()
    
    # False Positives (Normal로 분류되어야 하는데 Special로 분류)
    false_positives = results['false_positives']
    print("=" * 80)
    print(f"False Positives (Normal → Special 오분류): {len(false_positives)}개")
    print("=" * 80)
    
    if false_positives:
        print("\n[상위 10개 예시]")
        for i, fp in enumerate(false_positives[:10], 1):
            print(f"\n{i}. {fp['text'][:100]}...")
            print(f"   정답: {fp['ground_truth_label']} (NORMAL)")
            print(f"   예측: {fp['predicted_label']} (SPECIAL)")
            print(f"   신뢰도: {fp['predicted_confidence']:.3f}")
    else:
        print("False Positive가 없습니다.")
    print()
    
    # Label별 정확도
    print("=" * 80)
    print("Label별 정확도")
    print("=" * 80)
    for label in sorted(results['label_accuracy'].keys()):
        stats = results['label_accuracy'][label]
        if stats['total'] > 0:
            accuracy = stats['correct'] / stats['total'] * 100
            print(f"{label:25s}: {stats['correct']:4d}/{stats['total']:4d} ({accuracy:6.2f}%)")
    print()
    
    # Confusion Matrix (간단히)
    print("=" * 80)
    print("Confusion Matrix (상위 10개)")
    print("=" * 80)
    confusion_items = []
    for true_label, pred_dict in results['confusion_matrix'].items():
        for pred_label, count in pred_dict.items():
            if true_label != pred_label and count > 0:
                confusion_items.append((true_label, pred_label, count))
    
    confusion_items.sort(key=lambda x: x[2], reverse=True)
    for true_label, pred_label, count in confusion_items[:10]:
        print(f"{true_label:25s} → {pred_label:25s}: {count:4d}개")


def test_with_ground_truth(
    talksets_file: Path,
    sample_size: int = 500,
    output_dir: Path = None
):
    """
    정답지 기반 검증 테스트 실행
    
    Args:
        talksets_file: talksets 원본 JSON 파일 경로
        sample_size: 샘플 크기
        output_dir: 출력 디렉토리
    """
    print_separator("정답지 기반 검증 테스트")
    
    if not talksets_file.exists():
        print(f"[오류] talksets 파일을 찾을 수 없습니다: {talksets_file}")
        return
    
    # 1. 정답지 데이터셋 생성
    print("1단계: 정답지 데이터셋 생성")
    stt_data_list, ground_truth_list = create_ground_truth_dataset(
        talksets_file=talksets_file,
        sample_size=sample_size,
        output_dir=output_dir
    )
    
    if not stt_data_list or not ground_truth_list:
        print("[오류] 데이터셋 생성 실패")
        return
    
    # 2. 검증 실행
    print("\n2단계: MainPipeline으로 검증 실행")
    validation_results = validate_with_ground_truth(stt_data_list, ground_truth_list)
    
    # 3. 결과 출력
    print("\n3단계: 검증 결과 분석")
    print_validation_results(validation_results)
    
    # 4. 결과 저장
    if output_dir:
        results_path = output_dir / 'validation_results.json'
        # JSON 직렬화 가능한 형태로 변환
        results_dict = {
            'total_segments': validation_results['total_segments'],
            'correct_classifications': validation_results['correct_classifications'],
            'incorrect_classifications': validation_results['incorrect_classifications'],
            'label_type_accuracy': dict(validation_results['label_type_accuracy']),
            'label_accuracy': {k: dict(v) for k, v in validation_results['label_accuracy'].items()},
            'confusion_matrix': {k: dict(v) for k, v in validation_results['confusion_matrix'].items()},
            'false_negatives_count': len(validation_results['false_negatives']),
            'false_positives_count': len(validation_results['false_positives']),
            'false_negatives': validation_results['false_negatives'][:50],  # 상위 50개만
            'false_positives': validation_results['false_positives'][:50]  # 상위 50개만
        }
        
        with open(results_path, 'w', encoding='utf-8') as f:
            json.dump(results_dict, f, ensure_ascii=False, indent=2)
        
        print(f"\n[저장 완료] 검증 결과: {results_path}")
    
    return validation_results


def main():
    """메인 함수"""
    script_dir = Path(__file__).parent
    
    # talksets 원본 파일 경로
    talksets_file = script_dir / 'talksets-train-6.json'
    
    # 출력 디렉토리
    output_dir = script_dir / 'ground_truth_validation'
    
    if not talksets_file.exists():
        print(f"[오류] talksets 파일을 찾을 수 없습니다: {talksets_file}")
        print("talksets-train-6.json 파일이 test 디렉토리에 있는지 확인하세요.")
        return
    
    # 테스트 실행
    test_with_ground_truth(
        talksets_file=talksets_file,
        sample_size=500,
        output_dir=output_dir
    )


if __name__ == "__main__":
    main()

