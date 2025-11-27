'''
음성 파일에서 음향 특징 추출
pitch, energy, spectral centroid, ZCR, speech rate, MFCC 평균값
딕셔너리 형태로 모델에 입력됩니다.
'''

import librosa
import numpy as np

def extract_features(file_path):
    y, sr = librosa.load(file_path, sr=16000)
    pitches, magnitudes = librosa.piptrack(y=y, sr=sr)
    pitch = np.mean(pitches[pitches > 0]) if np.any(pitches > 0) else 0
    energy = np.mean(librosa.feature.rms(y=y))
    mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
    mfccs_mean = np.mean(mfccs.T, axis=0)
    spec_centroid = np.mean(librosa.feature.spectral_centroid(y=y, sr=sr))
    zcr = np.mean(librosa.feature.zero_crossing_rate(y))
    duration = librosa.get_duration(y=y, sr=sr)
    speech_rate = len(librosa.effects.split(y)) / duration

    feature_vector = np.array([pitch, energy, spec_centroid, zcr, speech_rate, *mfccs_mean])
    return feature_vector.reshape(1, 1, -1)  # LSTM 입력 형태
