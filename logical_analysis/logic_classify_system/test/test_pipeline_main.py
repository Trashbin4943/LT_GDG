"""
테스트 파이프라인 메인

모든 테스트를 순차적으로 실행하고 결과를 수집하여 통계량을 문서화
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 테스트 모듈 import
from logical_analysis.logic_classify_system.test.test_normal_label_classification import (
    test_normal_label_classification
)
from logical_analysis.logic_classify_system.test.test_special_label_classification import (
    test_special_label_classification
)
from logical_analysis.logic_classify_system.test.test_with_ground_truth import (
    test_with_ground_truth
)
from logical_analysis.logic_classify_system.test.test_feature_extraction import (
    test_feature_extraction,
    analyze_feature_extraction
)
from logical_analysis.logic_classify_system.test.test_statistics import (
    calculate_classification_metrics,
    calculate_validation_metrics,
    calculate_feature_extraction_metrics,
    export_metrics_to_json,
    export_metrics_to_markdown
)
from logical_analysis.logic_classify_system.test.test_helpers import create_test_pipeline


def run_normal_label_test(
    data_dir: Path,
    output_dir: Path,
    sample_size: int = 500,
    verbose: bool = True
) -> Optional[Dict[str, Any]]:
    """
    Normal Label 분류 테스트 실행
    
    Args:
        data_dir: STT 데이터 디렉토리
        output_dir: 출력 디렉토리
        sample_size: 샘플 크기
        verbose: 상세 출력 여부
    
    Returns:
        테스트 통계량 딕셔너리
    """
    if not data_dir.exists():
        if verbose:
            print(f"[건너뜀] 데이터 디렉토리가 없습니다: {data_dir}")
        return None
    
    if verbose:
        print("\n" + "=" * 80)
        print("테스트 1: Normal Label 분류 테스트")
        print("=" * 80)
    
    try:
        stats = test_normal_label_classification(
            data_dir=data_dir,
            max_files=None,
            sample_size=sample_size
        )
        
        if stats:
            # 통계량 계산
            metrics = calculate_classification_metrics(stats)
            
            # JSON 저장
            json_path = output_dir / 'metrics' / 'normal_label_metrics_v2.json'
            export_metrics_to_json(metrics, json_path)
            
            # Markdown 저장
            md_path = output_dir / 'metrics' / 'normal_label_metrics_v2.md'
            export_metrics_to_markdown(metrics, md_path, "Normal Label 분류 통계량 보고서 (v2)")
            
            return {
                'test_name': 'normal_label_classification',
                'stats': stats,
                'metrics': metrics,
                'timestamp': datetime.now().isoformat()
            }
    except Exception as e:
        if verbose:
            print(f"[오류] Normal Label 테스트 실패: {e}")
        return None
    
    return None


def run_special_label_test(
    data_dir: Path,
    output_dir: Path,
    sample_size: int = 500,
    verbose: bool = True
) -> Optional[Dict[str, Any]]:
    """
    Special Label 분류 테스트 실행
    
    Args:
        data_dir: STT 데이터 디렉토리
        output_dir: 출력 디렉토리
        sample_size: 샘플 크기
        verbose: 상세 출력 여부
    
    Returns:
        테스트 통계량 딕셔너리
    """
    if not data_dir.exists():
        if verbose:
            print(f"[건너뜀] 데이터 디렉토리가 없습니다: {data_dir}")
        return None
    
    if verbose:
        print("\n" + "=" * 80)
        print("테스트 2: Special Label 분류 테스트")
        print("=" * 80)
    
    try:
        stats = test_special_label_classification(
            data_dir=data_dir,
            max_files=None,
            sample_size=sample_size
        )
        
        if stats:
            # 통계량 계산
            metrics = calculate_classification_metrics(stats)
            
            # JSON 저장
            json_path = output_dir / 'metrics' / 'special_label_metrics_v2.json'
            export_metrics_to_json(metrics, json_path)
            
            # Markdown 저장
            md_path = output_dir / 'metrics' / 'special_label_metrics_v2.md'
            export_metrics_to_markdown(metrics, md_path, "Special Label 분류 통계량 보고서 (v2)")
            
            return {
                'test_name': 'special_label_classification',
                'stats': stats,
                'metrics': metrics,
                'timestamp': datetime.now().isoformat()
            }
    except Exception as e:
        if verbose:
            print(f"[오류] Special Label 테스트 실패: {e}")
        return None
    
    return None


def run_ground_truth_test(
    talksets_file: Path,
    output_dir: Path,
    sample_size: int = 500,
    verbose: bool = True
) -> Optional[Dict[str, Any]]:
    """
    정답지 기반 검증 테스트 실행
    
    Args:
        talksets_file: talksets 원본 파일
        output_dir: 출력 디렉토리
        sample_size: 샘플 크기
        verbose: 상세 출력 여부
    
    Returns:
        테스트 통계량 딕셔너리
    """
    if not talksets_file.exists():
        if verbose:
            print(f"[건너뜀] talksets 파일이 없습니다: {talksets_file}")
        return None
    
    if verbose:
        print("\n" + "=" * 80)
        print("테스트 3: 정답지 기반 검증 테스트")
        print("=" * 80)
    
    try:
        from logical_analysis.logic_classify_system.test.test_with_ground_truth import (
            create_ground_truth_dataset,
            validate_with_ground_truth,
            print_validation_results
        )
        
        # 정답지 데이터셋 생성
        gt_output_dir = output_dir / 'ground_truth_validation'
        stt_data_list, ground_truth_list = create_ground_truth_dataset(
            talksets_file=talksets_file,
            sample_size=sample_size,
            output_dir=gt_output_dir
        )
        
        if not stt_data_list or not ground_truth_list:
            if verbose:
                print("[오류] 정답지 데이터셋 생성 실패")
            return None
        
        # 검증 실행
        results = validate_with_ground_truth(stt_data_list, ground_truth_list)
        
        if verbose:
            print_validation_results(results)
        
        if results:
            # 통계량 계산
            metrics = calculate_validation_metrics(results)
            
            # JSON 저장
            json_path = output_dir / 'metrics' / 'ground_truth_metrics_v2.json'
            export_metrics_to_json(metrics, json_path)
            
            # Markdown 저장
            md_path = output_dir / 'metrics' / 'ground_truth_metrics_v2.md'
            export_metrics_to_markdown(metrics, md_path, "정답지 기반 검증 통계량 보고서 (v2)")
            
            return {
                'test_name': 'ground_truth_validation',
                'results': results,
                'metrics': metrics,
                'timestamp': datetime.now().isoformat()
            }
    except Exception as e:
        if verbose:
            print(f"[오류] 정답지 기반 검증 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    return None


def run_feature_extraction_test(
    data_dir: Path,
    output_dir: Path,
    sample_size: int = 200,
    verbose: bool = True
) -> Optional[Dict[str, Any]]:
    """
    특징점 추출 테스트 실행
    
    Args:
        data_dir: STT 데이터 디렉토리
        output_dir: 출력 디렉토리
        sample_size: 샘플 크기
        verbose: 상세 출력 여부
    
    Returns:
        테스트 통계량 딕셔너리
    """
    if not data_dir.exists():
        if verbose:
            print(f"[건너뜀] 데이터 디렉토리가 없습니다: {data_dir}")
        return None
    
    if verbose:
        print("\n" + "=" * 80)
        print("테스트 4: 특징점 추출 테스트")
        print("=" * 80)
    
    try:
        from logical_analysis.logic_classify_system.test.test_feature_extraction import (
            load_stt_file,
            analyze_feature_extraction
        )
        from logical_analysis.logic_classify_system.pipeline.main_pipeline import MainPipeline
        
        # STT 파일 목록 가져오기
        stt_files = sorted(data_dir.glob('*.json'))
        
        if not stt_files:
            if verbose:
                print(f"[오류] STT 파일을 찾을 수 없습니다: {data_dir}")
            return None
        
        # 샘플링
        if len(stt_files) > sample_size:
            import random
            stt_files = random.sample(stt_files, sample_size)
        
        # MainPipeline 초기화
        pipeline = create_test_pipeline(use_models=True)
        
        # 결과 저장
        all_results = []
        processed_files = 0
        
        if verbose:
            print(f"처리할 파일 수: {len(stt_files)}")
            print("파일 처리 중...")
        
        for i, stt_file in enumerate(stt_files, 1):
            try:
                stt_data = load_stt_file(stt_file)
                result = pipeline.process(stt_data)
                all_results.append(result)
                processed_files += 1
                
                if verbose and i % 50 == 0:
                    print(f"  진행 상황: {i}/{len(stt_files)} 파일 처리 완료")
            except Exception as e:
                if verbose and processed_files == 0:
                    print(f"  [오류] 오류 발생 ({stt_file.name}): {e}")
                continue
        
        if not all_results:
            if verbose:
                print("[오류] 처리된 결과가 없습니다.")
            return None
        
        # 특징점 추출 분석
        stats = analyze_feature_extraction(all_results)
        
        if stats:
            # 통계량 계산
            metrics = calculate_feature_extraction_metrics(stats)
            
            # JSON 저장
            json_path = output_dir / 'metrics' / 'feature_extraction_metrics_v2.json'
            export_metrics_to_json(metrics, json_path)
            
            # Markdown 저장
            md_path = output_dir / 'metrics' / 'feature_extraction_metrics_v2.md'
            export_metrics_to_markdown(metrics, md_path, "특징점 추출 통계량 보고서 (v2)")
            
            return {
                'test_name': 'feature_extraction',
                'stats': stats,
                'metrics': metrics,
                'timestamp': datetime.now().isoformat()
            }
    except Exception as e:
        if verbose:
            print(f"[오류] 특징점 추출 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    return None


def run_all_tests(
    script_dir: Path,
    output_dir: Path = None,
    sample_sizes: Dict[str, int] = None,
    verbose: bool = True
) -> Dict[str, Any]:
    """
    모든 테스트 실행
    
    Args:
        script_dir: 스크립트 디렉토리 (테스트 파일들이 있는 곳)
        output_dir: 출력 디렉토리 (None이면 script_dir/test_results 사용)
        sample_sizes: 각 테스트별 샘플 크기
        verbose: 상세 출력 여부
    
    Returns:
        모든 테스트 결과 딕셔너리
    """
    if output_dir is None:
        output_dir = script_dir / 'test_results'
    
    if sample_sizes is None:
        sample_sizes = {
            'normal': 500,
            'special': 500,
            'ground_truth': 500,
            'feature_extraction': 200
        }
    
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / 'metrics').mkdir(parents=True, exist_ok=True)
    
    if verbose:
        print("=" * 80)
        print("전체 테스트 파이프라인 실행")
        print("=" * 80)
        print(f"출력 디렉토리: {output_dir}")
        print()
    
    all_results = {
        'timestamp': datetime.now().isoformat(),
        'tests': {},
        'summary': {}
    }
    
    # 테스트 1: Normal Label 분류
    normal_data_dir = script_dir / 'temp_extract_stt'
    normal_result = run_normal_label_test(
        data_dir=normal_data_dir,
        output_dir=output_dir,
        sample_size=sample_sizes.get('normal', 500),
        verbose=verbose
    )
    if normal_result:
        all_results['tests']['normal_label_classification'] = normal_result
    
    # 테스트 2: Special Label 분류
    special_data_dir = script_dir / 'talksets_stt'
    special_result = run_special_label_test(
        data_dir=special_data_dir,
        output_dir=output_dir,
        sample_size=sample_sizes.get('special', 500),
        verbose=verbose
    )
    if special_result:
        all_results['tests']['special_label_classification'] = special_result
    
    # 테스트 3: 정답지 기반 검증
    talksets_file = script_dir / 'talksets-train-6.json'
    ground_truth_result = run_ground_truth_test(
        talksets_file=talksets_file,
        output_dir=output_dir,
        sample_size=sample_sizes.get('ground_truth', 500),
        verbose=verbose
    )
    if ground_truth_result:
        all_results['tests']['ground_truth_validation'] = ground_truth_result
    
    # 테스트 4: 특징점 추출
    feature_data_dir = script_dir / 'talksets_stt'  # 또는 다른 데이터셋
    feature_result = run_feature_extraction_test(
        data_dir=feature_data_dir,
        output_dir=output_dir,
        sample_size=sample_sizes.get('feature_extraction', 200),
        verbose=verbose
    )
    if feature_result:
        all_results['tests']['feature_extraction'] = feature_result
    
    # 요약 통계 생성
    if verbose:
        print("\n" + "=" * 80)
        print("테스트 요약")
        print("=" * 80)
    
    summary = {
        'total_tests': len(all_results['tests']),
        'completed_tests': list(all_results['tests'].keys()),
        'test_results': {}
    }
    
    for test_name, test_result in all_results['tests'].items():
        if 'metrics' in test_result:
            metrics = test_result['metrics']
            
            # 주요 지표 추출
            if 'overall_accuracy' in metrics:
                summary['test_results'][test_name] = {
                    'overall_accuracy': metrics['overall_accuracy'],
                    'overall_error_rate': metrics.get('overall_error_rate', 0)
                }
            elif 'normal_ratio' in metrics:
                summary['test_results'][test_name] = {
                    'normal_ratio': metrics['normal_ratio'],
                    'special_ratio': metrics.get('special_ratio', 0)
                }
    
    all_results['summary'] = summary
    
    # 전체 결과 저장
    results_path = output_dir / 'all_test_results_v2.json'
    export_metrics_to_json(all_results, results_path)
    
    # 요약 Markdown 생성
    summary_md_path = output_dir / 'test_summary_v2.md'
    summary_lines = [
        "# 전체 테스트 요약 (v2)",
        "",
        f"**생성 일시**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**버전**: v2 (Special Label 요인 합산 방식 적용)",
        "",
        "---",
        "",
        "## 📊 테스트 결과 요약",
        "",
        f"- **총 테스트 수**: {summary['total_tests']}개",
        f"- **완료된 테스트**: {', '.join(summary['completed_tests'])}",
        "",
        "---",
        "",
        "## 📈 테스트별 주요 지표",
        ""
    ]
    
    for test_name, test_metrics in summary['test_results'].items():
        summary_lines.append(f"### {test_name}")
        summary_lines.append("")
        for key, value in test_metrics.items():
            if isinstance(value, float):
                summary_lines.append(f"- **{key}**: {value:.2f}%")
            else:
                summary_lines.append(f"- **{key}**: {value}")
        summary_lines.append("")
    
    summary_lines.extend([
        "---",
        "",
        "## 📁 상세 결과",
        "",
        "각 테스트의 상세 통계량은 다음 파일들을 참조하세요:",
        "",
        "- `metrics/normal_label_metrics_v2.json`",
        "- `metrics/special_label_metrics_v2.json`",
        "- `metrics/ground_truth_metrics_v2.json`",
        "- `metrics/feature_extraction_metrics_v2.json`",
        "",
        "전체 결과: `all_test_results_v2.json`",
        "",
        "---",
        "",
        "## 🔄 주요 변경사항 (v2)",
        "",
        "- **Special Label 신뢰도 계산 방식 변경**: korcen + baseline 규칙 요인들을 합산하여 신뢰도 계산",
        "- **Normal Label 신뢰도 제거**: 정상 발화로 판단하게 된 근거를 정량화하기 어려워 제거",
        "- **Special Label 요인별 점수 추가**: `special_label_confidence`와 각 요인별 기여도(`*_factor_score`) 제공",
        "- **요인 개수 가중치**: Special Label 요인이 많을수록 신뢰도 상승",
        ""
    ])
    
    with open(summary_md_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(summary_lines))
    
    if verbose:
        print(f"\n[완료] 전체 결과 저장: {results_path}")
        print(f"[완료] 요약 문서 저장: {summary_md_path}")
    
    return all_results


def main():
    """메인 함수"""
    script_dir = Path(__file__).parent
    output_dir = script_dir / 'test_results'
    
    # 샘플 크기 설정
    sample_sizes = {
        'normal': 500,
        'special': 500,
        'ground_truth': 500,
        'feature_extraction': 200
    }
    
    # 모든 테스트 실행
    results = run_all_tests(
        script_dir=script_dir,
        output_dir=output_dir,
        sample_sizes=sample_sizes,
        verbose=True
    )
    
    print("\n" + "=" * 80)
    print("테스트 파이프라인 실행 완료")
    print("=" * 80)


if __name__ == "__main__":
    main()

