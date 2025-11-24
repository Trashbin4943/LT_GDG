"""
특징점 추출 메커니즘 검증 테스트

발화 데이터셋을 활용하여 다양한 특징점 추출 메커니즘이
올바르게 동작하는지 검증
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict, Counter

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


def analyze_feature_extraction(results: List[Any]) -> Dict[str, Any]:
    """특징점 추출 분석"""
    stats = {
        'total_turns': 0,
        'feature_scores_stats': defaultdict(lambda: {
            'count': 0,
            'sum': 0.0,
            'min': float('inf'),
            'max': float('-inf'),
            'examples': []  # 높은 점수와 낮은 점수 예시
        }),
        'extracted_features_stats': defaultdict(lambda: {
            'count': 0,
            'total_items': 0,
            'examples': []
        }),
        'label_feature_correlation': defaultdict(lambda: defaultdict(float)),  # Label별 특징점 점수 평균
        'feature_co_occurrence': defaultdict(lambda: defaultdict(int)),  # 특징점 동시 발생
    }
    
    for result in results:
        turn_results = result.turn_results if hasattr(result, 'turn_results') else []
        
        for turn_result in turn_results:
            customer_result = turn_result.customer_result
            label = customer_result.classification_result.label
            label_type = customer_result.classification_result.label_type
            text = customer_result.text
            feature_scores = customer_result.feature_scores
            extracted_features = customer_result.extracted_features
            
            stats['total_turns'] += 1
            
            # 특징점 점수 통계 수집
            active_features = []
            for feature_name, feature_value in feature_scores.items():
                if isinstance(feature_value, (int, float)) and feature_value > 0:
                    active_features.append(feature_name)
                    
                    feature_stats = stats['feature_scores_stats'][feature_name]
                    feature_stats['count'] += 1
                    feature_stats['sum'] += feature_value
                    feature_stats['min'] = min(feature_stats['min'], feature_value)
                    feature_stats['max'] = max(feature_stats['max'], feature_value)
                    
                    # Label별 특징점 점수 누적
                    stats['label_feature_correlation'][label][feature_name] += feature_value
                    
                    # 예시 저장 (높은 점수와 낮은 점수)
                    if len(feature_stats['examples']) < 5:
                        feature_stats['examples'].append({
                            'text': text[:100],
                            'score': feature_value,
                            'label': label,
                            'label_type': label_type
                        })
            
            # 특징점 동시 발생 분석
            if len(active_features) > 1:
                for i, feat1 in enumerate(active_features):
                    for feat2 in active_features[i+1:]:
                        stats['feature_co_occurrence'][feat1][feat2] += 1
                        stats['feature_co_occurrence'][feat2][feat1] += 1
            
            # 추출된 특징점 통계 수집
            for feature_name, feature_value in extracted_features.items():
                feature_stats = stats['extracted_features_stats'][feature_name]
                feature_stats['count'] += 1
                
                if isinstance(feature_value, list):
                    feature_stats['total_items'] += len(feature_value)
                    if len(feature_stats['examples']) < 3:
                        feature_stats['examples'].append({
                            'text': text[:100],
                            'items': feature_value[:5]  # 최대 5개
                        })
                elif feature_value:
                    feature_stats['total_items'] += 1
                    if len(feature_stats['examples']) < 3:
                        feature_stats['examples'].append({
                            'text': text[:100],
                            'value': feature_value
                        })
    
    # Label별 특징점 점수 평균 계산
    label_feature_avg = {}
    for label, feature_sums in stats['label_feature_correlation'].items():
        label_feature_avg[label] = {}
        # 해당 Label의 Turn 수 계산 (간단히)
        for feature_name in feature_sums.keys():
            feature_stats = stats['feature_scores_stats'][feature_name]
            if feature_stats['count'] > 0:
                # 해당 Label에서의 평균은 전체 평균으로 대체 (정확한 계산은 복잡)
                label_feature_avg[label][feature_name] = feature_sums[feature_name] / max(1, feature_stats['count'])
    
    stats['label_feature_correlation'] = label_feature_avg
    
    return stats


def print_feature_extraction_statistics(stats: Dict[str, Any]):
    """특징점 추출 통계 출력"""
    print(f"총 Turn 수: {stats['total_turns']:,}개")
    print()
    
    # 특징점 점수 통계
    print_separator("특징점 점수 통계")
    
    feature_names = sorted(stats['feature_scores_stats'].keys())
    for feature_name in feature_names:
        feature_stats = stats['feature_scores_stats'][feature_name]
        if feature_stats['count'] == 0:
            continue
        
        avg_score = feature_stats['sum'] / feature_stats['count']
        print(f"\n[{feature_name}]")
        print(f"  감지된 Turn 수: {feature_stats['count']:,}개 ({feature_stats['count'] / stats['total_turns'] * 100:.2f}%)")
        print(f"  평균 점수: {avg_score:.3f}")
        print(f"  최소 점수: {feature_stats['min']:.3f}")
        print(f"  최대 점수: {feature_stats['max']:.3f}")
        
        # 예시 출력
        if feature_stats['examples']:
            print(f"  예시:")
            for i, ex in enumerate(feature_stats['examples'][:3], 1):
                print(f"    {i}. [{ex['label']}] {ex['text']}... (점수: {ex['score']:.3f})")
    
    # 추출된 특징점 통계
    print_separator("추출된 특징점 통계")
    
    for feature_name in sorted(stats['extracted_features_stats'].keys()):
        feature_stats = stats['extracted_features_stats'][feature_name]
        if feature_stats['count'] == 0:
            continue
        
        avg_items = feature_stats['total_items'] / feature_stats['count'] if feature_stats['count'] > 0 else 0
        print(f"\n[{feature_name}]")
        print(f"  감지된 Turn 수: {feature_stats['count']:,}개")
        print(f"  평균 추출 항목 수: {avg_items:.2f}개")
        
        # 예시 출력
        if feature_stats['examples']:
            print(f"  예시:")
            for i, ex in enumerate(feature_stats['examples'][:2], 1):
                print(f"    {i}. {ex['text']}...")
                if 'items' in ex:
                    print(f"       추출 항목: {ex['items']}")
                elif 'value' in ex:
                    print(f"       추출 값: {ex['value']}")
    
    # Label별 특징점 점수 상관관계
    print_separator("Label별 특징점 점수 상관관계")
    
    for label in sorted(stats['label_feature_correlation'].keys()):
        label_type = "SPECIAL" if label in SPECIAL_LABELS else "NORMAL"
        print(f"\n[{label}] ({label_type})")
        feature_scores = stats['label_feature_correlation'][label]
        if feature_scores:
            for feature_name in sorted(feature_scores.keys(), key=lambda x: feature_scores[x], reverse=True):
                score = feature_scores[feature_name]
                if score > 0:
                    print(f"  {feature_name}: {score:.3f}")
    
    # 특징점 동시 발생 분석
    print_separator("특징점 동시 발생 분석")
    
    co_occurrence_pairs = []
    for feat1, feat2_dict in stats['feature_co_occurrence'].items():
        for feat2, count in feat2_dict.items():
            if feat1 < feat2:  # 중복 제거
                co_occurrence_pairs.append((feat1, feat2, count))
    
    co_occurrence_pairs.sort(key=lambda x: x[2], reverse=True)
    
    if co_occurrence_pairs:
        print("가장 자주 함께 발생하는 특징점 쌍:")
        for feat1, feat2, count in co_occurrence_pairs[:10]:
            print(f"  {feat1} + {feat2}: {count}회")
    else:
        print("동시 발생 패턴이 없습니다.")


def test_feature_extraction(
    data_dir: Path,
    max_files: int = None,
    sample_size: int = 100
):
    """
    특징점 추출 메커니즘 검증 테스트
    
    Args:
        data_dir: STT 데이터 파일이 있는 디렉토리
        max_files: 최대 처리할 파일 수 (None이면 모두 처리)
        sample_size: 샘플 크기 (전체 데이터가 많을 경우)
    """
    print_separator("특징점 추출 메커니즘 검증 테스트")
    
    # STT 파일 목록 가져오기
    stt_files = sorted(data_dir.glob('*.json'))
    
    if not stt_files:
        print(f"[오류] STT 파일을 찾을 수 없습니다: {data_dir}")
        return
    
    print(f"발견된 STT 파일 수: {len(stt_files)}")
    
    # 샘플링
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
            
            # 진행 상황 출력
            if i % 50 == 0:
                print(f"  진행 상황: {i}/{len(stt_files)} 파일 처리 완료")
        
        except Exception as e:
            failed_files += 1
            if failed_files <= 5:
                print(f"  [오류] 오류 발생 ({stt_file.name}): {e}")
            continue
    
    print()
    print(f"처리 완료: {processed_files:,}개 성공, {failed_files:,}개 실패")
    print()
    
    if not all_results:
        print("[오류] 처리된 결과가 없습니다.")
        return
    
    # 특징점 추출 분석
    stats = analyze_feature_extraction(all_results)
    
    # 결과 출력
    print_feature_extraction_statistics(stats)
    
    return stats


def main():
    """메인 함수"""
    script_dir = Path(__file__).parent
    
    # 여러 데이터셋에서 테스트 가능
    # 1. 정상 발화 데이터셋
    print("=" * 80)
    print("정상 발화 데이터셋 특징점 추출 검증")
    print("=" * 80)
    normal_data_dir = script_dir / 'temp_extract_stt'
    if normal_data_dir.exists():
        test_feature_extraction(
            data_dir=normal_data_dir,
            max_files=None,
            sample_size=200
        )
    else:
        print(f"[건너뜀] 데이터 디렉토리가 없습니다: {normal_data_dir}")
    
    print("\n" + "=" * 80 + "\n")
    
    # 2. 문제 발화 데이터셋
    print("=" * 80)
    print("문제 발화 데이터셋 특징점 추출 검증")
    print("=" * 80)
    special_data_dir = script_dir / 'talksets_stt'
    if special_data_dir.exists():
        test_feature_extraction(
            data_dir=special_data_dir,
            max_files=None,
            sample_size=200
        )
    else:
        print(f"[건너뜀] 데이터 디렉토리가 없습니다: {special_data_dir}")


if __name__ == "__main__":
    main()

