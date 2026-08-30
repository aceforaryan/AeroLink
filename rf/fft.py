class FFTProcessor:
    """
    Transforms time-domain complex I/Q samples into frequency-domain representations.
    Calculates Power Spectral Density (PSD).
    """
    
    def __init__(self, fft_size: int = 1024):
        self.fft_size = fft_size
        
    def compute_fft(self, iq_samples: list):
        """
        Computes the Fast Fourier Transform of the provided I/Q samples.
        """
        pass
        
    def estimate_power(self, fft_output: list):
        """
        Calculates the Power Spectral Density (PSD) from FFT output.
        P[k] = |X[k]|^2
        """
        pass
