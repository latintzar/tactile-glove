#!/usr/bin/env python3
"""Render qualitative spectrogram reconstructions from a documented recollection.

These fields are schematic image intensities, not recorded or simulated sensor
samples. The common position and geometric widths communicate recalled visual
relationships only. No Hz, seconds, dB, sample rate or calibration is inferred.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, Normalize
import numpy as np

ROOT = Path(__file__).resolve().parent
CONFIG = json.loads((ROOT / 'reconstruction-config.json').read_text())
BACKGROUND = '#080c0d'
PANEL = '#0b1112'
TEXT = '#f0f1e9'
MUTED = '#a6afac'
EDGE = '#34413f'
CMAP = LinearSegmentedColormap.from_list(
    'qualitative_spectral',
    ['#0b1112', '#0b2325', '#0c4d4b', '#288e72', '#a1c66e', '#ede99d', '#fffbea'],
)
NORM = Normalize(vmin=0.0, vmax=1.0)

plt.rcParams.update({
    'font.family': 'DejaVu Sans',
    'font.size': 11,
    'text.color': TEXT,
    'axes.labelcolor': MUTED,
    'xtick.color': MUTED,
    'ytick.color': MUTED,
    'axes.edgecolor': EDGE,
    'figure.facecolor': BACKGROUND,
    'savefig.facecolor': BACKGROUND,
    'svg.fonttype': 'none',
    'pdf.fonttype': 42,
})


def reconstruct(spec: dict) -> np.ndarray:
    """A visible feature, constructed geometrically from the verbal description."""
    x = np.linspace(0, 1, CONFIG['grid']['width'])
    y = np.linspace(0, 1, CONFIG['grid']['height'])
    xx, yy = np.meshgrid(x, y)
    dx = (xx - 0.5) / spec['schematic_width']
    dy = (yy - 0.5) / spec['schematic_height']
    # Smooth halo + bright central core. Width/height are drawing parameters.
    halo = np.exp(-0.5 * (dx * dx + dy * dy))
    core = np.exp(-1.8 * (dx * dx + dy * dy))
    return np.clip(0.63 * halo + 0.37 * core, 0, 1)


def draw_panel(ax, spec: dict, field: np.ndarray, *, ylabel: bool = True, title_size: float = 17):
    ax.set_facecolor(PANEL)
    image = ax.imshow(
        field, cmap=CMAP, norm=NORM, origin='lower', extent=(0, 1, 0, 1),
        interpolation='bilinear', aspect='auto', rasterized=True,
    )
    ax.set_title(spec['material'], loc='left', color=TEXT, fontsize=title_size, pad=19)
    # Broad qualitative coordinates keep the chart readable without invented units.
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_xlabel('Time · uncalibrated', labelpad=15, fontsize=10)
    if ylabel:
        ax.set_ylabel('Frequency · uncalibrated', labelpad=15, fontsize=10)
    for spine in ax.spines.values():
        spine.set_linewidth(0.7)
    return image


def render():
    fields = {spec['id']: reconstruct(spec) for spec in CONFIG['materials']}
    fig = plt.figure(figsize=(15.5, 6.6), dpi=180)
    grid = fig.add_gridspec(1, 3, left=0.065, right=0.935, top=0.71, bottom=0.20, wspace=0.17)
    for index, spec in enumerate(CONFIG['materials']):
        image = draw_panel(fig.add_subplot(grid[0, index]), spec, fields[spec['id']], ylabel=index == 0)
    fig.text(0.065, 0.925, 'Material signatures', fontsize=27, weight='medium', va='top')
    fig.text(0.065, 0.858, 'Reconstructed from my description of the experiment', fontsize=12, color=MUTED, va='top')
    cax = fig.add_axes((0.958, 0.20, 0.006, 0.51))
    bar = fig.colorbar(image, cax=cax)
    bar.set_ticks([])
    bar.outline.set_linewidth(0)
    cax.text(0.5, 1.045, 'Bright', transform=cax.transAxes, fontsize=8, color=MUTED, ha='center')
    cax.text(0.5, -0.065, 'Faint', transform=cax.transAxes, fontsize=8, color=MUTED, ha='center')
    fig.text(0.065, 0.075, 'Qualitative reconstruction', fontsize=10, color=MUTED)
    for extension in ('png', 'svg', 'pdf'):
        fig.savefig(ROOT / ('material-signatures.' + extension), dpi=180)
    plt.close(fig)

    for spec in CONFIG['materials']:
        tile, ax = plt.subplots(figsize=(5.6, 4.6), dpi=180)
        tile.subplots_adjust(left=0.12, right=0.98, top=0.80, bottom=0.18)
        draw_panel(ax, spec, fields[spec['id']], title_size=26)
        tile.savefig(ROOT / (spec['id'] + '.png'), dpi=180)
        plt.close(tile)

    audit = {
        'source_class': CONFIG['source_class'],
        'measured_data_used': False,
        'calibrated_units_used': False,
        'random_noise_added': False,
        'same_colour_normalisation': True,
        'same_position_and_axes': True,
        'feature_area_order': 'sandpaper > aluminium > wood',
        'field_sizes': {key: list(value.shape) for key, value in fields.items()},
        'peak_brightness': 'same common visual scale; no amplitude comparison claimed',
    }
    (ROOT / 'render-checks.json').write_text(json.dumps(audit, indent=2) + '\n')
    print(json.dumps(audit, indent=2))


if __name__ == '__main__':
    render()
