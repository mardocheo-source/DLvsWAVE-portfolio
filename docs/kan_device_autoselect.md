# KAN Device Autoselect

This pipeline pattern runs a short KAN metric pretest before the full training
run and can choose the fastest device for the current master.

## Modes

```bash
DEVICE_MODE=auto
```

Starts from `AUTO_DEVICE_PRIMARY` (`xpu` by default), runs the normal metric
pretest, compares it with `cpu` using `CPU_JOBS=6`, then trains with the faster
device.

```bash
DEVICE_MODE=cpu
DEVICE_MODE=xpu
DEVICE_MODE=cuda
DEVICE_MODE=nvidia
```

Forces a specific device and skips automatic selection.

## Japan Proximity Batch

Default is now automatic:

```bash
./commands/run_japan_zone_mag79_30d_and_7d_proximity_xpu.sh
```

Force CPU:

```bash
DEVICE_MODE=cpu CPU_JOBS=6 ./commands/run_japan_zone_mag79_30d_and_7d_proximity_xpu.sh
```

Force Intel XPU:

```bash
DEVICE_MODE=xpu ./commands/run_japan_zone_mag79_30d_and_7d_proximity_xpu.sh
```

Force NVIDIA CUDA:

```bash
DEVICE_MODE=cuda ./commands/run_japan_zone_mag79_30d_and_7d_proximity_xpu.sh
```

Auto mode prints lines like:

```text
[speed-test] XPU metric speed: 2.667s/tr
[speed-test] CPU metric speed: 1.583s/tr, jobs=3
[device-auto] selected cpu jobs=3
```

The speed test is run after the master is built, so if the master changes, the
next run tests the device choice on the new data shape. In `auto` mode the CPU
comparison is not limited to once per batch, because each target/proximity
variant may produce a different master.

## Generic Template

Use this template for other macro pipelines:

```bash
PIPELINE_MACRO=/path/to/RUN_GEOGRAPHIC_COUNTERCHECK.sh \
DEVICE_MODE=auto \
./commands/run_kan_device_auto_template.sh
```

Useful knobs:

```bash
AUTO_DEVICE_PRIMARY=xpu      # xpu or cuda
CPU_JOBS=6                  # CPU comparison/training workers
ACCELERATOR_JOBS=1          # GPU/XPU training workers
TRIALS_PER_VARIANT=144       # progress-bar expected trial count
PROGRESS_FILTER=0           # raw logs
```

## Notes

Small masters and tiny KAN presets can be faster on CPU because GPU/XPU transfer
and framework overhead dominate. Larger masters, larger KAN presets, or longer
iterations may favor XPU/CUDA, so auto mode should be preferred when the data
shape changes.
