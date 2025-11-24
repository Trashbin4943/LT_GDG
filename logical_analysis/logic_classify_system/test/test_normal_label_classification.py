"""
정상 발화 데이터셋 Normal Label 분류 테스트

전처리된 STT 데이터셋을 MainPipeline에 입력하여
Normal Label로 잘 분류되는지 확인하는 테스트
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


def analyze_label_distribution(results: List[Any], session_results: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Label 분포 분석"""
    stats = {
        'total_turns': 0,
        'total_sessions': 0,
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
        'session_details': [],  # 세션별 상세 정보
        'special_label_examples': [],  # Special Label로 분류된 케이스 예시
        'normal_label_examples': defaultdict(lambda: []),  # Normal Label별 예시
    }
    
    session_idx = 0
    for result in results:
        # PipelineResult 객체에서 turn_results 속성 접근
        turn_results = result.turn_results if hasattr(result, 'turn_results') else []
        
        if not turn_results:
            continue
        
        session_id = result.session_id if hasattr(result, 'session_id') else f"session_{session_idx}"
        stats['total_sessions'] += 1
        
        session_info = {
            'session_id': session_id,
            'turn_count': len(turn_results),
            'normal_turns': 0,
            'special_turns': 0,
            'turns': []
        }
        
        for turn_result in turn_results:
            customer_result = turn_result.customer_result
            label = customer_result.classification_result.label
            label_type = customer_result.classification_result.label_type
            confidence = customer_result.classification_result.confidence
            text = customer_result.text
            probabilities = customer_result.classification_result.probabilities or {}
            
            # Turn 상세 정보
            turn_info = {
                'turn_index': turn_result.turn_index if hasattr(turn_result, 'turn_index') else 0,
                'text': text,
                'label': label,
                'label_type': label_type,
                'confidence': confidence,
                'probabilities': probabilities,
                'feature_scores': customer_result.feature_scores,
                'extracted_features': customer_result.extracted_features
            }
            
            stats['total_turns'] += 1
            stats['label_type_distribution'][label_type] += 1
            
            stats['label_details'][label]['count'] += 1
            stats['label_details'][label]['confidence_sum'] += confidence
            
            # 예시 저장 (최대 5개)
            if len(stats['label_details'][label]['examples']) < 5:
                stats['label_details'][label]['examples'].append({
                    'text': text[:100],  # 처음 100자
                    'confidence': confidence,
                    'probabilities': probabilities
                })
            
            if label_type == 'NORMAL':
                stats['normal_count'] += 1
                stats['normal_labels'][label] += 1
                stats['confidence_stats']['normal'].append(confidence)
                session_info['normal_turns'] += 1
                
                # Normal Label별 예시 저장 (최대 3개)
                if len(stats['normal_label_examples'][label]) < 3:
                    stats['normal_label_examples'][label].append({
                        'text': text[:100],
                        'confidence': confidence,
                        'probabilities': probabilities,
                        'feature_scores': customer_result.feature_scores
                    })
            
            elif label_type == 'SPECIAL':
                stats['special_count'] += 1
                stats['special_labels'][label] += 1
                stats['confidence_stats']['special'].append(confidence)
                session_info['special_turns'] += 1
                
                # Special Label로 분류된 케이스 예시 저장 (최대 10개)
                if len(stats['special_label_examples']) < 10:
                    stats['special_label_examples'].append({
                        'session_id': session_id,
                        'text': text[:100],
                        'label': label,
                        'confidence': confidence,
                        'feature_scores': customer_result.feature_scores,
                        'extracted_features': customer_result.extracted_features,
                        'probabilities': probabilities
                    })
            
            session_info['turns'].append(turn_info)
        
        # 세션별 상세 정보 저장 (Special Label이 있는 세션만 상세 저장)
        if session_info['special_turns'] > 0 or len(stats['session_details']) < 20:
            stats['session_details'].append(session_info)
        
        session_idx += 1
    
    return stats


def print_statistics(stats: Dict[str, Any], total_files: int):
    """통계 정보 출력"""
    print(f"총 처리 파일 수: {total_files}")
    print(f"총 Turn 수: {stats['total_turns']}")
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
    
    # Normal Label 분포
    if stats['normal_labels']:
        print("=" * 80)
        print("Normal Label 상세 분포")
        print("=" * 80)
        for label, count in stats['normal_labels'].most_common():
            ratio = (count / stats['normal_count'] * 100) if stats['normal_count'] > 0 else 0
            avg_confidence = (
                stats['label_details'][label]['confidence_sum'] / count
                if count > 0 else 0
            )
            print(f"  {label:20s}: {count:6,}개 ({ratio:6.2f}%) - 평균 신뢰도: {avg_confidence:.3f}")
        print()
    
    # Special Label 분포
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
            print(f"  {label:20s}: {count:6,}개 ({ratio:6.2f}%) - 평균 신뢰도: {avg_confidence:.3f}")
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


