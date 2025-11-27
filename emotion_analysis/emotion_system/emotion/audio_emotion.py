import torch
import torch.nn as nn
from .label_map import label_map

class CNNEmotionModel(nn.Module):
    def __init__(self, num_classes=7):  # 체크포인트는 7 클래스 기준
        super().__init__()
        self.conv1 = nn.Conv2d(1, 20, kernel_size=(3, 3), padding=1)
        self.conv2 = nn.Conv2d(20, 20, kernel_size=(3, 3), padding=1)
        self.conv3 = nn.Conv2d(20, 20, kernel_size=(3, 3), padding=1)
        self.pool = nn.MaxPool2d(2, 2)
        self.relu = nn.ReLU()

        # fc 레이어는 첫 forward에서 자동 초기화
        self.fc1 = None
        self.fc2 = None
        self.fc3 = None
        self.num_classes = num_classes

    def _initialize_fc_layers(self, x):
        """첫 forward에서 fc 레이어 크기를 자동으로 설정"""
        flatten_dim = x.view(x.size(0), -1).size(1)
        self.fc1 = nn.Linear(flatten_dim, 256)
        self.fc2 = nn.Linear(256, 128)
        self.fc3 = nn.Linear(128, self.num_classes)

    def forward(self, x):
        x = x.unsqueeze(1)  # [batch, 1, height, width]
        x = self.relu(self.conv1(x))
        x = self.pool(x)
        x = self.relu(self.conv2(x))
        x = self.pool(x)
        x = self.relu(self.conv3(x))
        x = self.pool(x)

        if self.fc1 is None:
            # 첫 forward에서 fc 레이어 초기화
            self._initialize_fc_layers(x)

        x = x.view(x.size(0), -1)
        x = self.relu(self.fc1(x))
        x = self.relu(self.fc2(x))
        return self.fc3(x)