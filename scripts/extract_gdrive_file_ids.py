"""
Google Drive 공유 링크에서 파일 ID 또는 폴더 ID 추출

사용법:
    python scripts/extract_gdrive_file_ids.py <공유_링크>
    python scripts/extract_gdrive_file_ids.py "https://drive.google.com/file/d/1a2b3c4d5e6f7g8h9i0j/view?usp=sharing"
"""
import re
import sys
from urllib.parse import urlparse, parse_qs


def extract_file_id(url: str) -> str:
    """공유 링크에서 파일 ID 추출"""
    # 여러 패턴 시도
    patterns = [
        r'/file/d/([a-zA-Z0-9_-]+)',  # /file/d/FILE_ID/view
        r'/folders/([a-zA-Z0-9_-]+)',  # /folders/FOLDER_ID
        r'[?&]id=([a-zA-Z0-9_-]+)',    # ?id=FILE_ID
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    # URL 파라미터에서 id 찾기
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    if 'id' in params:
        return params['id'][0]
    
    return None


def extract_folder_id(url: str) -> str:
    """폴더 링크에서 폴더 ID 추출"""
    patterns = [
        r'/folders/([a-zA-Z0-9_-]+)',
        r'[?&]id=([a-zA-Z0-9_-]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None


def get_type_and_id(url: str) -> tuple:
    """URL 타입 (file/folder)과 ID 추출"""
    if '/file/d/' in url:
        file_id = extract_file_id(url)
        return ('file', file_id)
    elif '/folders/' in url or '/drive/folders/' in url:
        folder_id = extract_folder_id(url)
        return ('folder', folder_id)
    else:
        # 일반적인 ID 추출 시도
        id_value = extract_file_id(url)
        return ('unknown', id_value)


def main():
    """메인 함수"""
    if len(sys.argv) < 2:
        print("=" * 60)
        print("Google Drive 파일/폴더 ID 추출 도구")
        print("=" * 60)
        print("\n사용법:")
        print("  python scripts/extract_gdrive_file_ids.py <공유_링크>")
        print("\n예시:")
        print('  python scripts/extract_gdrive_file_ids.py "https://drive.google.com/file/d/1a2b3c4d5e6f7g8h9i0j/view?usp=sharing"')
        print('  python scripts/extract_gdrive_file_ids.py "https://drive.google.com/drive/folders/1a2b3c4d5e6f7g8h9i0j?usp=sharing"')
        print("\n매니페스트 형식:")
        print("-" * 60)
        print('  "source": {')
        print('    "type": "gdrive",')
        print('    "file_id": "추출된_ID"')
        print('  }')
        sys.exit(0)
    
    url = sys.argv[1]
    
    print("=" * 60)
    print("Google Drive ID 추출")
    print("=" * 60)
    print(f"\n입력 URL: {url}")
    print()
    
    url_type, id_value = get_type_and_id(url)
    
    if id_value:
        print("✓ ID 추출 성공!")
        print("-" * 60)
        print(f"타입: {url_type}")
        print(f"ID:   {id_value}")
        print()
        
        # 매니페스트 형식 출력
        print("매니페스트 형식:")
        print("-" * 60)
        if url_type == 'file':
            print('  "source": {')
            print('    "type": "gdrive",')
            print(f'    "file_id": "{id_value}"')
            print('  }')
            print()
            print('또는 공유 링크 직접 사용:')
            print('  "source": {')
            print('    "type": "gdrive_url",')
            print(f'    "url": "{url}"')
            print('  }')
        elif url_type == 'folder':
            print('  "gdrive_folder_id": "' + id_value + '"')
            print()
            print('또는 폴더 내 특정 파일:')
            print('  "source": {')
            print('    "type": "gdrive",')
            print('    "file_id": "폴더_내_파일_ID"  # 폴더 내 각 파일의 ID 필요')
            print('  }')
        else:
            print('  "source": {')
            print('    "type": "gdrive",')
            print(f'    "file_id": "{id_value}"')
            print('  }')
    else:
        print("✗ ID를 추출할 수 없습니다.")
        print()
        print("확인 사항:")
        print("  1. 공유 링크가 올바른지 확인")
        print("  2. 링크 형식 확인:")
        print("     - 파일: https://drive.google.com/file/d/FILE_ID/view?usp=sharing")
        print("     - 폴더: https://drive.google.com/drive/folders/FOLDER_ID?usp=sharing")
        sys.exit(1)


if __name__ == "__main__":
    main()

