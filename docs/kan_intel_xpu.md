# Intel XPU Notes

Questa nota documenta il setup sperimentale per usare una GPU Intel Arc con i
run KAN e DeepNet di DLvsWAVE.

## Stato Verificato

Ambiente XPU:

```bash
${HOME}/venvs/dlvswave-xpu/bin/python
```

Test locale riuscito:

```text
torch 2.12.0+xpu
xpu available True
xpu devices 1
KAN mini-fit su xpu:0 OK
```

Il CLI supporta ora:

```bash
--kan-device xpu
--deep-device xpu
```

e lo script micro Japan/Nankai legge:

```bash
KAN_DEVICE=xpu
DEEP_DEVICE=xpu
```

## Regola Jobs

Con Intel XPU usare:

```bash
JOBS=1
```

Motivo: `JOBS` avvia trial paralleli. Su CPU ha senso usare piu processi, ma su
una singola GPU Intel Arc piu processi KAN competono per la stessa VRAM e per lo
stesso device, rischiando rallentamenti, instabilita o out-of-memory.

Default consigliati:

```bash
KAN_DEVICE=xpu
DEEP_DEVICE=xpu
JOBS=1
```

Per CPU si puo continuare a usare:

```bash
KAN_DEVICE=cpu
JOBS=3
```

## Comando Forecast Micro 3d

Forecast Japan/Nankai 3d, finestra reale `2026-07-22 -> 2026-08-31`:

```bash
cd /mnt/git0/git/repository/DLvsWAVE

PYTHON_BIN=${HOME}/venvs/dlvswave-xpu/bin/python \
KAN_DEVICE=xpu \
DEEP_DEVICE=xpu \
JOBS=1 \
./commands/run_japan_nankai_3d_jul22_aug12_kan_micro4h.sh
```

Nota: il nome dello script contiene ancora `aug12` per continuita storica, ma il
forecast default e stato esteso fino a `2026-08-31`.

## Verifica GPU

Prima di lanciare un run lungo:

```bash
${HOME}/venvs/dlvswave-xpu/bin/python - <<'PY'
import torch
print("torch", torch.__version__)
print("xpu available", torch.xpu.is_available())
print("xpu devices", torch.xpu.device_count())
if torch.xpu.is_available():
    x = torch.randn(2000, 2000, device="xpu")
    print((x @ x).mean())
PY
```

Se `xpu available` non e `True`, non lanciare con `KAN_DEVICE=xpu`.

## Dipendenze XPU

La venv XPU e stata creata fuori da `/mnt/git0` per evitare problemi di spazio:

```bash
python3 -m venv ${HOME}/venvs/dlvswave-xpu
${HOME}/venvs/dlvswave-xpu/bin/python -m pip install -U pip setuptools wheel
${HOME}/venvs/dlvswave-xpu/bin/python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/xpu
${HOME}/venvs/dlvswave-xpu/bin/python -m pip install numpy scipy scikit-learn pillow pykan pyyaml matplotlib tqdm pandas
```

Non usare `pip --break-system-packages`.
