import librosa
import numpy as np

def extract_features(file_path):
    y, sr = librosa.load(file_path, sr=16000)
    # MFCC 추출 (2D 특징)
    mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=40)
    # 길이 맞추기 (예: 128 프레임)
    if mfccs.shape[1] > 128:
        mfccs = mfccs[:, :128]
    else:
        pad_width = 128 - mfccs.shape[1]
        mfccs = np.pad(mfccs, ((0, 0), (0, pad_width)), mode="constant")
    # 정규화
    mfccs = (mfccs - np.mean(mfccs)) / np.std(mfccs)
    return mfccs[np.newaxis, :, :]  # [1, height, width]
