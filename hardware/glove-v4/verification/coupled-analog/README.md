# Coupled 20-channel analog network

The generated deck connects all20 charge amplifiers,40 active filter stages, both shared excitation/midpoint amplifiers and the negative ADC driver. It stamps289 exact canonical component references and63 amplifier sections. All20 pressure pull-downs and changing contact resistances load the actual dual-feedback excitation buffer. Sensor charge and cable capacitance are explicit electrical inputs; supply/reference remain ideal boundaries.

Seven bounded original-model attempts failed numerical initialization or transient completion in ngspice42. Sparse1.3 and KLU solvers, DC initialization, nodeset, initial capacitor conditions and UIC attempts are retained separately. The final nodeset attempt supplies only starting guesses for the manufacturer's noise diode nodes; device equations are unchanged. These seven runs remain incomplete; the later conditioned diagnostic below reaches its endpoint but does not close numerical qualification. These failures do not establish that the physical circuit fails; they also cannot validate simultaneous-channel behavior.

The separately completed differential ADC network demonstrates that the OPA320 model works at fixed1.25 V bias in that network. An isolated or combined failure is specific to its circuit/backend conditions. Existing single-channel and shared passive-bias results retain their own narrower scope.

The runner rejects numerical errors, missing native endpoints and missing normal exit markers even when the process exits zero. The later conditioned diagnostic retains a complete waveform and those coupling metrics; its sensitivity failures prevent a coupled-network qualification pass. Independent board-channel crosstalk measurements and a converged supported-model analysis remain required before assigning a coupled-network pass.

Reproduce with `python3 hardware/glove-v4/verification/coupled-analog/run.py --case single_positive --work /tmp/glove-coupled-check`. Requires the recorded ngspice42/XSPICE environment. Native decks, logs and result metadata are in `attempts/`.

A further controlled warm-start diagnostic derives1541 internal starting guesses from completed single-amplifier operating points. The full network still aborts at its initial transient point; original model equations were preserved. Compressed native evidence is retained under`diagnostics/warmstart/`. This closes the initialization hypothesis without promoting a failed run to a hardware result.

## Conditioned native trace and sensitivity

[Retained native evidence](diagnostics/conditioning/results.json) now includes one completed135ms single-positive case with67,674 finite, strictly increasing time samples. All289 canonical references,63 amplifier sections and vendor equations are preserved; only solver options change. `--solver-profile conditioned` reproduces it with Gear, reltol1e-3, abstol1e-9 and gmin1e-9. The default runner retains its original strict profile. `diagnostics/conditioning/analyze.py` verifies every saved deck differs from the current canonical generator only in its options line, checks the native endpoint/error/exit markers, then reuses the runner's waveform analysis.

The diagnostic gives a0.560066V active differential pulse,0.001664V on the two sampled quiet channels (0.297% of active peak), and a2.305005V minimum VEXC during simultaneous20-channel pressure loading. Pressure-induced idle differential disturbance reaches21.807mV; end-of-run residuals remain several millivolts. These observations identify shared-bias transient behavior to investigate, rather than calibrated texture sensitivity or measured hardware crosstalk.

Tightening only gmin to1e-10 stops at14.318ms, before either test event; tightening only abstol to1e-12 fails initialization. Two jointly tighter runs also fail. Thus a numerical sensitivity comparison is unavailable: the complete trace relies on both relaxed settings, which matter in a high-impedance charge circuit. Qualified coupled cases remain zero. Compressed full/partial waveforms, native logs, decks, hashes and a bounded display trace are retained; no error or padded endpoint is promoted to completion.
