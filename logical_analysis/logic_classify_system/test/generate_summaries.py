"""
테스트 결과 Summary 문서 생성

두 테스트 결과를 각각 summary 문서로 생성
"""

import sys
from pathlib import Path
from datetime import datetime
import json

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from logical_analysis.logic_classify_system.config.labels import NORMAL_LABELS, SPECIAL_LABELS


def generate_normal_label_summary(stats: dict, total_files: int, output_path: Path) -> None:
    """Normal Label 분류 테스트 Summary 문서 생성"""
    total_turns = stats['total_turns']
    normal_ratio = (stats['normal_count'] / total_turns * 100) if total_turns > 0 else 0
    special_ratio = (stats['special_count'] / total_turns * 100) if total_turns > 0 else 0
    
    summary_lines = [
        "# 정상 발화 데이터셋 분류 테스트 분석 보고서 (v2)",
        "",
        f"**생성 일시**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**데이터셋**: temp_extract_stt (정상 발화 데이터셋)",
        f"**버전**: v2 (Special Label 요인 합산 방식 적용)",
        "",
        "**주요 변경사항**:",
        "- Special Label 신뢰도: korcen + baseline 규칙 요인들을 합산하여 계산",
        "- Normal Label 신뢰도 제거: 정상 발화로 판단하게 된 근거를 정량화하기 어려워 제거",
        "- Special Label 요인별 점수: 각 요인(`*_factor_score`)의 기여도 제공",
        "",
        "---",
        "",
        "## 📊 요약 통계",
        "",
        f"- **총 처리 파일 수**: {total_files:,}개",
        f"- **총 세션 수**: {stats.get('total_sessions', 0):,}개",
        f"- **총 Turn 수**: {total_turns:,}개",
        f"- **Normal Label 분류**: {stats['normal_count']:,}개 ({normal_ratio:.2f}%)",
        f"- **Special Label 분류**: {stats['special_count']:,}개 ({special_ratio:.2f}%)",
        "",
        "---",
        "",
        "## 📋 Normal Label 분포",
        "",
    ]
    
    # Normal Label 분포
    for label, count in stats['normal_labels'].most_common():
        ratio = (count / stats['normal_count'] * 100) if stats['normal_count'] > 0 else 0
        avg_confidence = (
            stats['label_details'][label]['confidence_sum'] / count
            if count > 0 else 0
        )
        summary_lines.extend([
            f"### {label}",
            "",
            f"- **개수**: {count:,}개 ({ratio:.2f}%)",
            f"- **평균 신뢰도**: {avg_confidence:.3f}",
            ""
        ])
        
        # 예시 추가
        examples = stats.get('normal_label_examples', {}).get(label, [])
        if examples:
            summary_lines.append("**분류 예시**:")
            summary_lines.append("")
            for i, ex in enumerate(examples, 1):
                summary_lines.extend([
                    f"{i}. **발화**: {ex['text']}",
                    f"   - **신뢰도**: {ex['confidence']:.3f}",
                ])
                if ex.get('probabilities'):
                    summary_lines.append(f"   - **확률 분포**: {ex['probabilities']}")
                if ex.get('feature_scores'):
                    # Special Label 신뢰도 (요인들 합산)
                    special_conf = ex['feature_scores'].get('special_label_confidence', 0.0)
                    if special_conf > 0:
                        summary_lines.append(f"   - **Special Label 신뢰도**: {special_conf:.3f}")
                        
                        # Special Label 요인별 점수
                        factor_scores = []
                        for factor_name in ['profanity_factor_score', 'threat_factor_score', 
                                          'sexual_harassment_factor_score', 'hate_speech_factor_score',
                                          'unreasonable_demand_factor_score', 'repetition_factor_score']:
                            factor_score = ex['feature_scores'].get(factor_name, 0.0)
                            if factor_score > 0:
                                factor_label = factor_name.replace('_factor_score', '').upper()
                                factor_scores.append(f"{factor_label}: {factor_score:.3f}")
                        
                        if factor_scores:
                            summary_lines.append(f"   - **Special Label 요인 점수**: {', '.join(factor_scores)}")
                summary_lines.append("")
            summary_lines.append("")
    
    # Special Label로 분류된 케이스
    special_examples = stats.get('special_label_examples', [])
    if special_examples:
        summary_lines.extend([
            "---",
            "",
            "## ⚠️ Normal Label로 분류되지 않은 케이스",
            "",
            f"총 **{len(special_examples)}개**의 케이스가 Special Label로 분류되었습니다.",
            "",
        ])
        
        for i, ex in enumerate(special_examples, 1):
            summary_lines.extend([
                f"### 케이스 {i}",
                "",
                f"- **세션 ID**: {ex['session_id']}",
                f"- **발화**: {ex['text']}",
                f"- **분류된 Label**: {ex['label']} ({ex.get('label_type', 'SPECIAL')})",
                f"- **신뢰도**: {ex['confidence']:.3f}",
                ""
            ])
            
            # 특징점 점수
            if ex.get('feature_scores'):
                summary_lines.append("**특징점 점수**:")
                feature_scores = ex['feature_scores']
                
                # Special Label 신뢰도 (요인들 합산)
                special_conf = feature_scores.get('special_label_confidence', 0.0)
                if special_conf > 0:
                    summary_lines.append(f"- Special Label 신뢰도 (요인 합산): {special_conf:.3f}")
                
                # Special Label 요인별 점수
                factor_scores = {}
                for factor_name in ['profanity_factor_score', 'threat_factor_score', 
                                  'sexual_harassment_factor_score', 'hate_speech_factor_score',
                                  'unreasonable_demand_factor_score', 'repetition_factor_score']:
                    factor_score = feature_scores.get(factor_name, 0.0)
                    if factor_score > 0:
                        factor_label = factor_name.replace('_factor_score', '').replace('_', ' ').title()
                        factor_scores[factor_label] = factor_score
                
                if factor_scores:
                    summary_lines.append("  **Special Label 요인별 기여도**:")
                    for factor_label, factor_score in sorted(factor_scores.items(), key=lambda x: x[1], reverse=True):
                        summary_lines.append(f"  - {factor_label}: {factor_score:.3f}")
                
                # 기타 특징점 점수
                other_scores = {}
                for key, value in feature_scores.items():
                    if value > 0 and key not in ['special_label_confidence'] and not key.endswith('_factor_score'):
                        other_scores[key] = value
                
                if other_scores:
                    summary_lines.append("  **기타 특징점 점수**:")
                    for key, value in sorted(other_scores.items(), key=lambda x: x[1], reverse=True):
                        summary_lines.append(f"  - {key}: {value:.3f}")
                
                summary_lines.append("")
            
            # 추출된 특징점
            if ex.get('extracted_features'):
                summary_lines.append("**추출된 특징점**:")
                for key, value in ex['extracted_features'].items():
                    if value:
                        if isinstance(value, list):
                            summary_lines.append(f"- {key}: {value[:3]}")
                        else:
                            summary_lines.append(f"- {key}: {value}")
                summary_lines.append("")
            
            if ex.get('probabilities'):
                summary_lines.append(f"**확률 분포**: {ex['probabilities']}")
                summary_lines.append("")
            
            summary_lines.append("")
    
    # 신뢰도 통계
    summary_lines.extend([
        "---",
        "",
        "## 📈 신뢰도 통계",
        "",
    ])
    
    if stats['confidence_stats']['normal']:
        normal_confidences = stats['confidence_stats']['normal']
        summary_lines.extend([
            "### Normal Label",
            "",
            f"- **평균 신뢰도**: {sum(normal_confidences) / len(normal_confidences):.3f}",
            f"- **최소 신뢰도**: {min(normal_confidences):.3f}",
            f"- **최대 신뢰도**: {max(normal_confidences):.3f}",
            "",
        ])
    
    if stats['confidence_stats']['special']:
        special_confidences = stats['confidence_stats']['special']
        summary_lines.extend([
            "### Special Label",
            "",
            f"- **평균 신뢰도**: {sum(special_confidences) / len(special_confidences):.3f}",
            f"- **최소 신뢰도**: {min(special_confidences):.3f}",
            f"- **최대 신뢰도**: {max(special_confidences):.3f}",
            "",
        ])
    
    # 최종 평가
    summary_lines.extend([
        "---",
        "",
        "## ✅ 최종 평가",
        "",
        f"**Normal Label 분류 비율**: {normal_ratio:.2f}%",
        "",
    ])
    
    if normal_ratio >= 80:
        summary_lines.append("✅ 정상 발화 데이터셋이 Normal Label로 잘 분류되고 있습니다.")
    elif normal_ratio >= 60:
        summary_lines.append("⚠️ Normal Label 분류 비율이 다소 낮습니다. 추가 검토가 필요할 수 있습니다.")
    else:
        summary_lines.append("❌ Normal Label 분류 비율이 낮습니다. 분류 로직을 재검토해야 합니다.")
    
    summary_lines.append("")
    
    # 파일 저장
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(summary_lines))
    
    print(f"[완료] Summary 문서 저장: {output_path}")


