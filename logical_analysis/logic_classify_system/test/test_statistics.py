"""
테스트 통계량 계산 및 문서화 유틸리티

각 테스트 결과를 분석 및 분류체계 분석에 사용할 수 있는
주요 척도와 통계량으로 변환
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict, Counter
from datetime import datetime


def calculate_classification_metrics(stats: Dict[str, Any]) -> Dict[str, Any]:
    """
    분류 성능 지표 계산
    
    Args:
        stats: 테스트 결과 통계
    
    Returns:
        분류 성능 지표 딕셔너리
    """
    total_turns = stats.get('total_turns', 0)
    if total_turns == 0:
        return {}
    
    normal_count = stats.get('normal_count', 0)
    special_count = stats.get('special_count', 0)
    
    metrics = {
        'total_turns': total_turns,
        'normal_count': normal_count,
        'special_count': special_count,
        'normal_ratio': (normal_count / total_turns * 100) if total_turns > 0 else 0,
        'special_ratio': (special_count / total_turns * 100) if total_turns > 0 else 0,
        'label_distribution': {
            'normal': dict(stats.get('normal_labels', Counter())),
            'special': dict(stats.get('special_labels', Counter()))
        },
        'confidence_statistics': {
            'normal': _calculate_confidence_stats(stats.get('confidence_stats', {}).get('normal', [])),
            'special': _calculate_confidence_stats(stats.get('confidence_stats', {}).get('special', []))
        },
        'special_label_confidence_stats': _calculate_special_label_confidence_stats(stats),
        'label_details': {}
    }
    
    # Label별 상세 통계
    label_details = stats.get('label_details', {})
    for label, details in label_details.items():
        count = details.get('count', 0)
        if count > 0:
            metrics['label_details'][label] = {
                'count': count,
                'ratio': (count / total_turns * 100) if total_turns > 0 else 0,
                'average_confidence': details.get('confidence_sum', 0.0) / count,
                'examples_count': len(details.get('examples', []))
            }
    
    return metrics


def calculate_validation_metrics(results: Dict[str, Any]) -> Dict[str, Any]:
    """
    정답지 기반 검증 성능 지표 계산
    
    Args:
        results: 검증 결과 통계
    
    Returns:
        검증 성능 지표 딕셔너리
    """
    total_segments = results.get('total_segments', 0)
    if total_segments == 0:
        return {}
    
    correct = results.get('correct_classifications', 0)
    incorrect = results.get('incorrect_classifications', 0)
    false_negatives = results.get('false_negatives', [])
    false_positives = results.get('false_positives', [])
    
    # Label 타입별 정확도
    label_type_accuracy = {}
    for label_type in ['NORMAL', 'SPECIAL']:
        stats = results.get('label_type_accuracy', {}).get(label_type, {})
        total = stats.get('total', 0)
        if total > 0:
            label_type_accuracy[label_type] = {
                'correct': stats.get('correct', 0),
                'total': total,
                'accuracy': (stats.get('correct', 0) / total * 100),
                'error_rate': ((total - stats.get('correct', 0)) / total * 100)
            }
    
    # Label별 정확도
    label_accuracy = {}
    for label, stats in results.get('label_accuracy', {}).items():
        total = stats.get('total', 0)
        if total > 0:
            label_accuracy[label] = {
                'correct': stats.get('correct', 0),
                'total': total,
                'accuracy': (stats.get('correct', 0) / total * 100),
                'error_rate': ((total - stats.get('correct', 0)) / total * 100)
            }
    
    metrics = {
        'total_segments': total_segments,
        'overall_accuracy': (correct / total_segments * 100) if total_segments > 0 else 0,
        'overall_error_rate': (incorrect / total_segments * 100) if total_segments > 0 else 0,
        'correct_classifications': correct,
        'incorrect_classifications': incorrect,
        'false_negatives_count': len(false_negatives),
        'false_positives_count': len(false_positives),
        'false_negative_rate': (len(false_negatives) / total_segments * 100) if total_segments > 0 else 0,
        'false_positive_rate': (len(false_positives) / total_segments * 100) if total_segments > 0 else 0,
        'label_type_accuracy': label_type_accuracy,
        'label_accuracy': label_accuracy,
        'confusion_matrix': {
            k: dict(v) for k, v in results.get('confusion_matrix', {}).items()
        }
    }
    
    return metrics


def calculate_feature_extraction_metrics(stats: Dict[str, Any]) -> Dict[str, Any]:
    """
    특징점 추출 성능 지표 계산
    
    Args:
        stats: 특징점 추출 결과 통계
    
    Returns:
        특징점 추출 성능 지표 딕셔너리
    """
    total_turns = stats.get('total_turns', 0)
    if total_turns == 0:
        return {}
    
    metrics = {
        'total_turns': total_turns,
        'feature_scores_statistics': {},
        'extracted_features_statistics': {},
        'label_feature_correlation': dict(stats.get('label_feature_correlation', {})),
        'feature_co_occurrence': {
            k: dict(v) for k, v in stats.get('feature_co_occurrence', {}).items()
        }
    }
    
    # 특징점 점수 통계
    feature_scores_stats = stats.get('feature_scores_stats', {})
    for feature_name, feature_stats in feature_scores_stats.items():
        count = feature_stats.get('count', 0)
        if count > 0:
            metrics['feature_scores_statistics'][feature_name] = {
                'detection_count': count,
                'detection_rate': (count / total_turns * 100) if total_turns > 0 else 0,
                'average_score': feature_stats.get('sum', 0.0) / count,
                'min_score': feature_stats.get('min', 0.0),
                'max_score': feature_stats.get('max', 0.0),
                'examples_count': len(feature_stats.get('examples', []))
            }
    
    # 추출된 특징점 통계
    extracted_features_stats = stats.get('extracted_features_stats', {})
    for feature_name, feature_stats in extracted_features_stats.items():
        count = feature_stats.get('count', 0)
        if count > 0:
            metrics['extracted_features_statistics'][feature_name] = {
                'detection_count': count,
                'detection_rate': (count / total_turns * 100) if total_turns > 0 else 0,
                'average_items_per_detection': (
                    feature_stats.get('total_items', 0) / count
                    if count > 0 else 0
                ),
                'total_items': feature_stats.get('total_items', 0),
                'examples_count': len(feature_stats.get('examples', []))
            }
    
    return metrics


def _calculate_confidence_stats(confidences: List[float]) -> Dict[str, float]:
    """신뢰도 통계 계산"""
    if not confidences:
        return {}
    
    return {
        'mean': sum(confidences) / len(confidences),
        'min': min(confidences),
        'max': max(confidences),
        'median': _calculate_median(confidences),
        'std': _calculate_std(confidences)
    }


def _calculate_median(values: List[float]) -> float:
    """중앙값 계산"""
    sorted_values = sorted(values)
    n = len(sorted_values)
    if n % 2 == 0:
        return (sorted_values[n//2 - 1] + sorted_values[n//2]) / 2
    else:
        return sorted_values[n//2]


def _calculate_std(values: List[float]) -> float:
    """표준편차 계산"""
    if len(values) < 2:
        return 0.0
    
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
    return variance ** 0.5


def _calculate_special_label_confidence_stats(stats: Dict[str, Any]) -> Dict[str, Any]:
    """Special Label 신뢰도 통계 계산 (요인 합산 신뢰도)"""
    special_label_confidences = []
    
    # Special Label로 분류된 케이스들의 special_label_confidence 수집
    special_examples = stats.get('special_label_examples', [])
    for ex in special_examples:
        if ex.get('feature_scores'):
            special_conf = ex['feature_scores'].get('special_label_confidence', 0.0)
            if special_conf > 0:
                special_label_confidences.append(special_conf)
    
    # session_details에서도 수집
    session_details = stats.get('session_details', [])
    for session in session_details:
        for turn in session.get('turns', []):
            if turn.get('label_type') == 'SPECIAL':
                feature_scores = turn.get('feature_scores', {})
                special_conf = feature_scores.get('special_label_confidence', 0.0)
                if special_conf > 0:
                    special_label_confidences.append(special_conf)
    
    if not special_label_confidences:
        return {}
    
    return {
        'mean': sum(special_label_confidences) / len(special_label_confidences),
        'min': min(special_label_confidences),
        'max': max(special_label_confidences),
        'median': _calculate_median(special_label_confidences),
        'std': _calculate_std(special_label_confidences),
        'count': len(special_label_confidences)
    }


def export_metrics_to_json(metrics: Dict[str, Any], output_path: Path) -> None:
    """
    통계량을 JSON 파일로 저장
    
    Args:
        metrics: 통계량 딕셔너리
        output_path: 출력 파일 경로
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)
    
    print(f"[저장 완료] 통계량 JSON: {output_path}")


