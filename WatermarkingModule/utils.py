import numpy as np
from scipy.fftpack import dct, idct
import cv2

def rgb2ycbcr(img_bgr):
    img = img_bgr.astype(np.float32)
    B, G, R = img[:, :, 0], img[:, :, 1], img[:, :, 2]
    Y  = 0.299 * R + 0.587 * G + 0.114 * B
    Cb = 128 + (B - Y) / 2
    Cr = 128 + (R - Y) / 1.6
    return Y, Cb, Cr

def ycbcr2bgr(Y, Cb, Cr):
    B = (Cb - 128) * 2   + Y
    R = (Cr - 128) * 1.6 + Y
    G = (Y - 0.299 * R - 0.114 * B) / 0.587
    img = np.stack([B, G, R], axis=-1)
    return np.clip(img, 0, 255).astype(np.uint8)

def dct2(block):
    return dct(dct(block.T, norm='ortho').T, norm='ortho')

def idct2(block):
    return idct(idct(block.T, norm='ortho').T, norm='ortho')

def zigzag_indices(n=8):
    idxs = []
    for s in range(2 * n - 1):
        if s % 2 == 0:
            for i in range(s + 1):
                j = s - i
                if i < n and j < n: idxs.append((i, j))
        else:
            for j in range(s + 1):
                i = s - j
                if i < n and j < n: idxs.append((i, j))
    return idxs

def bytes_to_bits(data: bytes) -> np.ndarray:
    bits = []
    for byte in data:
        for i in range(8)[::-1]:
            bits.append((byte >> i) & 1)
    return np.array(bits, dtype=np.uint8)

def bits_to_bytes(bits: np.ndarray) -> bytes:
    out = bytearray()
    for i in range(0, bits.size, 8):
        byte = 0
        for j in range(8):
            if i + j < bits.size:
                byte = (byte << 1) | int(bits[i + j])
        out.append(byte)
    return bytes(out)

def majority_vote_bits(reps):
    sums = reps.sum(axis=0)
    return (sums > (reps.shape[0] / 2)).astype(np.uint8)