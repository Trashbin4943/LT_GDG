"""
모델 파일 검증 스크립트

모델 파일이 올바르게 다운로드되었는지 확인합니다.

사용법:
    python scripts/verify_models.py
    python scripts/verify_models.py intensity_regression
"""
import json
import os
import sys
import hashlib
from pathlib import Path
from typing import Dict, List, Tuple


class ModelVerifier:
    """모델 파일 검증 클래스"""
    
    def __init__(self, manifest_path: str = "models_manifest.json"):
        """
        Args:
            manifest_path: 모델 매니페스트 파일 경로
        """
        manifest_file = Path(manifest_path)
        if not manifest_file.exists():
            raise FileNotFoundError(
                f"매니페스트 파일을 찾을 수 없습니다: {manifest_path}"
            )
        
        with open(manifest_file, 'r', encoding='utf-8') as f:
            self.manifest = json.load(f)
    
    def calculate_md5(self, filepath: str) -> str:
        """파일의 MD5 체크섬 계산"""
        md5_hash = hashlib.md5()
        try:
            with open(filepath, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    md5_hash.update(chunk)
            return md5_hash.hexdigest()
        except Exception as e:
            raise RuntimeError(f"파일 읽기 실패: {e}")
    
    def verify_file(self, filepath: str, file_info: Dict) -> Tuple[bool, str]:
        """
        파일 검증
        
        Returns:
            (is_valid, message) 튜플
        """
        if not os.path.exists(filepath):
            return False, "파일이 존재하지 않음"
        
        # 파일 크기 확인
        actual_size = os.path.getsize(filepath)
        expected_size = file_info.get('size')
        if expected_size and actual_size != expected_size:
            return False, f"크기 불일치 (예상: {expected_size}, 실제: {actual_size})"
        
        # MD5 체크섬 검증
        expected_md5 = file_info.get('md5')
        if expected_md5:
            try:
                actual_md5 = self.calculate_md5(filepath)
                if actual_md5.lower() != expected_md5.lower():
                    return False, f"체크섬 불일치 (예상: {expected_md5}, 실제: {actual_md5})"
            except Exception as e:
                return False, f"체크섬 계산 실패: {e}"
        
        return True, "정상"
    
    def verify_model(self, model_name: str) -> Tuple[bool, Dict]:
        """
        특정 모델 검증
        
        Returns:
            (all_valid, results) 튜플
            results: {filename: (is_valid, message, size_mb)} 딕셔너리
        """
        if model_name not in self.manifest['models']:
            return False, {}
        
        model_info = self.manifest['models'][model_name]
        base_path = Path(model_info['base_path'])
        
        results = {}
        all_valid = True
        
        for file_info in model_info['files']:
            filename = file_info['filename']
            filepath = base_path / filename
            
            is_valid, message = self.verify_file(str(filepath), file_info)
            
            size_mb = 0
            if os.path.exists(filepath):
                size_mb = os.path.getsize(filepath) / (1024 * 1024)
            
            results[filename] = {
                'valid': is_valid,
                'message': message,
                'size_mb': size_mb
            }
            
            if not is_valid:
                all_valid = False
        
        return all_valid, results
    
    def verify_all(self) -> Tuple[bool, Dict]:
        """
        모든 모델 검증
        
        Returns:
            (all_valid, all_results) 튜플
        """
        all_valid = True
        all_results = {}
        
        for model_name in self.manifest['models']:
            model_valid, results = self.verify_model(model_name)
            all_results[model_name] = {
                'valid': model_valid,
                'files': results
            }
            
            if not model_valid:
                all_valid = False
        
        return all_valid, all_results


def print_verification_results(model_name: str, results: Dict, verbose: bool = False):
    """검증 결과 출력"""
    print(f"\n[{model_name}]")
    print("-" * 60)
    
    valid_count = 0
    invalid_count = 0
    
    for filename, file_result in results.items():
        is_valid = file_result['valid']
        message = file_result['message']
        size_mb = file_result['size_mb']
        
        if is_valid:
            status = "✓"
            color_code = ""
            print(f"  {status} {filename:40s} ({size_mb:8.2f} MB) {message}")
            valid_count += 1
        else:
            status = "✗"
            color_code = ""
            print(f"  {status} {filename:40s} - {message}")
            invalid_count += 1
            if verbose:
                print(f"      세부 정보: {message}")
    
    print(f"  결과: 정상 {valid_count}, 문제 {invalid_count}")
    
    return valid_count, invalid_count


def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='모델 파일 검증 스크립트',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  python scripts/verify_models.py                    # 모든 모델 검증
  python scripts/verify_models.py intensity_regression  # 특정 모델만
        """
    )
    
    parser.add_argument(
        'model_name',
        nargs='?',
        help='검증할 모델 이름 (지정하지 않으면 모든 모델)'
    )
    
    parser.add_argument(
        '--manifest',
        default='models_manifest.json',
        help='매니페스트 파일 경로 (기본값: models_manifest.json)'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='상세 정보 출력'
    )
    
    args = parser.parse_args()
    
    try:
        verifier = ModelVerifier(args.manifest)
        
        print("=" * 60)
        print("모델 파일 검증")
        print("=" * 60)
        print(f"매니페스트 버전: {verifier.manifest.get('version', 'unknown')}")
        print(f"마지막 업데이트: {verifier.manifest.get('last_updated', 'unknown')}")
        
        if args.model_name:
            # 특정 모델만 검증
            all_valid, results = verifier.verify_model(args.model_name)
            print_verification_results(args.model_name, results, args.verbose)
        else:
            # 모든 모델 검증
            all_valid, all_results = verifier.verify_all()
            
            total_valid = 0
            total_invalid = 0
            
            for model_name, model_result in all_results.items():
                valid_count, invalid_count = print_verification_results(
                    model_name,
                    model_result['files'],
                    args.verbose
                )
                total_valid += valid_count
                total_invalid += invalid_count
        
        print("\n" + "=" * 60)
        if all_valid:
            print("✓ 모든 모델 파일이 정상입니다.")
            if not args.model_name:
                print(f"  총 {total_valid}개 파일 검증 완료")
        else:
            print("✗ 일부 모델 파일에 문제가 있습니다.")
            if not args.model_name:
                print(f"  정상: {total_valid}, 문제: {total_invalid}")
            print("\n  다음 명령어로 모델을 다운로드하세요:")
            if args.model_name:
                print(f"    python scripts/download_models.py {args.model_name}")
            else:
                print(f"    python scripts/download_models.py")
        print("=" * 60)
        
        sys.exit(0 if all_valid else 1)
    
    except FileNotFoundError as e:
        print(f"✗ 오류: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"✗ 예상치 못한 오류: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