def print_label_examples(stats: Dict[str, Any], top_n: int = 3):
    """Label별 예시 출력"""
    print("=" * 80)
    print("Normal Label별 상세 분류 결과")
    print("=" * 80)
    
    # Normal Label 예시 (상세)
    normal_labels = sorted([label for label in stats['label_details'].keys() if label in NORMAL_LABELS])
    if normal_labels:
        for label in normal_labels:
            examples = stats['normal_label_examples'][label]
            if examples:
                print(f"\n[{label}] - {stats['label_details'][label]['count']:,}개")
                print("-" * 80)
                for i, ex in enumerate(examples, 1):
                    print(f"\n  예시 {i}:")
                    print(f"    발화: {ex['text']}")
                    print(f"    신뢰도: {ex['confidence']:.3f}")
                    if ex.get('probabilities'):
                        print(f"    확률 분포: {ex['probabilities']}")
                    if ex.get('feature_scores'):
                        feature_scores = ex['feature_scores']
                        # Special Label 신뢰도 (요인들 합산)
                        special_conf = feature_scores.get('special_label_confidence', 0.0)
                        if special_conf > 0:
                            print(f"    Special Label 신뢰도 (요인 합산): {special_conf:.3f}")
                            
                            # Special Label 요인별 점수
                            factor_scores = []
                            for factor_name in ['profanity_factor_score', 'threat_factor_score', 
                                              'sexual_harassment_factor_score', 'hate_speech_factor_score',
                                              'unreasonable_demand_factor_score', 'repetition_factor_score']:
                                factor_score = feature_scores.get(factor_name, 0.0)
                                if factor_score > 0:
                                    factor_label = factor_name.replace('_factor_score', '').upper()
                                    factor_scores.append(f"{factor_label}: {factor_score:.3f}")
                            
                            if factor_scores:
                                print(f"    Special Label 요인 점수: {', '.join(factor_scores)}")
    
    # Special Label로 분류된 케이스 예시
    if stats['special_label_examples']:
        print("\n" + "=" * 80)
        print("Normal Label로 분류되지 않은 케이스 (Special Label로 분류됨)")
        print("=" * 80)
        print(f"총 {len(stats['special_label_examples'])}개 케이스\n")
        
        for i, ex in enumerate(stats['special_label_examples'], 1):
            print(f"[케이스 {i}]")
            print(f"  세션 ID: {ex['session_id']}")
            print(f"  발화: {ex['text']}")
            print(f"  분류된 Label: {ex['label']} ({ex.get('label_type', 'SPECIAL')})")
            print(f"  신뢰도: {ex['confidence']:.3f}")
            
            # 특징점 점수
            if ex.get('feature_scores'):
                print(f"  특징점 점수:")
                for key, value in ex['feature_scores'].items():
                    if value > 0:
                        print(f"    - {key}: {value:.3f}")
            
            # 추출된 특징점
            if ex.get('extracted_features'):
                print(f"  추출된 특징점:")
                for key, value in ex['extracted_features'].items():
                    if value:
                        if isinstance(value, list):
                            print(f"    - {key}: {value[:3]}")  # 최대 3개만
                        else:
                            print(f"    - {key}: {value}")
            
            if ex.get('probabilities'):
                print(f"  확률 분포: {ex['probabilities']}")
            print()


