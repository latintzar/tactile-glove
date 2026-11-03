# Material signatures

In my piezo experiment, I saw distinct spectral signatures for aluminium, wood and sandpaper. Sandpaper showed the largest bright region in the middle; wood a small, thin feature; aluminium a small-to-medium feature.

![Three material signatures](https://atelierneyra.com/hardware/tactile-glove/media/black-nitrile-20261103/material-signatures.png)

*Reconstructed from my description of the experiment.*

This figure preserves the qualitative visual result I recalled on 3 November 2026. Its shapes reproduce the reported relationships. Frequency, duration and amplitude were unrecorded, so the axes remain uncalibrated. The original Bela P60/P220 recordings and their recorded outcomes retain their own experiment record.

## Reproduce the figure

From the repository root:

```sh
cd docs/material-signatures
python3 -m pip install -r requirements.txt
python3 render.py
python3 -m http.server 8079
```

Open http://127.0.0.1:8079/. The included page displays the generated panels. The script produces standalone PNG, SVG and PDF figures. `reconstruction-config.json` keeps the reported material descriptions and schematic shape parameters separate. The plotting code runs locally.

## Source

- `render.py`: deterministic plotting source.
- `reconstruction-config.json`: qualitative source and drawing parameters.
- `index.html`: responsive display after rendering.
- `requirements.txt`: plotting dependencies.

Peter Neyra’s original plotting code and documentation use the repository’s MIT licence.
