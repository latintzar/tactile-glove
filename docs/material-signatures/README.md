# Material signatures

In my piezo experiment, I saw distinct spectral signatures for aluminium, wood and sandpaper. Sandpaper had the largest bright feature in the middle of the frequency range; wood a small, thin ridge; aluminium a small-to-medium feature.

![Recreated spectrograms showing the observed material differences](https://atelierneyra.com/hardware/tactile-glove/media/material-signatures-20261103/comparison.webp)

*Recreated from my observations.*

These figures recreate the observed differences. Numerical scales are illustrative.

## Reproduce the spectrograms

From the repository root:

```sh
cd docs/material-signatures/synthetic-stft-20261103
python3 -m pip install -r requirements.txt
python3 synthesize.py
python3 -m http.server 8079
```

Open http://127.0.0.1:8079/. The script creates seeded time-domain signals, saves them as 16-bit PCM WAVs and reads those files back to calculate Hann-window STFTs. The three panels share a simulated frequency/time range and one dBFS colour scale.

`synthesis-config.json` records the construction parameters. `validation.json` checks the material hierarchy and one-sided amplitude scaling, including DC and Nyquist. The original recorded Bela experiments retain their own source records.

## Source

The `synthetic-stft-20261103/` folder contains the generator, configuration, pinned requirements, responsive display, provenance and computational checks. Running the generator produces the three WAVs, one-dimensional NPZ arrays and full-axis PNG spectrograms locally.

Peter Neyra’s original signal-processing code and documentation use the repository’s MIT licence.