def test_normal_label_classification(
    data_dir: Path,
    max_files: int = None,
    sample_size: int = 100
):
    """
    정상 발화 데이터셋 Normal Label 분류 테스트
    
    Args:
        data_dir: STT 데이터 파일이 있는 디렉토리
        max_files: 최대 처리할 파일 수 (None이면 모두 처리)
        sample_size: 샘플 크기 (전체 데이터가 많을 경우)
    """
    print_separator("정상 발화 데이터셋 Normal Label 분류 테스트")
    
    # STT 파일 목록 가져오기
    stt_files = sorted(data_dir.glob('*.json'))
    
    if not stt_files:
        print(f"[오류] STT 파일을 찾을 수 없습니다: {data_dir}")
        return
    
    print(f"발견된 STT 파일 수: {len(stt_files)}")
    
    # 샘플링 (전체가 너무 많을 경우)
    if max_files is None and len(stt_files) > sample_size:
        print(f"파일이 너무 많아 {sample_size}개 샘플만 처리합니다.")
        import random
        stt_files = random.sample(stt_files, sample_size)
    elif max_files:
        stt_files = stt_files[:max_files]
    
    print(f"처리할 파일 수: {len(stt_files)}")
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
            
            # 진행 상황 출력 (100개마다)
            if i % 100 == 0:
                print(f"  진행 상황: {i}/{len(stt_files)} 파일 처리 완료")
        
        except Exception as e:
            failed_files += 1
            if failed_files <= 5:  # 최대 5개 오류만 출력
                print(f"  [오류] 오류 발생 ({stt_file.name}): {e}")
            continue
    
    print()
    print(f"처리 완료: {processed_files}개 성공, {failed_files}개 실패")
    print()
    
    if not all_results:
        print("[오류] 처리된 결과가 없습니다.")
        return
    
    # 통계 분석 (세션 결과 포함)
    session_results = []  # 향후 확장용
    stats = analyze_label_distribution(all_results, session_results)
    
    # 결과 출력
    print_statistics(stats, processed_files)
    
    # Label별 예시 출력
    print_label_examples(stats)
    
    # 세션별 상세 분석 (Normal Label 분류 결과)
    print_separator("세션별 Normal Label 분류 상세 분석")
    print(f"총 {stats['total_sessions']:,}개 세션 분석\n")
    
    # Normal Label별 신뢰도 분포
    print("=" * 80)
    print("Normal Label별 신뢰도 분포")
    print("=" * 80)
    for label in sorted(stats['normal_labels'].keys()):
        count = stats['normal_labels'][label]
        avg_conf = stats['label_details'][label]['confidence_sum'] / count if count > 0 else 0
        
        # 해당 Label의 신뢰도 리스트 추출
        confidences = [
            ex['confidence'] for ex in stats['normal_label_examples'][label]
        ]
        if stats['confidence_stats']['normal']:
            # 전체 Normal Label 중에서 이 Label에 해당하는 것들 찾기
            label_confidences = [ex['confidence'] for ex in stats['label_details'][label]['examples']]
            if label_confidences:
                print(f"\n  {label}:")
                print(f"    개수: {count:,}개")
                print(f"    평균 신뢰도: {avg_conf:.3f}")
                print(f"    최소 신뢰도: {min(label_confidences):.3f}")
                print(f"    최대 신뢰도: {max(label_confidences):.3f}")
    
    # 최종 평가
    print_separator("최종 평가")
    total = stats['total_turns']
    normal_ratio = (stats['normal_count'] / total * 100) if total > 0 else 0
    
    print(f"총 Turn 수: {total:,}개")
    print(f"Normal Label 분류: {stats['normal_count']:,}개 ({normal_ratio:.2f}%)")
    print(f"Special Label 분류: {stats['special_count']:,}개 ({100 - normal_ratio:.2f}%)")
    print()
    
    if normal_ratio >= 80:
        print("[성공] 정상 발화 데이터셋이 Normal Label로 잘 분류되고 있습니다.")
    elif normal_ratio >= 60:
        print("[주의] Normal Label 분류 비율이 다소 낮습니다. 추가 검토가 필요할 수 있습니다.")
    else:
        print("[경고] Normal Label 분류 비율이 낮습니다. 분류 로직을 재검토해야 합니다.")
    
    # Summary 문서 생성
    from .generate_summaries import generate_normal_label_summary
    script_dir = Path(__file__).parent
    summary_path = script_dir / 'test_results' / 'normal_label_classification_analysis_v2.md'
    generate_normal_label_summary(stats, processed_files, summary_path)
    
    return stats


def main():
    """메인 함수"""
    # 현재 스크립트의 디렉토리 기준으로 경로 설정
    script_dir = Path(__file__).parent
    data_dir = script_dir / 'temp_extract_stt'
    
    if not data_dir.exists():
        print(f"❌ 데이터 디렉토리가 존재하지 않습니다: {data_dir}")
        return
    
    # 테스트 실행
    # 전체 데이터가 많을 수 있으므로 샘플 크기 지정 가능
    test_normal_label_classification(
        data_dir=data_dir,
        max_files=None,  # None이면 샘플링, 숫자를 지정하면 해당 개수만 처리
        sample_size=500  # 전체가 많을 경우 샘플 크기
    )


if __name__ == "__main__":
    main()