def export_metrics_to_markdown(metrics: Dict[str, Any], output_path: Path, title: str = "통계량 보고서") -> None:
    """
    통계량을 Markdown 문서로 저장
    
    Args:
        metrics: 통계량 딕셔너리
        output_path: 출력 파일 경로
        title: 문서 제목
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    lines = [
        f"# {title}",
        "",
        f"**생성 일시**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "---",
        "",
        "## 📊 주요 통계량",
        "",
    ]
    
    # 주요 통계량 추가
    if 'total_turns' in metrics or 'total_segments' in metrics:
        total = metrics.get('total_turns') or metrics.get('total_segments', 0)
        lines.append(f"- **총 분석 단위**: {total:,}개")
        lines.append("")
    
    if 'overall_accuracy' in metrics:
        lines.extend([
            f"- **전체 정확도**: {metrics['overall_accuracy']:.2f}%",
            f"- **전체 오류율**: {metrics['overall_error_rate']:.2f}%",
            ""
        ])
    
    if 'normal_ratio' in metrics:
        lines.extend([
            f"- **Normal Label 비율**: {metrics['normal_ratio']:.2f}%",
            f"- **Special Label 비율**: {metrics['special_ratio']:.2f}%",
            ""
        ])
    
    # 상세 통계량 추가 (JSON 형태로)
    lines.extend([
        "---",
        "",
        "## 📈 상세 통계량",
        "",
        "```json",
        json.dumps(metrics, ensure_ascii=False, indent=2),
        "```",
        ""
    ])
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    print(f"[저장 완료] 통계량 Markdown: {output_path}")

