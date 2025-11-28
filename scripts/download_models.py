"""
모델 파일 다운로드 및 검증 스크립트

사용법:
    python scripts/download_models.py                    # 모든 모델 다운로드
    python scripts/download_models.py intensity_regression  # 특정 모델만 다운로드
"""
import json
import os
import sys
import hashlib
from pathlib import Path
from typing import Dict, List, Optional

try:
    import boto3
    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False
    print("⚠ boto3가 설치되지 않았습니다. S3 다운로드를 사용할 수 없습니다.")

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    print("⚠ requests가 설치되지 않았습니다. URL 다운로드를 사용할 수 없습니다.")

try:
    import gdown
    HAS_GDOWN = True
except ImportError:
    HAS_GDOWN = False
    print("⚠ gdown이 설치되지 않았습니다. Google Drive 다운로드를 사용할 수 없습니다. (pip install gdown)")


class ModelDownloader:
    """모델 파일 다운로드 및 검증 클래스"""
    
    def __init__(self, manifest_path: str = "models_manifest.json"):
        """
        Args:
            manifest_path: 모델 매니페스트 파일 경로
        """
        manifest_file = Path(manifest_path)
        if not manifest_file.exists():
            raise FileNotFoundError(
                f"매니페스트 파일을 찾을 수 없습니다: {manifest_path}\n"
                "models_manifest.json.example을 참고하여 생성하세요."
            )
        
        with open(manifest_file, 'r', encoding='utf-8') as f:
            self.manifest = json.load(f)
        
        self.manifest_path = manifest_path
    
    def calculate_md5(self, filepath: str) -> str:
        """파일의 MD5 체크섬 계산"""
        md5_hash = hashlib.md5()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                md5_hash.update(chunk)
        return md5_hash.hexdigest()
    
    def verify_file(self, filepath: str, expected_md5: str) -> bool:
        """파일 존재 여부 및 체크섬 검증"""
        if not os.path.exists(filepath):
            return False
        
        try:
            actual_md5 = self.calculate_md5(filepath)
            return actual_md5.lower() == expected_md5.lower()
        except Exception as e:
            print(f"  ⚠ 검증 중 오류 발생: {e}")
            return False
    
    def download_from_s3(self, bucket: str, key: str, destination: str):
        """S3에서 파일 다운로드"""
        if not HAS_BOTO3:
            raise ImportError("boto3가 필요합니다. pip install boto3")
        
        s3 = boto3.client('s3')
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        
        print(f"  다운로드 중: s3://{bucket}/{key}")
        try:
            s3.download_file(bucket, key, destination)
        except Exception as e:
            raise RuntimeError(f"S3 다운로드 실패: {e}")
    
    def download_from_url(self, url: str, destination: str):
        """URL에서 파일 다운로드"""
        if not HAS_REQUESTS:
            raise ImportError("requests가 필요합니다. pip install requests")
        
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        
        print(f"  다운로드 중: {url}")
        try:
            response = requests.get(url, stream=True, timeout=300)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(destination, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            print(f"\r  진행률: {percent:.1f}%", end='')
            
            print()  # 줄바꿈
        except Exception as e:
            if os.path.exists(destination):
                os.remove(destination)
            raise RuntimeError(f"URL 다운로드 실패: {e}")
    
    def download_from_gdrive(self, file_id: str, destination: str, is_folder: bool = False):
        """Google Drive에서 파일 다운로드 (gdown 사용)"""
        if not HAS_GDOWN:
            raise ImportError("gdown이 필요합니다. pip install gdown")
        
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        
        # Google Drive 파일 URL 생성
        if is_folder:
            # 폴더의 경우 zip으로 다운로드
            url = f"https://drive.google.com/uc?id={file_id}"
            # 임시 zip 파일로 다운로드
            zip_path = destination + ".zip"
            print(f"  다운로드 중 (폴더): gdrive file_id={file_id}")
            gdown.download_folder(url, output=os.path.dirname(destination), quiet=False, use_cookies=False)
        else:
            # 개별 파일 다운로드
            url = f"https://drive.google.com/uc?id={file_id}"
            print(f"  다운로드 중: gdrive file_id={file_id}")
            gdown.download(url, destination, quiet=False)
    
    def download_from_gdrive_url(self, share_url: str, destination: str):
        """Google Drive 공유 링크에서 파일 다운로드"""
        if not HAS_GDOWN:
            raise ImportError("gdown이 필요합니다. pip install gdown")
        
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        
        print(f"  다운로드 중: {share_url}")
        try:
            # gdown은 공유 링크에서 파일 ID를 자동 추출
            gdown.download(share_url, destination, quiet=False, fuzzy=True)
        except Exception as e:
            if os.path.exists(destination):
                os.remove(destination)
            raise RuntimeError(f"Google Drive 다운로드 실패: {e}")
    
    def download_file(self, file_info: Dict, destination: str) -> bool:
        """파일 다운로드 (소스 타입에 따라 자동 선택)"""
        source = file_info.get('source', {})
        source_type = source.get('type', 'unknown')
        
        try:
            if source_type == 's3':
                self.download_from_s3(
                    source['bucket'],
                    source['key'],
                    destination
                )
            elif source_type == 'url':
                self.download_from_url(
                    source['url'],
                    destination
                )
            elif source_type == 'gdrive':
                # Google Drive 파일 ID 사용
                file_id = source.get('file_id')
                is_folder = source.get('is_folder', False)
                if file_id:
                    self.download_from_gdrive(file_id, destination, is_folder)
                else:
                    raise ValueError("gdrive 타입에는 file_id가 필요합니다")
            elif source_type == 'gdrive_url':
                # Google Drive 공유 링크 사용
                share_url = source.get('url')
                if share_url:
                    self.download_from_gdrive_url(share_url, destination)
                else:
                    raise ValueError("gdrive_url 타입에는 url이 필요합니다")
            elif source_type == 'local':
                # 로컬 파일 복사 (개발/테스트용)
                local_path = source.get('path')
                if local_path and os.path.exists(local_path):
                    os.makedirs(os.path.dirname(destination), exist_ok=True)
                    import shutil
                    shutil.copy2(local_path, destination)
                    print(f"  복사됨: {local_path}")
                else:
                    raise FileNotFoundError(f"로컬 파일을 찾을 수 없습니다: {local_path}")
            else:
                raise ValueError(f"지원하지 않는 소스 타입: {source_type}")
            
            return True
        except Exception as e:
            print(f"  ✗ 다운로드 실패: {e}")
            if os.path.exists(destination):
                os.remove(destination)
            return False
    
    def download_model(self, model_name: str, skip_existing: bool = True) -> bool:
        """특정 모델 다운로드"""
        if model_name not in self.manifest['models']:
            print(f"✗ 모델을 찾을 수 없습니다: {model_name}")
            print(f"  사용 가능한 모델: {', '.join(self.manifest['models'].keys())}")
            return False
        
        model_info = self.manifest['models'][model_name]
        base_path = Path(model_info['base_path'])
        
        print(f"\n[{model_name}] 모델 다운로드 중...")
        print(f"  대상 경로: {base_path}")
        
        success_count = 0
        skip_count = 0
        fail_count = 0
        
        for file_info in model_info['files']:
            filename = file_info['filename']
            filepath = base_path / filename
            
            # 파일이 이미 존재하고 검증이 통과하면 건너뜀
            if skip_existing:
                expected_md5 = file_info.get('md5')
                if expected_md5 and self.verify_file(str(filepath), expected_md5):
                    size_mb = os.path.getsize(filepath) / (1024 * 1024)
                    print(f"  ✓ {filename} 이미 존재하고 검증됨 ({size_mb:.2f} MB)")
                    skip_count += 1
                    continue
            
            # 파일 다운로드
            print(f"  → {filename} ({file_info.get('size', 0) / (1024*1024):.2f} MB)")
            if self.download_file(file_info, str(filepath)):
                # 검증
                expected_md5 = file_info.get('md5')
                if expected_md5:
                    if self.verify_file(str(filepath), expected_md5):
                        print(f"  ✓ {filename} 다운로드 및 검증 완료")
                        success_count += 1
                    else:
                        print(f"  ✗ {filename} 검증 실패!")
                        if os.path.exists(filepath):
                            os.remove(filepath)
                        fail_count += 1
                else:
                    print(f"  ✓ {filename} 다운로드 완료 (검증 스킵)")
                    success_count += 1
            else:
                fail_count += 1
        
        # 결과 요약
        print(f"\n  결과: 성공 {success_count}, 건너뜀 {skip_count}, 실패 {fail_count}")
        
        return fail_count == 0
    
    def download_all(self, skip_existing: bool = True) -> bool:
        """모든 모델 다운로드"""
        print("=" * 60)
        print("모델 파일 다운로드 시작")
        print("=" * 60)
        print(f"매니페스트 버전: {self.manifest.get('version', 'unknown')}")
        print(f"마지막 업데이트: {self.manifest.get('last_updated', 'unknown')}")
        print()
        
        all_success = True
        for model_name in self.manifest['models']:
            try:
                success = self.download_model(model_name, skip_existing)
                if not success:
                    all_success = False
            except Exception as e:
                print(f"✗ {model_name} 다운로드 중 오류: {e}")
                all_success = False
        
        print("\n" + "=" * 60)
        if all_success:
            print("✓ 모든 모델 다운로드 완료")
        else:
            print("✗ 일부 모델 다운로드 실패")
        print("=" * 60)
        
        return all_success


def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='모델 파일 다운로드 스크립트',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  python scripts/download_models.py                    # 모든 모델 다운로드
  python scripts/download_models.py intensity_regression  # 특정 모델만
  python scripts/download_models.py --force            # 기존 파일 재다운로드
        """
    )
    
    parser.add_argument(
        'model_name',
        nargs='?',
        help='다운로드할 모델 이름 (지정하지 않으면 모든 모델)'
    )
    
    parser.add_argument(
        '--manifest',
        default='models_manifest.json',
        help='매니페스트 파일 경로 (기본값: models_manifest.json)'
    )
    
    parser.add_argument(
        '--force',
        action='store_true',
        help='기존 파일이 있어도 재다운로드'
    )
    
    args = parser.parse_args()
    
    try:
        downloader = ModelDownloader(args.manifest)
        
        if args.model_name:
            # 특정 모델만 다운로드
            success = downloader.download_model(
                args.model_name,
                skip_existing=not args.force
            )
        else:
            # 모든 모델 다운로드
            success = downloader.download_all(
                skip_existing=not args.force
            )
        
        sys.exit(0 if success else 1)
    
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

