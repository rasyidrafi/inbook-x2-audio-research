# Hardware test result: NOT APPROVED for permanent installation

The live trial found failures that compile tests could not detect. Neither
1.1.0 nor the follow-up 1.1.1 experiment is approved for permanent installation.
All builds ran on the remote build host. DKMS on the laptop remains 1.0.1.

## What worked with 1.1.0

- Direct load without a quirk override detected the board and selected mask 0x80.
- The user confirmed normal music playback.
- Three initial and twenty additional STOP/prepare/START transitions kept both
  audio GPIOs high while PCM counters advanced.
- Six idle-to-playback cycles succeeded with the WirePlumber keep-open workaround
  temporarily disabled; each cycle began with the actual sink SUSPENDED.
- One deep suspend/resume completed. The machine woke earlier than the scheduled
  25-second RTC alarm; logs show about four seconds between suspend entry/exit.
  The user confirmed normal sound afterward, and a subsequent silent playback
  advanced hw_ptr from 18192 to 42240 in roughly half a second.
- Capture using ALSA directly and using its PipeWire plugin completed successfully
  to /dev/null. This verifies data flow, not microphone acoustic quality.
- pw-record returned 1 despite producing exactly 384000 bytes for two seconds
  of stereo 48 kHz s16 capture, with no stderr. The same result occurred on
  recovered baseline 1.0.1; this was not specific to the candidate.
- Direct ALSA pause returned ENOSYS. It is unsupported on this tested PCM and
  is not counted as a passed hardware pause test.

## Failure 1: leaked headphone GPIO on module removal

The modern candidate based on upstream v7.3 did not release gpio_headphone in
remove(). Its headphone-acquisition and card-registration error paths also had
incomplete descriptor cleanup. The older local 1.0.1 source had cleanup that
was lost when generating the modern candidate from upstream.

After unloading the candidate, headphone-enable remained requested. Baseline
1.0.1 could not probe: EBUSY obtaining headphone-enable, and no sound card was
registered. A one-shot, board/owner-checked diagnostic cleanup released the
orphaned descriptor; its helper module was immediately unloaded. Baseline was
rebound and actual speaker playback and capture were verified. This helper is
not a runtime workaround, is not installed, and is not part of the public driver.

The 1.1.1 experiment adds a third patch releasing both descriptors, cancelling
initialized work on card-registration failure, and unwinding failed GPIO
acquisition correctly. Two new C-backed tests exercise actual remove and failure
cleanup code. Seven unit tests and both kernel builds passed on the build host.
Those results do not qualify the experiment for deployment.

## Failure 2: topology error and kernel Oops during subsequent reload

During the subsequent 1.1.1 reload trial, SOF failed to set up
PIPELINE.7.HDA5.OUT with IPC error -22 and failed sound card registration.
The next reload produced invalid topology/list state and a NULL dereference in
soc_tplg_dapm_widget_elems_load, through snd_soc_tplg_component_load and
snd_sof_load_topology. The insmod process died, the module remained in the
COMING state, and no sound card was available.

The intended three reload cycles did NOT complete. The live reload tests were
stopped. The cause of the topology failure is not yet established: the trace
does not prove that the new GPIO cleanup caused it, nor that it is independent
of earlier hot reloads, suspend, or prior failed probing. No further experimental
kernel manipulation is appropriate in the damaged kernel session.

## Recovery and remaining limits

The installed 1.0.1 modules, quirk=128 configuration, and original WirePlumber
configuration were retained/restored. No candidate was installed in DKMS or
initramfs. A reboot into the existing installation is the recovery path for the
kernel Oops; permission is required before interrupting unsaved user work.

Headset hardware was unavailable. Cold boot with a candidate, runtime testing
on LTS, long-duration stability, and microphone sound quality are not qualified.
Do not infer that successful playback tests mean all audio functions work.

This report contains a summary only. Raw kernel logs, runtime snapshots, host
identifiers, and the one-shot recovery helper remain in the private workspace.