def generate_special_label_summary(stats: dict, total_files: int, output_path: Path) -> None:
    """Special Label 분류 테스트 Summary 문서 생성"""
    total_turns = stats['total_turns']
    normal_ratio = (stats['normal_count'] / total_turns * 100) if total_turns > 0 else 0
    special_ratio = (stats['special_count'] / total_turns * 100) if total_turns > 0 else 0
    
    summary_lines = [
        "# 문제 발화 데이터셋 Special Label 분류 테스트 분석 보고서 (v2)",
        "",
        f"**생성 일시**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**데이터셋**: talksets_stt (윤리 검증 데이터셋 - 문제 발화 비율 높음)",
        f"**버전**: v2 (Special Label 요인 합산 방식 적용)",
        "",
        "**주요 변경사항**:",
        "- Special Label 신뢰도: korcen + baseline 규칙 요인들을 합산하여 계산",
        "- 요인 개수 가중치: Special Label 요인이 많을수록 신뢰도 상승",
        "- Special Label 요인별 점수: 각 요인(`*_factor_score`)의 기여도 제공",
        "",
        "---",
        "",
        "## 📊 요약 통계",
        "",
        f"- **총 처리 파일 수**: {total_files:,}개",
        f"- **총 Turn 수**: {total_turns:,}개",
        f"- **Normal Label 분류**: {stats['normal_count']:,}개 ({normal_ratio:.2f}%)",
        f"- **Special Label 분류**: {stats['special_count']:,}개 ({special_ratio:.2f}%)",
        "",
        "---",
        "",
        "## 🚨 Special Label 상세 분포",
        "",
    ]
    
    # Special Label 상세 분포
    for label, count in stats['special_labels'].most_common():
        ratio = (count / stats['special_count'] * 100) if stats['special_count'] > 0 else 0
        avg_confidence = (
            stats['label_details'][label]['confidence_sum'] / count
            if count > 0 else 0
        )
        
        summary_lines.extend([
            f"### {label}",
            "",
            f"- **개수**: {count:,}개 ({ratio:.2f}%)",
            f"- **평균 신뢰도**: {avg_confidence:.3f}",
            ""
        ])
        
        # 특징점 점수 통계
        special_stats = stats.get('special_label_breakdown', {}).get(label, {})
        if special_stats and special_stats.get('count', 0) > 0:
            count_for_stats = special_stats['count']
            avg_profanity = special_stats['profanity_score_sum'] / count_for_stats if count_for_stats > 0 else 0
            avg_threat = special_stats['threat_score_sum'] / count_for_stats if count_for_stats > 0 else 0
            
            summary_lines.append("**평균 특징점 점수**:")
            summary_lines.append(f"- 욕설 점수: {avg_profanity:.3f}")
            summary_lines.append(f"- 위협 점수: {avg_threat:.3f}")
            
            # 각 특징점별 평균
            for feature_name, feature_values in special_stats.get('feature_stats', {}).items():
                if feature_values:
                    avg_value = sum(feature_values) / len(feature_values)
                    summary_lines.append(f"- {feature_name}: {avg_value:.3f}")
            summary_lines.append("")
            
            # 예시
            examples = special_stats.get('examples', [])
            if examples:
                summary_lines.append("**분류 예시**:")
                summary_lines.append("")
                for i, ex in enumerate(examples[:3], 1):  # 최대 3개
                    summary_lines.extend([
                        f"{i}. **발화**: {ex['text']}",
                        f"   - **신뢰도**: {ex['confidence']:.3f}",
                    ])
                    
                    # 특징점 점수
                    if ex.get('feature_scores'):
                        feature_scores = ex['feature_scores']
                        
                        # Special Label 신뢰도 (요인들 합산)
                        special_conf = feature_scores.get('special_label_confidence', 0.0)
                        if special_conf > 0:
                            summary_lines.append(f"   - **Special Label 신뢰도 (요인 합산)**: {special_conf:.3f}")
                        
                        # Special Label 요인별 점수
                        factor_scores = {}
                        for factor_name in ['profanity_factor_score', 'threat_factor_score', 
                                          'sexual_harassment_factor_score', 'hate_speech_factor_score',
                                          'unreasonable_demand_factor_score', 'repetition_factor_score']:
                            factor_score = feature_scores.get(factor_name, 0.0)
                            if factor_score > 0:
                                factor_label = factor_name.replace('_factor_score', '').replace('_', ' ').title()
                                factor_scores[factor_label] = factor_score
                        
                        if factor_scores:
                            summary_lines.append("   - **Special Label 요인별 기여도**:")
                            for factor_label, factor_score in sorted(factor_scores.items(), key=lambda x: x[1], reverse=True):
                                summary_lines.append(f"     - {factor_label}: {factor_score:.3f}")
                        
                        # 기타 특징점 점수
                        other_scores = {}
                        for key in ['profanity_score', 'threat_score', 'sexual_harassment_score', 
                                   'hate_speech_score', 'unreasonable_demand_score', 'repetition_keyword_score']:
                            if key in feature_scores and feature_scores[key] > 0:
                                other_scores[key] = feature_scores[key]
                        
                        if other_scores:
                            summary_lines.append("   - **기타 특징점 점수**:")
                            for key, value in sorted(other_scores.items(), key=lambda x: x[1], reverse=True):
                                summary_lines.append(f"     - {key}: {value:.3f}")
                    
                    # 추출된 특징점
                    if ex.get('extracted_features'):
                        summary_lines.append("   - **추출된 특징점**:")
                        for key, value in ex['extracted_features'].items():
                            if value:
                                if isinstance(value, list):
                                    summary_lines.append(f"     - {key}: {value[:2]}")
                                else:
                                    summary_lines.append(f"     - {key}: {value}")
                    
                    summary_lines.append("")
            summary_lines.append("")
    
    # Normal Label 분포 (간단히)
    if stats['normal_labels']:
        summary_lines.extend([
            "---",
            "",
            "## 📋 Normal Label 분포 (오분류 케이스)",
            "",
        ])
        for label, count in stats['normal_labels'].most_common():
            ratio = (count / stats['normal_count'] * 100) if stats['normal_count'] > 0 else 0
            summary_lines.append(f"- **{label}**: {count:,}개 ({ratio:.2f}%)")
        summary_lines.append("")
    
    # 신뢰도 통계
    summary_lines.extend([
        "---",
        "",
        "## 📈 신뢰도 통계",
        "",
    ])
    
    if stats['confidence_stats']['special']:
        special_confidences = stats['confidence_stats']['special']
        summary_lines.extend([
            "### Special Label",
            "",
            f"- **평균 신뢰도**: {sum(special_confidences) / len(special_confidences):.3f}",
            f"- **최소 신뢰도**: {min(special_confidences):.3f}",
            f"- **최대 신뢰도**: {max(special_confidences):.3f}",
            "",
        ])
    
    if stats['confidence_stats']['normal']:
        normal_confidences = stats['confidence_stats']['normal']
        summary_lines.extend([
            "### Normal Label (오분류)",
            "",
            f"- **평균 신뢰도**: {sum(normal_confidences) / len(normal_confidences):.3f}",
            f"- **최소 신뢰도**: {min(normal_confidences):.3f}",
            f"- **최대 신뢰도**: {max(normal_confidences):.3f}",
            "",
        ])
    
    # 최종 평가
    summary_lines.extend([
        "---",
        "",
        "## ✅ 최종 평가",
        "",
        f"**Special Label 분류 비율**: {special_ratio:.2f}%",
        f"**Normal Label 분류 비율**: {normal_ratio:.2f}%",
        "",
    ])
    
    if special_ratio >= 30:
        summary_lines.append("✅ 문제 발화 데이터셋이 Special Label로 잘 분류되고 있습니다.")
    elif special_ratio >= 15:
        summary_lines.append("⚠️ Special Label 분류 비율이 다소 낮습니다. 일부 문제 발화가 Normal로 분류되었을 수 있습니다.")
    else:
        summary_lines.append("❌ Special Label 분류 비율이 낮습니다. 분류 로직을 재검토해야 합니다.")
    
    summary_lines.append("")
    
    # 파일 저장
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(summary_lines))
    
    print(f"[완료] Summary 문서 저장: {output_path}")


def main():
    """메인 함수"""
    script_dir = Path(__file__).parent
    output_dir = script_dir / 'test_results'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("Summary 문서 생성 도구")
    print("테스트를 실행한 후 결과를 저장하세요.")


if __name__ == "__main__":
    main()

