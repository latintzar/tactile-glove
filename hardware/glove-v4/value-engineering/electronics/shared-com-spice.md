# Shared-COM native SPICE check

This is an electronics value-engineering artifact for the proposed one-hot shared-COM bus. It does not alter canonical hardware. The generated decks and waveforms are in [shared-com-spice-run](shared-com-spice-run/), and the reproducible runner is [shared-com-spice.py](shared-com-spice.py).

## Model and acceptance rule

The deck uses the original local TI OPA320 vendor model, four 80 pF 4067 COM parasitic capacitors tied to the shared bus, one enabled 4067 at a time, and the retained positive and negative ADC paths: 22 ohm isolation, 1 nF charge bucket, 200 ohm plus 31 pF acquisition load. The selected bank is enabled from time zero so the bus precharges to the source low level before the source step at 10 us: 0.1 V to 2.5 V for dynamic and 0 V to 2.5 V for pressure. It sweeps the requested 4067 resistance proxies (1 kohm and 2 kohm). The pressure case adds the requested 10 kohm source resistance. The analog comparison is at the existing 6 us dynamic and 24 us pressure waits.

Acceptance is the absolute differential sample residual at the wait time versus the final modeled differential value, below one-half 16-bit ADC LSB (45.8 uV at 3.0 V full scale). This is a model result, not a production guarantee.

| case | wait | residual at wait | half LSB | result |
|---|---:|---:|---:|---|
| dynamic, 1 kohm mux | 6 us | 24.2 nV | 45.8 uV | PASS |
| dynamic, 2 kohm mux | 6 us | 241.4 uV | 45.8 uV | FAIL |
| pressure, 10 kohm source + 1 kohm mux | 24 us | 3.005 mV | 45.8 uV | FAIL |
| pressure, 10 kohm source + 2 kohm mux | 24 us | 5.262 mV | 45.8 uV | FAIL |

The shared-COM proposal therefore fails the same-spec check in this conservative direct-bus topology. The pressure failure is decisive: removing the bank followers leaves the 10 kohm pressure source charging the roughly 320 pF shared-COM node through the mux resistance; the retained OPA320 then buffers that node into the ADC bucket. The raw current component-row opportunity is U10 plus U26, about $2.0919 before adding the HC139, local bypass, PCB changes, and assembly effects. That saving is too small to book while the required pressure settling is failing. A variant that retains the pressure follower path would need a fresh topology and BOM count; it is not this candidate.

The dynamic 1 kohm pass is useful evidence that the bus itself can settle with a low source impedance. The 2 kohm dynamic fail and both pressure fails reject the candidate as a full replacement for the current four-bank topology.

## HC139 bank-transition requirement

The SN74HC139 is an active-low decoder. During a bank-code transition such as 01 -> 10, unequal address and output propagation can select an intermediate wrong decode; the design must not assume glitch-free one-hot behavior. The analog deck intentionally does not claim to model decoder timing or switch charge injection.

Use the existing SN74AHC595 spare bit as an explicit blank-enable:

1. assert blank, disabling all four 4067 enables;
2. wait through decoder/output skew and switch turn-off;
3. preload the next bank address;
4. release blank and select exactly one bank.

The blank interval should be set by measured HC139/4067 behavior and verified on the assembled board. Per-channel filter, protection, and bank-plus-slot identity remain required.

## Model limits

Switch charge injection, off leakage, decoder skew, PCB parasitics, switched-SAR behavior, and op-amp process/temperature variation are outside this deck. The native runs completed at 80 us with no ngspice errors. These results are evidence to reject the proposed direct shared-COM replacement, not evidence that a redesigned buffered topology is impossible.
