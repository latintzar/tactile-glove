# Battery-path transient review

The finite-source-impedance runs did not complete. Their native logs report numerical timestep failure in the TI TPS63070 PSpice macro under ngspice 42. They establish neither a transient pass nor a circuit failure. The source decks, native logs, native stopping times and content hashes are retained in [the attempt record](simulation/battery-path-transient-review.json).

The attempts add the 190 mΩ battery-path allocation and actual 300 kΩ/100 kΩ enable divider to the converter model. The later network splits 160 mΩ upstream impedance and 30 mΩ BATFET impedance, includes effective battery/SYS capacitance, and tests startup and a source reduction. Both later runs stopped at 384.198 µs, before the load step. Earlier bounded Gear/trapezoidal attempts also stopped early. Further parameter changes are not counted as verification.

ngspice can return exit status zero after a failed transient. Its subsequent `linearize` command can pad a waveform to the requested ending time. The runner now requires the native time vector to reach the requested endpoint before interpolation; failed padded exports are excluded from accepted waveform evidence. Historical stiff-source results retain their original waveforms and hashes, with original native-log coverage stated separately.

The independent [battery-path calculation](battery-path-check-results.json) verifies topology, resistance allocations and DC current. The routed copper audit verifies its stated conductor model. Neither calculation substitutes for converter-loop transient verification. A converged vendor-model run and first-article startup/load captures remain release checks for this source-impedance condition.

The unchanged `buck_corrected60u` stiff-source deck was rerun with the stricter recorder on 23 October. It completed its native 700 µs transient with 7,001 valid rows and reproduced the prior waveform byte-for-byte (SHA-256 `3b596f41a0ad41bda7a3f0d62f25489190cdbf6ac844bf3408a53ad21706b046`). Its retained log now verifies native completion; this result covers that stiff-source case only.

## Extended operating-point and KLU cases —23 October

Five additional bounded cases are in [the follow-up record](simulation/finite-path-followup.json). A prebiased4.2 V case timed out;3.7 V stopped at157.514 µs. KLU repeats of3.7 V operation and finite-path startup also remained incomplete. Neither solver provides a validated regulating finite-path waveform.

The cold3.2 V source case completes numerically with EN low: the300 kΩ/100 kΩ divider is at the typical0.8 V rising threshold. The regulator therefore never enters regulated operation. An ideal current sink later pulls its precharged output below ground; that is an invalid load-region artifact, not a predicted physical output. This case is below the3.55 V firmware restart condition and is retained as enable-state evidence only. Native completion and functional regulation are separate criteria.
