#!/usr/bin/env python3
"""Generate synthetic waveforms, then calculate actual STFTs from their WAVs.

No measured material samples are used. The resonant bandwidths and amplitudes are
illustrative choices expressing an experimenter's remembered visual differences.
All spectral pixels derive from a real 1-D waveform -> PCM WAV -> Hann-window FFT.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import wave

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
import numpy as np
from scipy import signal

ROOT = Path(__file__).resolve().parent
CONFIG = json.loads((ROOT / 'synthesis-config.json').read_text())
FS = CONFIG['sample_rate_hz']
N = round(FS * CONFIG['duration_seconds'])
TIME = np.arange(N, dtype=np.float64) / FS
BACKGROUND = '#050508'
TEXT = '#f1f0e9'
MUTED = '#a9a9ab'
NORM = Normalize(CONFIG['stft']['display_min_dbfs'], CONFIG['stft']['display_max_dbfs'])

plt.rcParams.update({
    'font.family': 'DejaVu Sans',
    'font.size': 10,
    'text.color': TEXT,
    'axes.labelcolor': MUTED,
    'xtick.color': MUTED,
    'ytick.color': MUTED,
    'figure.facecolor': BACKGROUND,
    'savefig.facecolor': BACKGROUND,
    'axes.edgecolor': '#cbcbcf',
    'svg.fonttype': 'none',
})


def normalised_rms(values: np.ndarray) -> np.ndarray:
    return values / max(float(np.sqrt(np.mean(values * values))), 1e-15)


def contact_envelope() -> np.ndarray:
    """Smooth starts/stops and small pressure changes applied to the time series."""
    envelope = np.zeros(N)
    for start, end in CONFIG['contact_strokes_seconds']:
        inside = (TIME >= start) & (TIME <= end)
        u = (TIME[inside] - start) / (end - start)
        attack_release = np.clip(u / 0.075, 0, 1) * np.clip((1 - u) / 0.075, 0, 1)
        pressure = 0.72 + 0.15 * np.sin(2 * np.pi * (2.4 * u + start / 10))
        pressure += 0.08 * np.sin(2 * np.pi * 7.1 * u)
        envelope[inside] = attack_release * pressure
    return envelope


ENVELOPE = contact_envelope()
ACTIVE = ENVELOPE > 0.25


def synthesize_waveform(spec: dict, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    # Low-level amplifier floor and shared low-frequency contact rumble. These
    # are explicitly synthetic, time-domain components rather than image noise.
    floor = rng.standard_normal(N) * 0.00030
    low_sos = signal.butter(3, 700, fs=FS, output='sos')
    rumble = normalised_rms(signal.sosfilt(low_sos, rng.standard_normal(N)))
    floor += rumble * 0.014 * (0.25 + 0.75 * ENVELOPE)

    # A driven 1-D resonator creates the material's illustrative spectral width.
    b, a = signal.iirpeak(CONFIG['frequency_centre_hz'], spec['resonator_q'], fs=FS)
    excitation = rng.standard_normal(N)
    ringing = signal.lfilter(b, a, excitation)
    # A steeper real time-domain stopband confines the response around the
    # middle-frequency peak. Its filter width is illustrative, not a material fit.
    half_width = max(220.0, min(1750.0, 4.0 * CONFIG['frequency_centre_hz'] / spec['resonator_q']))
    stopband_sos = signal.butter(
        6,
        [CONFIG['frequency_centre_hz'] - half_width, CONFIG['frequency_centre_hz'] + half_width],
        btype='bandpass', fs=FS, output='sos',
    )
    ringing = signal.sosfilt(stopband_sos, ringing)
    ringing = normalised_rms(ringing)
    output = floor + ringing * spec['active_rms'] * ENVELOPE

    # Brief physical-contact-like time-domain transients yield the vertical
    # spectral streaks in the reference. This timing is a simulation choice.
    for event in [3.0, 10.2, 17.5, 25.2, 33.3, 38.0]:
        index = round(event * FS)
        count = round(0.035 * FS)
        decay = np.exp(-np.arange(count) / (FS * 0.005))
        output[index:index + count] += rng.standard_normal(count) * decay * 0.026
    return output


def write_wav(path: Path, values: np.ndarray) -> None:
    assert np.max(np.abs(values)) < 0.98, 'Synthetic signal clips.'
    pcm = np.round(values * 32767).astype('<i2')
    with wave.open(str(path), 'wb') as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(FS)
        handle.writeframes(pcm.tobytes())


def read_wav(path: Path) -> np.ndarray:
    with wave.open(str(path), 'rb') as handle:
        assert handle.getframerate() == FS
        assert handle.getnchannels() == 1 and handle.getsampwidth() == 2
        return np.frombuffer(handle.readframes(handle.getnframes()), dtype='<i2').astype(np.float64) / 32767.0


def calculate_stft(values: np.ndarray):
    size = CONFIG['stft']['window_samples']
    hop = CONFIG['stft']['hop_samples']
    frequency, time, spectrum = signal.stft(
        values, fs=FS, window=CONFIG['stft']['window'],
        nperseg=size, noverlap=size - hop, nfft=size,
        detrend=False, return_onesided=True, boundary=None, padded=False,
    )
    # scipy's amplitude-normalised one-sided STFT is used consistently for every
    # panel. Positive interior bins receive the conjugate negative-frequency
    # contribution. DC and the even-FFT Nyquist endpoint already contain their
    # full amplitude and therefore retain factor 1.
    amplitude = np.abs(spectrum)
    if size % 2 == 0:
        amplitude[1:-1] *= 2.0
    else:
        amplitude[1:] *= 2.0
    dbfs = 20.0 * np.log10(np.maximum(amplitude, 1e-10))
    return frequency, time, spectrum, dbfs


def panel(ax, spec, frequency, time, dbfs, *, title_size=17, show_ylabel=True):
    image = ax.pcolormesh(time, frequency, dbfs, cmap='jet', norm=NORM, shading='auto', rasterized=True)
    ax.set_xlim(0, CONFIG['duration_seconds'])
    ax.set_ylim(0, FS / 2)
    ax.set_xticks([0, 11, 22, 33, 44])
    ax.set_yticks(np.arange(0, FS / 2 + 1, 1000))
    ax.grid(which='major', color='#e0e0ed', linewidth=0.5, alpha=0.67)
    ax.set_axisbelow(False)
    ax.set_title(spec['title'], loc='left', fontsize=title_size, pad=15, color=TEXT)
    ax.set_xlabel('Simulated time (s)', labelpad=10, fontsize=9)
    if show_ylabel:
        ax.set_ylabel('Simulated frequency (Hz)', labelpad=10, fontsize=9)
    ax.tick_params(labelsize=8, length=3)
    return image


def frequency_metrics(frequency, time, spectrum):
    active_frames = np.interp(time, TIME, ENVELOPE) > 0.35
    power = np.mean(np.abs(spectrum[:, active_frames]) ** 2, axis=1)
    middle = (frequency >= 2200) & (frequency <= 5000)
    index = np.flatnonzero(middle)[np.argmax(power[middle])]
    threshold = power[index] * (10 ** (-6 / 10))
    left = index
    right = index
    while left > 0 and power[left - 1] >= threshold:
        left -= 1
    while right + 1 < power.size and power[right + 1] >= threshold:
        right += 1
    width = frequency[right] - frequency[left] + (frequency[1] - frequency[0])
    return {
        'synthetic_peak_frequency_hz': float(frequency[index]),
        'synthetic_minus6db_width_hz': float(width),
        'synthetic_midband_power': float(power[middle].sum()),
    }


def amplitude_scale_checks():
    amplitude = 0.25
    count = CONFIG['stft']['window_samples'] * 8
    n = np.arange(count)
    cases = [
        ('bin_centred_sine', amplitude * np.sin(2 * np.pi * 64 * n / CONFIG['stft']['window_samples']), 64),
        ('dc', np.full(count, amplitude), 0),
        ('nyquist', amplitude * (-1.0) ** n, CONFIG['stft']['window_samples'] // 2),
    ]
    records = []
    for name, values, index in cases:
        frequency, _, _, dbfs = calculate_stft(values)
        reconstructed = 10.0 ** (dbfs[index] / 20.0)
        assert np.allclose(reconstructed, amplitude, rtol=1e-10, atol=1e-12), (name, reconstructed)
        records.append({
            'case': name,
            'input_peak_amplitude': amplitude,
            'synthetic_bin_frequency_hz': float(frequency[index]),
            'measured_stft_peak_amplitude_min': float(reconstructed.min()),
            'measured_stft_peak_amplitude_max': float(reconstructed.max()),
            'expected_dbfs': float(20 * np.log10(amplitude)),
            'max_absolute_amplitude_error': float(np.max(np.abs(reconstructed - amplitude))),
            'passed': True,
        })
    return records


def main():
    scale_checks = amplitude_scale_checks()
    plots = {}
    waveforms = {}
    metrics = {}
    for index, spec in enumerate(CONFIG['materials']):
        values = synthesize_waveform(spec, CONFIG['seed'] + index * 1009)
        assert np.array_equal(values, synthesize_waveform(spec, CONFIG['seed'] + index * 1009))
        wav = ROOT / (spec['id'] + '-synthetic.wav')
        write_wav(wav, values)
        # Plot the waveform read back from the actual PCM file, never a painted field.
        decoded = read_wav(wav)
        assert len(decoded) == N and np.all(np.isfinite(decoded))
        frequency, time, spectrum, dbfs = calculate_stft(decoded)
        plots[spec['id']] = (frequency, time, dbfs)
        waveforms[spec['id']] = decoded.astype(np.float32)
        metrics[spec['id']] = {
            **frequency_metrics(frequency, time, spectrum),
            'samples': N, 'peak_absolute': float(np.max(np.abs(decoded))),
            'wav_sha256': hashlib.sha256(wav.read_bytes()).hexdigest(),
        }

        fig, ax = plt.subplots(figsize=(6.6, 7.3), dpi=180)
        fig.subplots_adjust(left=0.15, right=0.86, top=0.86, bottom=0.15)
        image = panel(ax, spec, frequency, time, dbfs, title_size=22)
        bar = fig.colorbar(image, ax=ax, fraction=0.032, pad=0.035)
        bar.set_ticks(np.arange(-96, 1, 12))
        bar.ax.tick_params(labelsize=7)
        bar.set_label('Simulated level (dBFS)', fontsize=8, labelpad=7)
        fig.text(0.15, 0.94, 'Synthetic reconstruction', fontsize=11, color=MUTED)
        fig.savefig(ROOT / (spec['id'] + '-spectrogram.png'), dpi=180)
        plt.close(fig)

    # The NPZ contains only the 1-D synthetic source signals and their sample rate.
    # All 2-D spectral output is reproducibly calculated from those time series.
    np.savez_compressed(ROOT / 'synthetic-signals.npz', sample_rate_hz=np.int32(FS), **waveforms)
    fig = plt.figure(figsize=(17.2, 8.5), dpi=180)
    grid = fig.add_gridspec(1, 3, left=0.065, right=0.91, top=0.78, bottom=0.17, wspace=0.20)
    for index, spec in enumerate(CONFIG['materials']):
        image = panel(fig.add_subplot(grid[0, index]), spec, *plots[spec['id']], show_ylabel=index == 0)
    cax = fig.add_axes((0.935, 0.17, 0.009, 0.61))
    bar = fig.colorbar(image, cax=cax)
    bar.set_ticks(np.arange(-96, 1, 12))
    bar.ax.tick_params(labelsize=8)
    bar.set_label('Simulated level (dBFS)', fontsize=10, labelpad=9)
    fig.text(0.065, 0.935, 'Material signatures', fontsize=29, va='top')
    fig.text(0.065, 0.875, 'Synthetic reconstruction', fontsize=13, color=MUTED, va='top')
    fig.text(0.065, 0.065, "Peter reported successful visual differences. Signals, frequencies, durations and levels shown here are synthetic.", fontsize=10, color=MUTED)
    fig.savefig(ROOT / 'comparison.png', dpi=180)
    plt.close(fig)

    widths = [metrics[name]['synthetic_minus6db_width_hz'] for name in ['sandpaper', 'aluminium', 'wood']]
    powers = [metrics[name]['synthetic_midband_power'] for name in ['sandpaper', 'aluminium', 'wood']]
    assert widths[0] > widths[1] > widths[2], widths
    assert powers[0] > powers[1] > powers[2], powers
    assert all(3000 <= m['synthetic_peak_frequency_hz'] <= 4200 for m in metrics.values())
    validation = {
        'status': 'computed_from_synthetic_time_series',
        'sample_rate_hz': FS, 'duration_seconds': CONFIG['duration_seconds'],
        'shared_axes_and_colour_scale': True,
        'stft_source': 'Each stored 16-bit PCM WAV read back into a 1-D sample array',
        'stft_window_samples': CONFIG['stft']['window_samples'],
        'stft_hop_samples': CONFIG['stft']['hop_samples'],
        'spectral_image_painting': False,
        'measured_material_data_used': False,
        'numbers_are_simulation_parameters': True,
        'signals_regenerate_exactly_from_fixed_seeds': True,
        'one_sided_dc_nyquist_scaling_correct': True,
        'amplitude_scale_checks': scale_checks,
        'bandwidth_order_sandpaper_aluminium_wood': True,
        'midband_power_order_sandpaper_aluminium_wood': True,
        'materials': metrics,
    }
    (ROOT / 'validation.json').write_text(json.dumps(validation, indent=2) + '\n')
    print(json.dumps(validation, indent=2))


if __name__ == '__main__':
    main()
