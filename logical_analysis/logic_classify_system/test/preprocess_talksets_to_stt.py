"""
talksets-train 파일을 STT 표준 입력 형태로 전처리

윤리 검증 데이터셋인 talksets-train 파일들을 읽어서
STT 표준 입력 형식으로 변환하여 저장
"""

import json
from pathlib import Path
from typing import List, Dict, Any
import uuid


def parse_talksets_data(talksets_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    talksets 데이터를 STT 표준 형식으로 변환
    
    Args:
        talksets_data: talksets 원본 데이터
                      형식: [{"id": "...", "sentences": [{"speaker": 1, "text": "...", ...}, ...]}, ...]
    
    Returns:
        STT 표준 형식 딕셔너리 리스트
    """
    stt_results = []
    
    for talk_item in talksets_data:
        talk_id = talk_item.get('id', str(uuid.uuid4()))
        sentences = talk_item.get('sentences', [])
        
        if not sentences:
            continue
        
        # segments 생성
        segments = []
        segment_index = 0
        
        for sentence in sentences:
            speaker_num = sentence.get('speaker', 1)
            text = sentence.get('text', '').strip()
            
            # 빈 텍스트 제외
            if not text:
                continue
            
            # speaker 번호를 화자 라벨로 변환
            # 1: customer (손님), 2: agent (상담원)
            speaker = "customer" if speaker_num == 1 else "agent"
            
            # 타임스탬프 생성 (문장 순서대로 2초 간격)
            start_time = segment_index * 2.0
            end_time = (segment_index + 1) * 2.0
            
            segments.append({
                "speaker": speaker,
                "text": text,
                "start": start_time,
                "end": end_time
            })
            
            segment_index += 1
        
        if not segments:
            continue
        
        # STT 표준 형식 생성
        stt_data = {
            "session_id": f"session_{talk_id}",
            "segments": segments,
            "metadata": {
                "source": "talksets-train",
                "talk_id": talk_id,
                "total_sentences": len(sentences),
                "immoral_count": sum(1 for s in sentences if s.get('is_immoral', False))
            }
        }
        
        stt_results.append(stt_data)
    
    return stt_results


def process_talksets_file(input_path: Path, output_dir: Path) -> int:
    """
    단일 talksets 파일을 처리하여 STT 형식으로 저장
    
    Args:
        input_path: 입력 talksets 파일 경로
        output_dir: 출력 디렉토리 경로
    
    Returns:
        처리된 대화 수
    """
    print(f"처리 중: {input_path.name}")
    
    # JSON 파일 읽기
    with open(input_path, 'r', encoding='utf-8') as f:
        talksets_data = json.load(f)
    
    # 리스트가 아닌 경우 리스트로 변환
    if not isinstance(talksets_data, list):
        talksets_data = [talksets_data]
    
    # STT 형식으로 변환
    stt_results = parse_talksets_data(talksets_data)
    
    if not stt_results:
        print(f"  [경고] 처리된 대화가 없습니다.")
        return 0
    
    # 출력 디렉토리 생성
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 각 대화를 개별 파일로 저장
    saved_count = 0
    for stt_data in stt_results:
        talk_id = stt_data['session_id'].replace('session_', '')
        output_filename = f"talksets_stt_{talk_id}.json"
        output_path = output_dir / output_filename
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(stt_data, f, ensure_ascii=False, indent=2)
            saved_count += 1
        except Exception as e:
            print(f"  [오류] 파일 저장 실패 ({output_filename}): {e}")
    
    print(f"  [완료] 처리 완료: {saved_count}개 대화 저장")
    return saved_count


def process_talksets_directory(input_dir: Path, output_dir: Path) -> Dict[str, Any]:
    """
    디렉토리 내의 모든 talksets 파일을 처리
    
    Args:
        input_dir: 입력 디렉토리 경로
        output_dir: 출력 디렉토리 경로
    
    Returns:
        처리 결과 통계
    """
    # 출력 디렉토리 생성
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # talksets-train 파일 찾기
    talksets_files = list(input_dir.glob('talksets-train*.json'))
    
    stats = {
        "total_files": len(talksets_files),
        "processed_files": 0,
        "failed_files": 0,
        "total_conversations": 0,
        "errors": []
    }
    
    if not talksets_files:
        print(f"[경고] talksets-train 파일을 찾을 수 없습니다: {input_dir}")
        return stats
    
    print(f"총 {len(talksets_files)}개의 talksets 파일을 처리합니다...")
    print()
    
    for talksets_file in talksets_files:
        try:
            conversation_count = process_talksets_file(talksets_file, output_dir)
            stats["processed_files"] += 1
            stats["total_conversations"] += conversation_count
        except Exception as e:
            stats["failed_files"] += 1
            stats["errors"].append({
                "file": talksets_file.name,
                "error": str(e)
            })
            print(f"[오류] 처리 실패: {talksets_file.name} - {e}")
    
    return stats


def main():
    """메인 함수"""
    # 현재 스크립트의 디렉토리 기준으로 경로 설정
    script_dir = Path(__file__).parent
    input_dir = script_dir  # test 디렉토리에서 직접 찾기
    output_dir = script_dir / 'talksets_stt'
    
    print("=" * 80)
    print("talksets-train 파일을 STT 표준 입력 형태로 전처리")
    print("=" * 80)
    print(f"입력 디렉토리: {input_dir}")
    print(f"출력 디렉토리: {output_dir}")
    print()
    
    if not input_dir.exists():
        print(f"[오류] 입력 디렉토리가 존재하지 않습니다: {input_dir}")
        return
    
    # 디렉토리 처리
    stats = process_talksets_directory(input_dir, output_dir)
    
    # 결과 출력
    print()
    print("=" * 80)
    print("처리 완료")
    print("=" * 80)
    print(f"총 파일 수: {stats['total_files']}")
    print(f"처리 성공: {stats['processed_files']}")
    print(f"처리 실패: {stats['failed_files']}")
    print(f"총 대화 수: {stats['total_conversations']:,}")
    
    if stats['errors']:
        print("\n오류 발생 파일:")
        for error in stats['errors'][:10]:  # 최대 10개만 출력
            print(f"  - {error['file']}: {error['error']}")
    
    print(f"\n출력 디렉토리: {output_dir}")


if __name__ == "__main__":
    main()

