"""
Feature banks: proiezioni non-apprese che mappano x -> phi(x).
Tutti i banchi seguono interfaccia scikit-style: fit(X) + transform(X).
fit() NON usa y - serve solo a calibrare il banco sul range dei dati.
"""
import numpy as np
from numpy.polynomial.chebyshev import chebval


def first_n_primes(n):
    primes = []
    c = 2
    while len(primes) < n:
        if all(c % p != 0 for p in primes if p * p <= c):
            primes.append(c)
        c += 1
    return np.array(primes, dtype=float)


class FeatureBank:
    """Interfaccia base. Sottoclassi implementano fit/transform."""
    def fit(self, X, y=None):
        return self
    def transform(self, X):
        raise NotImplementedError
    def fit_transform(self, X, y=None):
        return self.fit(X, y).transform(X)
    @property
    def n_output_features(self):
        return self._n_out


class PassThroughBank(FeatureBank):
    """Identita - baseline: readout lineare su input grezzi."""
    def fit(self, X, y=None):
        self._n_out = X.shape[1]
        return self
    def transform(self, X):
        return X


class RandomFourierBank(FeatureBank):
    """Random Fourier Features (Rahimi & Recht 2007).
    Approssima un kernel RBF con proiezioni random."""
    def __init__(self, n_features=64, gamma=1.0, seed=0):
        self.n_features = n_features
        self.gamma = gamma
        self.seed = seed
    def fit(self, X, y=None):
        rng = np.random.RandomState(self.seed)
        d = X.shape[1]
        self.W = rng.normal(0, np.sqrt(2 * self.gamma), (d, self.n_features))
        self.b = rng.uniform(0, 2 * np.pi, self.n_features)
        self._n_out = self.n_features
        return self
    def transform(self, X):
        return np.cos(X @ self.W + self.b) * np.sqrt(2.0 / self.n_features)


class PrimeFourierBank(FeatureBank):
    """Fourier features con frequenze costruite dai numeri primi.
    Ogni output e' cos(sum_i sign_i * p_k * x_i) con p_k primo.
    Deterministico (nessun random nei pesi)."""
    def __init__(self, n_features=64, scale=0.5, sign_seed=42):
        self.n_features = n_features
        self.scale = scale
        self.sign_seed = sign_seed
    def fit(self, X, y=None):
        d = X.shape[1]
        primes = first_n_primes(max(self.n_features, d * 8))
        rng = np.random.RandomState(self.sign_seed)
        self.W = np.zeros((d, self.n_features))
        for j in range(self.n_features):
            for i in range(d):
                self.W[i, j] = primes[(j * d + i) % len(primes)] * self.scale
            self.W[:, j] *= rng.choice([-1, 1], size=d)
        self.b = np.zeros(self.n_features)
        self._n_out = self.n_features
        return self
    def transform(self, X):
        return np.cos(X @ self.W + self.b) * np.sqrt(2.0 / self.n_features)


class ChebyshevBank(FeatureBank):
    """Polinomi di Chebyshev T_0..T_degree per ogni dim di input.
    Base ortogonale classica per approx di funzioni."""
    def __init__(self, degree=8):
        self.degree = degree
    def fit(self, X, y=None):
        self.x_min = X.min(axis=0)
        self.x_max = X.max(axis=0)
        self.x_range = self.x_max - self.x_min
        self.x_range[self.x_range == 0] = 1.0
        d = X.shape[1]
        self._n_out = d * (self.degree + 1)
        return self
    def transform(self, X):
        Xn = 2 * (X - self.x_min) / self.x_range - 1
        Xn = np.clip(Xn, -1, 1)
        n, d = Xn.shape
        out = np.zeros((n, d * (self.degree + 1)))
        for i in range(d):
            for k in range(self.degree + 1):
                coef = np.zeros(k + 1)
                coef[k] = 1.0
                out[:, i * (self.degree + 1) + k] = chebval(Xn[:, i], coef)
        return out


class MorletWaveletBank(FeatureBank):
    """Wavelet di Morlet a multi-scala, multi-posizione (per dim).
    psi(x) = cos(omega*u) * exp(-u^2/2), u = (x-pos)/scale."""
    def __init__(self, n_scales=4, n_positions=8, omega=5.0):
        self.n_scales = n_scales
        self.n_positions = n_positions
        self.omega = omega
    def fit(self, X, y=None):
        self.x_min = X.min(axis=0)
        self.x_max = X.max(axis=0)
        self.x_range = self.x_max - self.x_min
        self.x_range[self.x_range == 0] = 1.0
        d = X.shape[1]
        self.scales = np.array([2.0 ** (-i) for i in range(self.n_scales)])
        self.positions = np.linspace(-1, 1, self.n_positions)
        self._n_out = d * self.n_scales * self.n_positions
        return self
    def transform(self, X):
        Xn = 2 * (X - self.x_min) / self.x_range - 1
        n, d = Xn.shape
        out = np.zeros((n, d * self.n_scales * self.n_positions))
        idx = 0
        for i in range(d):
            for s in self.scales:
                for p in self.positions:
                    u = (Xn[:, i] - p) / s
                    out[:, idx] = np.cos(self.omega * u) * np.exp(-0.5 * u ** 2)
                    idx += 1
        return out


class RandomProjectionBank(FeatureBank):
    """Random projection + tanh (layer reservoir-like, non ricorrente)."""
    def __init__(self, n_features=64, seed=0):
        self.n_features = n_features
        self.seed = seed
    def fit(self, X, y=None):
        rng = np.random.RandomState(self.seed)
        d = X.shape[1]
        self.W = rng.normal(0, 1.0 / np.sqrt(d), (d, self.n_features))
        self.b = rng.uniform(-0.5, 0.5, self.n_features)
        self._n_out = self.n_features
        return self
    def transform(self, X):
        return np.tanh(X @ self.W + self.b)


# Registry: nome -> factory(seed) -> istanza
BANKS = {
    "passthrough":       lambda seed: PassThroughBank(),
    "random_fourier":    lambda seed: RandomFourierBank(n_features=64, gamma=1.0, seed=seed),
    "prime_fourier":     lambda seed: PrimeFourierBank(n_features=64, scale=0.5),
    "chebyshev":         lambda seed: ChebyshevBank(degree=8),
    "morlet_wavelet":    lambda seed: MorletWaveletBank(n_scales=4, n_positions=8),
    "random_projection": lambda seed: RandomProjectionBank(n_features=64, seed=seed),
}
