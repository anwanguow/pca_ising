#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
import matplotlib.pyplot as plt
from sklearn.decomposition import PCA

seed = 42
np.random.seed(seed)

def wolff_step(spins, beta):
    L = spins.shape[0]
    i, j = np.random.randint(0, L), np.random.randint(0, L)
    spin_value = spins[i, j]
    cluster = {(i, j)}
    stack = [(i, j)]
    p_add = 1 - np.exp(-2 * beta)
    
    while stack:
        x, y = stack.pop()
        for dx, dy in [(1,0),(-1,0),(0,1),(0,-1)]:
            nx, ny = (x+dx)%L, (y+dy)%L
            if (nx,ny) not in cluster and spins[nx,ny]==spin_value:
                if np.random.rand() < p_add:
                    cluster.add((nx,ny))
                    stack.append((nx,ny))
    for (x,y) in cluster:
        spins[x,y] = -spins[x,y]
    return spins

def equilibrate(spins, beta, max_sweeps=20000, W=100, eps_m=None, eps_v=None):
    N = spins.size
    if eps_m is None:
        eps_m = 1e-3 * N
    if eps_v is None:
        eps_v = 1e-4 * N * N

    m_traj = []
    for sweep in range(1, max_sweeps+1):
        wolff_step(spins, beta)
        m_traj.append(np.sum(spins))
        if sweep >= 2*W:
            A = np.array(m_traj[-W:])
            B = np.array(m_traj[-2*W:-W])
            if (abs(A.mean()-B.mean()) < eps_m and
                abs(A.var()-B.var())   < eps_v):
                return sweep
    return max_sweeps

def estimate_tau_int(m_traj, tau_max=None):
    m = np.asarray(m_traj, dtype=float)
    m -= m.mean()
    N = len(m)
    if tau_max is None:
        tau_max = N // 2
    var = np.dot(m, m) / N
    C = [1.0]
    for tau in range(1, tau_max):
        c = np.dot(m[:-tau], m[tau:]) / (N-tau) / var
        if c < 0:
            break
        C.append(c)
    return 1 + 2 * np.sum(C[1:])

def simulate(L, temps, n_samples,
             max_eq_sweeps=20000, W=100,
             n_ac_sweeps=5000, ac_factor=10):
    
    """
    For each temperature in `temps`:
      1. Equilibrate until convergence.
      2. Measure m_t for `n_ac_sweeps` to estimate tau_int.
      3. Set sweeps_between = ceil(ac_factor * tau_int).
      4. Sample `n_samples` configurations separated by sweeps_between.
    Returns:
      X: array of shape (len(temps)*n_samples, L*L)
      sample_temps: array of corresponding temperatures
    """
    
    samples = []
    sample_temps = []

    for T in temps:
        beta = 1.0 / T
        spins = np.random.choice([-1,1], size=(L,L))
        
        # 1) Equilibrate
        eq_sweeps = equilibrate(spins, beta,
                                max_sweeps=max_eq_sweeps,
                                W=W)
        print(f"T={T:.2f}: equilibrated in {eq_sweeps} sweeps")
        
        # 2) Estimate autocorrelation time
        m_traj = []
        for _ in range(n_ac_sweeps):
            wolff_step(spins, beta)
            m_traj.append(np.sum(spins))
        tau_int = estimate_tau_int(m_traj)
        sweeps_between = max(1, int(np.ceil(ac_factor * tau_int)))
        print(f"  tau_int ≈ {tau_int:.2f}, using interval = {sweeps_between}")
        
        # 3) Sample configurations
        for _ in range(n_samples):
            for _ in range(sweeps_between):
                wolff_step(spins, beta)
            samples.append(spins.flatten().copy())
            sample_temps.append(T)
        print(T)
    return np.array(samples), np.array(sample_temps)

# -----------------------
# Settings
# -----------------------



L = 80
temps = np.arange(1.6, 3.0, 0.01)
n_samples = 80


X, sample_temps = simulate(L, temps, n_samples)

# -----------------------
# PCA
# -----------------------

N_components=10

pca = PCA(n_components = N_components)
Y = pca.fit_transform(X)
explained = pca.explained_variance_ratio_

# -----------------------
# Plotting
# -----------------------

plt.rcParams.update({
    'font.size': 15,
    'axes.titlesize': 15,
    'axes.labelsize': 15,
    'xtick.labelsize': 13,
    'ytick.labelsize': 13,
    'legend.fontsize': 13
})

# Fig.1: Explained variance
plt.figure(figsize=(8, 4), dpi=300)
indices = np.arange(1, N_components+1)
plt.bar(indices, explained, tick_label=[f'PC{i}' for i in indices])
plt.xlabel('Principal Component')
plt.ylabel('Explained Variance')
plt.xticks(indices)
plt.tight_layout()
plt.show()

# Fig.2: PC1 vs Temperature
plt.figure(figsize=(8, 3.6), dpi=300)
plt.scatter(sample_temps, Y[:,0], s=5)
plt.axhline(0, color='gray', linestyle='--')
plt.xlabel('Temperature')
plt.ylabel('1st Principal Component')
plt.tight_layout()
plt.show()

# Fig.3: PC1 vs PC2 colored by Temperature
plt.figure(figsize=(8, 3.6), dpi=300)
scatter = plt.scatter(
    Y[:,0], Y[:,1],
    c=sample_temps,
    s=20,
    cmap='coolwarm',
    edgecolor='none'
)

plt.xlabel('1st Principal Component')
plt.ylabel('2nd Principal Component')
plt.yticks([-20, 0, 20])
cbar = plt.colorbar(scatter)
cbar.set_label('Temperature T', fontsize=14)
plt.axvline(0, color='gray', linestyle='--', linewidth=1)
plt.axhline(0, color='gray', linestyle='--', linewidth=1)
plt.tight_layout()
plt.show()
