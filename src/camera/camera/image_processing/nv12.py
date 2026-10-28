import cv2
import numpy as np


def nv12_to_bgr(frame, width, height):
    """Convert a packed NV12 byte buffer to an HxWx3 uint8 BGR array."""
    if frame is None:
        return None
    raw = np.frombuffer(frame, dtype=np.uint8)
    required = int(width) * int(height) * 3 // 2
    if width <= 0 or height <= 0 or width % 2 or height % 2:
        raise ValueError('NV12宽高必须为正偶数')
    if raw.size != required:
        raise ValueError(f'NV12帧长度不匹配: {raw.size} != {required}，需检查分辨率或行对齐')
    nv12 = raw[:required].reshape((int(height) * 3 // 2, int(width)))
    return cv2.cvtColor(nv12, cv2.COLOR_YUV2BGR_NV12)
