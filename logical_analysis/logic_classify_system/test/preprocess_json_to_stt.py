"""
JSON 파일을 STT 표준 입력 형태로 전처리

temp_extract 폴더의 JSON 파일들을 읽어서
STT 표준 입력 형식으로 변환하여 저장
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Any
import re


def parse_consulting_content(content: str) -> List[Dict[str, Any]]:
    """
    consulting_content를 파싱하여 segments 리스트로 변환
    
    Args:
        content: "고객: ...\n상담사: ..." 형식의 텍스트
    
    Returns:
        segments 리스트: [{"speaker": "customer", "text": "...", "timestamp": None}, ...]
    """
    segments = []
    
    if not content:
        return segments
    
    # 고객과 상담사 발화를 분리
    # 패턴: "고객: ..." 또는 "상담사: ..."
    pattern = r'(고객|상담사)[:：]\s*(.+?)(?=(?:고객|상담사)[:：]|$)'
    matches = re.finditer(pattern, content, re.DOTALL)
    
    speaker_map = {
        "고객": "customer",
        "상담사": "agent"
    }
    
    segment_index = 0
    for match in matches:
        speaker_label = match.group(1)
        text = match.group(2).strip()
        
        # 빈 텍스트 제외
        if not text:
            continue
        
        # 여러 줄의 공백을 하나로 정리
        text = re.sub(r'\s+', ' ', text).strip()
        
        speaker = speaker_map.get(speaker_label, "unknown")
        
        segments.append({
            "speaker": speaker,
            "text": text,
            "start": segment_index * 2.0,  # 임시 타임스탬프 (초 단위)
            "end": (segment_index + 1) * 2.0
        })
        
        segment_index += 1
    
    return segments


def convert_json_to_stt_format(json_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    JSON 데이터를 STT 표준 입력 형식으로 변환
    
    Args:
        json_data: 원본 JSON 데이터
    
    Returns:
        STT 표준 입력 형식 딕셔너리
    """
    # session_id 생성 (source_id 사용)
    session_id = f"session_{json_data.get('source_id', 'unknown')}"
    
    # consulting_content 파싱
    consulting_content = json_data.get('consulting_content', '')
    segments = parse_consulting_content(consulting_content)
    
    # STT 표준 입력 형식 생성
    stt_data = {
        "session_id": session_id,
        "segments": segments,
        # 메타데이터 추가
        "metadata": {
            "source": json_data.get('source', ''),
            "source_id": json_data.get('source_id', ''),
            "consulting_category": json_data.get('consulting_category', ''),
            "consulting_turns": json_data.get('consulting_turns', ''),
            "consulting_length": json_data.get('consulting_length', '')
        }
    }
    
    return stt_data


def process_json_file(input_path: Path, output_dir: Path) -> Path:
    """
    단일 JSON 파일을 처리하여 STT 형식으로 저장
    
    Args:
        input_path: 입력 JSON 파일 경로
        output_dir: 출력 디렉토리 경로
    
    Returns:
        출력 파일 경로
    """
    # JSON 파일 읽기
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 리스트로 감싸진 경우 첫 번째 항목 사용
    if isinstance(data, list) and len(data) > 0:
        json_data = data[0]
    else:
        json_data = data
    
    # STT 형식으로 변환
    stt_data = convert_json_to_stt_format(json_data)
    
    # 출력 파일명 생성
    output_filename = input_path.stem.replace('_분류', '_stt') + '.json'
    output_path = output_dir / output_filename
    
    # 출력 디렉토리 생성
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # STT 형식으로 저장
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(stt_data, f, ensure_ascii=False, indent=2)
    
    return output_path


def process_directory(input_dir: Path, output_dir: Path) -> Dict[str, Any]:
    """
    디렉토리 내의 모든 JSON 파일을 처리
    
    Args:
        input_dir: 입력 디렉토리 경로
        output_dir: 출력 디렉토리 경로
    
    Returns:
        처리 결과 통계
    """
    # 출력 디렉토리 생성
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # JSON 파일 찾기
    json_files = list(input_dir.glob('*.json'))
    
    stats = {
        "total_files": len(json_files),
        "processed_files": 0,
        "failed_files": 0,
        "errors": []
    }
    
    print(f"총 {len(json_files)}개의 JSON 파일을 처리합니다...")
    
    for json_file in json_files:
        try:
            output_path = process_json_file(json_file, output_dir)
            stats["processed_files"] += 1
            print(f"✅ 처리 완료: {json_file.name} -> {output_path.name}")
        except Exception as e:
            stats["failed_files"] += 1
            stats["errors"].append({
                "file": json_file.name,
                "error": str(e)
            })
            print(f"❌ 처리 실패: {json_file.name} - {e}")
    
    return stats


def main():
    """메인 함수"""
    # 현재 스크립트의 디렉토리 기준으로 경로 설정
    script_dir = Path(__file__).parent
    input_dir = script_dir / 'temp_extract'
    output_dir = script_dir / 'temp_extract_stt'
    
    print("=" * 80)
    print("JSON 파일을 STT 표준 입력 형태로 전처리")
    print("=" * 80)
    print(f"입력 디렉토리: {input_dir}")
    print(f"출력 디렉토리: {output_dir}")
    print()
    
    if not input_dir.exists():
        print(f"❌ 입력 디렉토리가 존재하지 않습니다: {input_dir}")
        return
    
    # 디렉토리 처리
    stats = process_directory(input_dir, output_dir)
    
    # 결과 출력
    print()
    print("=" * 80)
    print("처리 완료")
    print("=" * 80)
    print(f"총 파일 수: {stats['total_files']}")
    print(f"처리 성공: {stats['processed_files']}")
    print(f"처리 실패: {stats['failed_files']}")
    
    if stats['errors']:
        print("\n오류 발생 파일:")
        for error in stats['errors']:
            print(f"  - {error['file']}: {error['error']}")
    
    print(f"\n출력 디렉토리: {output_dir}")


if __name__ == "__main__":
    main()

