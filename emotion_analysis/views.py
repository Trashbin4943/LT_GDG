from rest_framework.decorators import api_view
from rest_framework.response import Response
from emotion_system.emotion.unified_emotion import UnifiedEmotionAnalyzer
from emotion_system.preprocessing.stt_preprocessor import STTPreprocessor

@api_view(["POST"])
def analyze_emotion(request):
    analyzer = UnifiedEmotionAnalyzer()
    data = request.data

    if "text" in data:
        return Response(analyzer.analyze(text=data["text"]))
    elif "audio_path" in data:
        return Response(analyzer.analyze(audio_path=data["audio_path"]))
    elif "stt_data" in data:
        preprocessor = STTPreprocessor()
        turns = preprocessor.process(data["stt_data"], session_id="test123")
        results = [analyzer.analyze(turn=turn) for turn in turns]
        return Response(results)
    else:
        return Response({"error": "지원되지 않는 입력 형식"})