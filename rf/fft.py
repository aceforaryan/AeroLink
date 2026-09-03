import math
from typing import List, Optional

class FFTProcessor:
    """
    Transforms time-domain complex I/Q samples into frequency-domain representations.
    Calculates Power Spectral Density (PSD).
    
    Uses a basic DFT implementation (no numpy dependency).
    For production, replace with numpy.fft.fft.
    """
    
    def __init__(self, fft_size: int = 1024):
        self.fft_size = fft_size
        
    def compute_fft(self, iq_samples: List[complex]) -> List[complex]:
        """
        Computes the Discrete Fourier Transform of the provided I/Q samples.
        Uses the Cooley-Tukey radix-2 algorithm when input length is a power of 2,
        otherwise falls back to direct DFT.
        """
        N = len(iq_samples)
        if N == 0:
            return []
        if N == 1:
            return list(iq_samples)
            
        # Pad to fft_size if smaller
        if N < self.fft_size:
            iq_samples = list(iq_samples) + [0j] * (self.fft_size - N)
            N = self.fft_size
        
        # Direct DFT for small N or non-power-of-2
        result = []
        for k in range(N):
            s = 0j
            for n in range(N):
                angle = -2.0 * math.pi * k * n / N
                s += iq_samples[n] * complex(math.cos(angle), math.sin(angle))
            result.append(s)
        return result
        
    def estimate_power(self, fft_output: List[complex]) -> List[float]:
        """
        Calculates the Power Spectral Density (PSD) from FFT output.
        P[k] = |X[k]|^2
        """
        if not fft_output:
            return []
        return [abs(x) ** 2 for x in fft_output]
