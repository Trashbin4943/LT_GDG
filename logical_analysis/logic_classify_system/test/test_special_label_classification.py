"""
문제 발화 데이터셋 Special Label 분류 테스트

전처리된 talksets STT 데이터셋을 MainPipeline에 입력하여
Special Label로 잘 분류되는지 확인하는 테스트
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Any
from collections import Counter, defaultdict
from datetime import datetime

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from logical_analysis.logic_classify_system.pipeline.main_pipeline import MainPipeline
from logical_analysis.logic_classify_system.config.labels import NORMAL_LABELS, SPECIAL_LABELS


def print_separator(title: str):
    """구분선 출력"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def load_stt_file(file_path: Path) -> Dict[str, Any]:
    """STT 파일 로드"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def analyze_label_distribution(results: List[Any]) -> Dict[str, Any]:
    """Label 분포 분석"""
    stats = {
        'total_turns': 0,
        'normal_labels': Counter(),
        'special_labels': Counter(),
        'normal_count': 0,
        'special_count': 0,
        'label_type_distribution': Counter(),
        'confidence_stats': {
            'normal': [],
            'special': []
        },
        'label_details': defaultdict(lambda: {'count': 0, 'confidence_sum': 0.0, 'examples': []}),
        'special_label_breakdown': defaultdict(lambda: {
            'count': 0,
            'confidence_sum': 0.0,
            'examples': [],
            'profanity_score_sum': 0.0,
            'threat_score_sum': 0.0,
            'feature_stats': defaultdict(list)
        })
    }
    
    for result in results:
        # PipelineResult 객체에서 turn_results 속성 접근
        turn_results = result.turn_results if hasattr(result, 'turn_results') else []
        
        for turn_result in turn_results:
            customer_result = turn_result.customer_result
            label = customer_result.classification_result.label
            label_type = customer_result.classification_result.label_type
            confidence = customer_result.classification_result.confidence
            text = customer_result.text  # 전체 텍스트
            
            stats['total_turns'] += 1
            stats['label_type_distribution'][label_type] += 1
            
            stats['label_details'][label]['count'] += 1
            stats['label_details'][label]['confidence_sum'] += confidence
            
            # 예시 저장 (최대 5개)
            if len(stats['label_details'][label]['examples']) < 5:
                stats['label_details'][label]['examples'].append({
                    'text': text,
                    'confidence': confidence
                })
            
            if label_type == 'NORMAL':
                stats['normal_count'] += 1
                stats['normal_labels'][label] += 1
                stats['confidence_stats']['normal'].append(confidence)
            elif label_type == 'SPECIAL':
                stats['special_count'] += 1
                stats['special_labels'][label] += 1
                stats['confidence_stats']['special'].append(confidence)
                
                # Special Label 상세 분석
                special_label_stats = stats['special_label_breakdown'][label]
                special_label_stats['count'] += 1
                special_label_stats['confidence_sum'] += confidence
                
                # 예시 저장 (최대 5개)
                if len(special_label_stats['examples']) < 5:
                    special_label_stats['examples'].append({
                        'text': text,
                        'confidence': confidence,
                        'feature_scores': customer_result.feature_scores,
                        'extracted_features': customer_result.extracted_features
                    })
                
                # 특징점 점수 수집
                feature_scores = customer_result.feature_scores
                for feature_name, feature_value in feature_scores.items():
                    if isinstance(feature_value, (int, float)):
                        special_label_stats['feature_stats'][feature_name].append(feature_value)
                
                # 주요 특징점 점수 합산
                profanity_score = feature_scores.get('profanity_score', 0.0)
                threat_score = feature_scores.get('threat_score', 0.0)
                special_label_stats['profanity_score_sum'] += profanity_score
                special_label_stats['threat_score_sum'] += threat_score
    
    return stats


def print_statistics(stats: Dict[str, Any], total_files: int):
    """통계 정보 출력"""
    print(f"총 처리 파일 수: {total_files:,}")
    print(f"총 Turn 수: {stats['total_turns']:,}")
    print()
    
    # Label 타입 분포
    print("=" * 80)
    print("Label 타입 분포")
    print("=" * 80)
    total = stats['total_turns']
    normal_ratio = (stats['normal_count'] / total * 100) if total > 0 else 0
    special_ratio = (stats['special_count'] / total * 100) if total > 0 else 0
    
    print(f"Normal Label: {stats['normal_count']:,}개 ({normal_ratio:.2f}%)")
    print(f"Special Label: {stats['special_count']:,}개 ({special_ratio:.2f}%)")
    print()
    
    # Normal Label 분포 (간단히)
    if stats['normal_labels']:
        print("=" * 80)
        print("Normal Label 분포")
        print("=" * 80)
        for label, count in stats['normal_labels'].most_common():
            ratio = (count / stats['normal_count'] * 100) if stats['normal_count'] > 0 else 0
            avg_confidence = (
                stats['label_details'][label]['confidence_sum'] / count
                if count > 0 else 0
            )
            print(f"  {label:20s}: {count:6,}개 ({ratio:6.2f}%) - 평균 신뢰도: {avg_confidence:.3f}")
        print()
    
    # Special Label 상세 분포
    if stats['special_labels']:
        print("=" * 80)
        print("Special Label 상세 분포")
        print("=" * 80)
        for label, count in stats['special_labels'].most_common():
            ratio = (count / stats['special_count'] * 100) if stats['special_count'] > 0 else 0
            avg_confidence = (
                stats['label_details'][label]['confidence_sum'] / count
                if count > 0 else 0
            )
            print(f"\n  {label}:")
            print(f"    개수: {count:,}개 ({ratio:.2f}%)")
            print(f"    평균 신뢰도: {avg_confidence:.3f}")
            
            # 특징점 점수 통계
            special_stats = stats['special_label_breakdown'][label]
            if special_stats['count'] > 0:
                avg_profanity = special_stats['profanity_score_sum'] / special_stats['count']
                avg_threat = special_stats['threat_score_sum'] / special_stats['count']
                print(f"    평균 욕설 점수: {avg_profanity:.3f}")
                print(f"    평균 위협 점수: {avg_threat:.3f}")
                
                # 각 특징점별 평균
                for feature_name, feature_values in special_stats['feature_stats'].items():
                    if feature_values:
                        avg_value = sum(feature_values) / len(feature_values)
                        print(f"    평균 {feature_name}: {avg_value:.3f}")
        print()
    
    # 신뢰도 통계
    print("=" * 80)
    print("신뢰도 통계")
    print("=" * 80)
    if stats['confidence_stats']['normal']:
        normal_confidences = stats['confidence_stats']['normal']
        print(f"Normal Label 평균 신뢰도: {sum(normal_confidences) / len(normal_confidences):.3f}")
        print(f"Normal Label 최소 신뢰도: {min(normal_confidences):.3f}")
        print(f"Normal Label 최대 신뢰도: {max(normal_confidences):.3f}")
        print()
    
    if stats['confidence_stats']['special']:
        special_confidences = stats['confidence_stats']['special']
        print(f"Special Label 평균 신뢰도: {sum(special_confidences) / len(special_confidences):.3f}")
        print(f"Special Label 최소 신뢰도: {min(special_confidences):.3f}")
        print(f"Special Label 최대 신뢰도: {max(special_confidences):.3f}")
        print()


def print_special_label_examples(stats: Dict[str, Any], top_n: int = 3):
    """Special Label별 상세 예시 출력"""
    print("=" * 80)
    print("Special Label별 상세 예시")
    print("=" * 80)
    
    # Special Label 예시
    special_labels = sorted([label for label in stats['label_details'].keys() if label in SPECIAL_LABELS])
    
    for label in special_labels:
        examples = stats['special_label_breakdown'][label]['examples']
        if examples:
            print(f"\n[{label}]")
            print("-" * 80)
            for i, ex in enumerate(examples[:top_n], 1):
                print(f"\n  예시 {i}:")
                print(f"    발화: {ex['text']}...")
                print(f"    신뢰도: {ex['confidence']:.3f}")
                
                # 주요 특징점 점수
                feature_scores = ex.get('feature_scores', {})
                print(f"    특징점 점수:")
                for feature_name in ['profanity_score', 'threat_score', 'sexual_harassment_score', 
                                    'hate_speech_score', 'unreasonable_demand_score']:
                    if feature_name in feature_scores and feature_scores[feature_name] > 0:
                        print(f"      - {feature_name}: {feature_scores[feature_name]:.3f}")
                
                # 추출된 특징점
                extracted_features = ex.get('extracted_features', {})
                if extracted_features:
                    print(f"    추출된 특징점:")
                    for key, value in extracted_features.items():
                        if value:  # 비어있지 않은 경우만
                            if isinstance(value, list) and len(value) > 0:
                                print(f"      - {key}: {value[:3]}")  # 최대 3개만
                            elif not isinstance(value, list):
                                print(f"      - {key}: {value}")


def test_special_label_classification(
    data_dir: Path,
    max_files: int = None,
    sample_size: int = 200
):
    """
    문제 발화 데이터셋 Special Label 분류 테스트
    
    Args:
        data_dir: STT 데이터 파일이 있는 디렉토리
        max_files: 최대 처리할 파일 수 (None이면 샘플링)
        sample_size: 샘플 크기 (전체 데이터가 많을 경우)
    """
    print_separator("문제 발화 데이터셋 Special Label 분류 테스트")
    
    # STT 파일 목록 가져오기
    stt_files = sorted(data_dir.glob('talksets_stt_*.json'))
    
    if not stt_files:
        print(f"[오류] STT 파일을 찾을 수 없습니다: {data_dir}")
        return
    
    print(f"발견된 STT 파일 수: {len(stt_files):,}")
    
    # 샘플링 (전체가 너무 많을 경우)
    if max_files is None and len(stt_files) > sample_size:
        print(f"파일이 너무 많아 {sample_size}개 샘플만 처리합니다.")
        import random
        stt_files = random.sample(stt_files, sample_size)
    elif max_files:
        stt_files = stt_files[:max_files]
    
    print(f"처리할 파일 수: {len(stt_files):,}")
    print()
    
    # MainPipeline 초기화
    pipeline = MainPipeline()
    
    # 결과 저장
    all_results = []
    processed_files = 0
    failed_files = 0
    
    print("파일 처리 중...")
    for i, stt_file in enumerate(stt_files, 1):
        try:
            # STT 파일 로드
            stt_data = load_stt_file(stt_file)
            
            # MainPipeline으로 처리
            result = pipeline.process(stt_data)
            
            # 결과 저장
            all_results.append(result)
            processed_files += 1
            
            # 진행 상황 출력 (50개마다)
            if i % 50 == 0:
                print(f"  진행 상황: {i}/{len(stt_files)} 파일 처리 완료")
        
        except Exception as e:
            failed_files += 1
            if failed_files <= 5:  # 최대 5개 오류만 출력
                print(f"  [오류] 오류 발생 ({stt_file.name}): {e}")
            continue
    
    print()
    print(f"처리 완료: {processed_files:,}개 성공, {failed_files:,}개 실패")
    print()
    
    if not all_results:
        print("[오류] 처리된 결과가 없습니다.")
        return
    
    # 통계 분석
    stats = analyze_label_distribution(all_results)
    
    # 결과 출력
    print_statistics(stats, processed_files)
    
    # Special Label 상세 예시 출력
    print_special_label_examples(stats)
    
    # 최종 평가
    print_separator("최종 평가")
    total = stats['total_turns']
    special_ratio = (stats['special_count'] / total * 100) if total > 0 else 0
    normal_ratio = (stats['normal_count'] / total * 100) if total > 0 else 0
    
    print(f"Normal Label 분류 비율: {normal_ratio:.2f}%")
    print(f"Special Label 분류 비율: {special_ratio:.2f}%")
    print()
    
    # Special Label 종류별 분포
    if stats['special_labels']:
        print("Special Label 종류별 분포:")
        for label, count in stats['special_labels'].most_common():
            ratio = (count / stats['special_count'] * 100) if stats['special_count'] > 0 else 0
            print(f"  - {label}: {count:,}개 ({ratio:.2f}%)")
        print()
    
    # 평가 결과
    if special_ratio >= 30:
        print("[성공] 문제 발화 데이터셋이 Special Label로 잘 분류되고 있습니다.")
    elif special_ratio >= 15:
        print("[주의] Special Label 분류 비율이 다소 낮습니다. 일부 문제 발화가 Normal로 분류되었을 수 있습니다.")
    else:
        print("[경고] Special Label 분류 비율이 낮습니다. 분류 로직을 재검토해야 합니다.")
    
    # Summary 문서 생성
    from .generate_summaries import generate_special_label_summary
    script_dir = Path(__file__).parent
    summary_path = script_dir / 'test_results' / 'special_label_classification_analysis_v2.md'
    generate_special_label_summary(stats, processed_files, summary_path)
    
    return stats


def main():
    """메인 함수"""
    # 현재 스크립트의 디렉토리 기준으로 경로 설정
    script_dir = Path(__file__).parent
    data_dir = script_dir / 'talksets_stt'
    
    if not data_dir.exists():
        print(f"[오류] 데이터 디렉토리가 존재하지 않습니다: {data_dir}")
        print("먼저 preprocess_talksets_to_stt.py를 실행하여 데이터를 전처리하세요.")
        return
    
    # 테스트 실행
    # 전체 데이터가 많을 수 있으므로 샘플 크기 지정 가능
    test_special_label_classification(
        data_dir=data_dir,
        max_files=None,  # None이면 샘플링, 숫자를 지정하면 해당 개수만 처리
        sample_size=500  # 전체가 많을 경우 샘플 크기
    )


if __name__ == "__main__":
    main()

