# Deploy en NVIDIA Jetson Orin Nano

Guía paso a paso **probada en JetPack 6.2.1** (validado 2026-05-22: smoke test E2E pasa, YOLO26 + ArUco + ráfaga funcionan en GPU del Orin). El **código Python** es portable entre macOS y Jetson; lo que cambia es el **entorno** (PyTorch ARM, cuSPARSELt, drivers V4L2). Esta guía cubre exactamente eso.

> **Resumen ejecutivo:** El stack JP6.2 requiere torch 2.5 (no 2.3), cuSPARSELt instalada aparte, numpy fijado en 1.x, opencv-contrib-python ≤4.12, y torchvision construido desde source. Cada uno se explica abajo con su razón.

---

## 0. Pre-requisitos

- Jetson Orin Nano flasheado con **JetPack 6.2.x** (trae CUDA 12.6, cuDNN 9.3, TensorRT 10.3 preinstalados).
- Cámara Logitech C270 USB (o equivalente).
- Acceso al Jetson (monitor + teclado, o SSH).
- Internet (solo durante setup — la captura en finca es offline).

Verificar la versión exacta:
```bash
sudo apt-cache show nvidia-jetpack | grep -E "Version|Package" | head -4
cat /etc/nv_tegra_release | head -2
```
Esperado: `Version: 6.2.x+...` y `R36 (release), REVISION: 4.x` (L4T 36.4.x).

---

## 1. Transferir el repo

```bash
git clone git@github.com:ChutLuis/thesis-weigh-estimation.git ~/Documents/thesis-weigh-estimation
cd ~/Documents/thesis-weigh-estimation/prototype
```

---

## 2. Verificar la cámara C270

```bash
ls /dev/video*
v4l2-ctl --list-devices
v4l2-ctl --device=/dev/video0 --list-formats-ext | head -20
```
Si la C270 no es `video0`, edita `config.yaml` → `camera.index: 1` (o el índice que aparezca).

---

## 3. Python venv

JetPack 6.2 trae Python 3.10 preinstalado.

```bash
python3 -m venv ~/venv-thesis
source ~/venv-thesis/bin/activate
pip install --upgrade pip
```

---

## 4. PyTorch 2.5 (cuDNN 9 compatible) — desde NVIDIA, no PyPI

**No uses `pip install torch` genérico** (te da CPU-only para ARM) ni el wheel `torch 2.3` antiguo de NVIDIA Forums (compilado contra cuDNN 8, que JP6.2 ya no incluye).

```bash
pip install --no-cache https://developer.download.nvidia.com/compute/redist/jp/v61/pytorch/torch-2.5.0a0+872d972e41.nv24.08.17622132-cp310-cp310-linux_aarch64.whl
```

> **Por qué este wheel exacto:** `torch 2.5.0a0+...nv24.08` es la build de NVIDIA compilada contra cuDNN 9 (la que trae JP6.2). El wheel `torch 2.3` que el thread de Forums sugiere por default es de la era cuDNN 8 — en JP6.2 falla con `ImportError: libcudnn.so.8: cannot open shared object file`.

**Verificación parcial (debe fallar todavía por cuSPARSELt — eso es esperado):**
```bash
python3 -c "import torch; print(torch.__version__, torch.cuda.is_available())"
```
Si sale `ImportError: libcusparseLt.so.0: cannot open shared object file` → sigue al paso 5. Eso es lo que toca.

---

## 5. cuSPARSELt 0.7.1 — instalar aparte (JetPack no la trae)

El wheel torch 2.5 depende de cuSPARSELt (`libcusparseLt.so.0`), una librería NVIDIA para álgebra lineal con tensores dispersos. **JetPack 6.2 NO la instala por defecto** — hay que instalarla manual desde el repo local de NVIDIA.

```bash
cd ~
wget https://developer.download.nvidia.com/compute/cusparselt/0.7.1/local_installers/cusparselt-local-tegra-repo-ubuntu2204-0.7.1_1.0-1_arm64.deb

sudo dpkg -i cusparselt-local-tegra-repo-ubuntu2204-0.7.1_1.0-1_arm64.deb
sudo cp /var/cusparselt-local-tegra-repo-ubuntu2204-0.7.1/cusparselt-*-keyring.gpg /usr/share/keyrings/
sudo apt-get update
sudo apt-get install -y libcusparselt0 libcusparselt-dev
```

**Verificación de torch + GPU:**
```bash
python3 -c "import torch; print('torch:', torch.__version__); print('CUDA:', torch.cuda.is_available()); print('Device:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'N/A')"
```
Esperado:
```
torch: 2.5.0a0+872d972e41.nv24.08
CUDA: True
Device: Orin
```

---

## 6. numpy 1.x — antes que torch lo necesite

El wheel torch de NVIDIA fue compilado mediados-2024, contra numpy 1.x ABI. **Si numpy 2.x está instalado, todo `import torch` lanza warning de ABI y fallan operaciones de tensor.**

```bash
pip install 'numpy<2'
```

Re-verifica torch SIN warning de NumPy:
```bash
python3 -c "import torch, numpy; print('numpy:', numpy.__version__); print('torch:', torch.__version__, 'CUDA:', torch.cuda.is_available())"
```
Esperado: salida limpia, **sin** el bloque rojo `A module that was compiled using NumPy 1.x cannot be run in NumPy 2.2.6...`.

---

## 7. torchvision 0.20 — build desde source

NVIDIA no hostea wheel binario de torchvision para JP6.2 que matchee con torch 2.5. PyPI sí ofrece `torchvision 0.27` para aarch64 — **pero es CPU-only y no enlaza con la torch 2.5 CUDA de NVIDIA**. Toca buildear desde source. Demora ~25 min en Orin Nano pero se hace una sola vez.

```bash
sudo apt-get install -y libjpeg-dev zlib1g-dev libpython3-dev libopenblas-dev libavcodec-dev libavformat-dev libswscale-dev

cd ~
git clone --branch release/0.20 https://github.com/pytorch/vision torchvision-build
cd torchvision-build
export BUILD_VERSION=0.20.0
pip install . --no-build-isolation
```

> **NO uses `python3 setup.py install --user`** (lo que dice el blog NinjaLABO). Eso instala fuera del venv en `~/.local/`, y el venv-thesis no lee `.local`. Usa `pip install .` que sí respeta el venv activo.

**Verificación:**
```bash
cd ~
python3 -c "
import torch, torchvision
print('torch:', torch.__version__, 'CUDA:', torch.cuda.is_available())
print('torchvision:', torchvision.__version__, 'from:', torchvision.__file__)
import torchvision.ops
print('nms registered:', 'nms' in dir(torchvision.ops))
"
```
**Lo crítico es `nms registered: True`** — eso confirma que el C++ de torchvision se enlazó con torch.

Si te sale `RuntimeError: operator torchvision::nms does not exist` o `ModuleNotFoundError`, ver troubleshooting (§ 11).

---

## 8. Resto de dependencias del prototipo

```bash
cd ~/Documents/thesis-weigh-estimation/prototype
pip install -r requirements.txt
```

> **Si `pip install` upgradea numpy a 2.x otra vez** (porque opencv-contrib-python 4.13 lo arrastra), tu requirements.txt tiene los pines correctos (`numpy<2`, `opencv-contrib-python<4.13`) — pero re-confirma:
> ```bash
> pip install 'numpy<2' 'opencv-contrib-python<4.13'
> ```

**El conflicto de OpenCV** (importante): ultralytics declara `opencv-python>=4.6` como dep, y nosotros pedimos `opencv-contrib-python`. Pip instala ambos, escriben al mismo `cv2/` directory y se sobrescriben. La opencv-python no-contrib **no tiene aruco**. Si vez `AttributeError: module 'cv2' has no attribute 'aruco'`:

```bash
pip uninstall -y opencv-python opencv-contrib-python
pip install 'opencv-contrib-python<4.13'
```

(El warning de pip "ultralytics requires opencv-python>=4.6.0, which is not installed" es solo metadatos — ultralytics importa `cv2`, que opencv-contrib-python sí provee.)

---

## 9. Ajustes de `config.yaml` para Jetson

```yaml
camera:
  index: 0          # o 1 según v4l2-ctl --list-devices
  width: 1280
  height: 720
  fps: 30

cow_detector:
  model: models/yolo26n.pt
  device: "cuda:0"  # explícito, importante en Jetson
  min_confidence: 0.50
```

---

## 10. Pruebas progresivas

### 10.1 Smoke test (sin cámara, sin GUI) — verificación final
```bash
cd ~/Documents/thesis-weigh-estimation/prototype
curl -sS -L -A "Mozilla/5.0" -o /tmp/test_cow.jpg "https://images.unsplash.com/photo-1500595046743-cd271d694d30?w=800"
python3 tests/test_pipeline_smoke.py
```
Esperado:
```
frame: (531, 800, 3)  markers=1  cows=4
  marker id=3  side=179px
  cow conf=0.95  ...
OK — pipeline smoke test passed
```

### 10.2 Visor en vivo (requiere monitor o X-forwarding)
```bash
python3 src/detect_live.py
```
Si `cv2.imshow` falla → ver troubleshooting § 11.

### 10.3 Captura headless (modo producción)
```bash
python3 src/capture.py --max-bursts 3
ls data/captures/aruco_*/
cat data/captures/aruco_*/[!_]*.json
```

---

## 11. Troubleshooting (todos vistos en deploy real)

| Síntoma | Causa | Solución |
|---|---|---|
| `ImportError: libcudnn.so.8: cannot open shared object file` | Wheel torch 2.3 (cuDNN 8 era) en JP6.2 (cuDNN 9) | Reinstalar torch 2.5 (paso 4) |
| `ImportError: libcusparseLt.so.0: cannot open shared object file` | cuSPARSELt no instalada | Paso 5 |
| `UserWarning: Failed to initialize NumPy: _ARRAY_API not found` y/o `Numpy is not available` | numpy 2.x vs torch wheel numpy 1.x | `pip install 'numpy<2'` |
| `RuntimeError: operator torchvision::nms does not exist` desde `~/torchvision-build/` | Importando source dir, no install | `cd ~` antes de importar |
| `ModuleNotFoundError: No module named 'torchvision'` después de `python3 setup.py install --user` | Instaló en `~/.local`, venv no lo ve | Reinstalar con `pip install .` (sin `--user`) |
| `AttributeError: module 'cv2' has no attribute 'aruco'` | opencv-python sin contrib sobreescribió a opencv-contrib-python | `pip uninstall opencv-python; pip install --force-reinstall opencv-contrib-python` |
| Cámara no abre (`cv2.VideoCapture(0)`) | Permiso o índice incorrecto | `sudo usermod -aG video $USER`, verificar con `v4l2-ctl --list-devices` |
| `cv2.imshow` cuelga o crashea | OpenCV sin GUI build | Headless es el modo de producción de todos modos. Para dev, usar `pip install opencv-python` con GUI (conflicto resuelto solo en dev) |
| `pypi.jetson-ai-lab.dev` falla DNS | Tu red bloquea o tu DNS no resuelve | Skip ese índice, usar `developer.download.nvidia.com` directo |
| Marcadores no detectados a >3 m | Marker chico en píxeles | Bajar `min_marker_size_px` o imprimir más grande (18-20 cm) |
| FPS < 5 con CUDA disponible | Inferencia accidentalmente en CPU | Forzar `device: cuda:0` en config; verificar con `nvidia-smi` que GPU está activa |

---

## 12. Optimización (después del setup base)

### TensorRT FP16 export (2–4× FPS)
```bash
python3 -c "
from ultralytics import YOLO
m = YOLO('models/yolo26n.pt')
m.export(format='engine', half=True, device=0)
"
```
Luego en `config.yaml`:
```yaml
cow_detector:
  model: models/yolo26n.engine
```

---

## 13. Servicio systemd (operación 24/7 en finca)

```bash
sudo tee /etc/systemd/system/cow-capture.service <<'EOF'
[Unit]
Description=Cow weight estimation capture pipeline
After=network.target

[Service]
Type=simple
User=chutluis
WorkingDirectory=/home/chutluis/Documents/thesis-weigh-estimation/prototype
Environment="PATH=/home/chutluis/venv-thesis/bin:/usr/bin"
ExecStart=/home/chutluis/venv-thesis/bin/python3 src/capture.py --config config.yaml
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now cow-capture
sudo journalctl -u cow-capture -f
```

---

## 14. Checklist final antes de instalar en finca

- [x] Smoke test pasa (`python3 tests/test_pipeline_smoke.py`)
- [ ] Live viewer abre cámara C270 (`python3 src/detect_live.py`)
- [ ] FPS razonable (>15 esperado en Orin Nano con `device: cuda:0`)
- [ ] Burst real escribe en `data/captures/aruco_*/`
- [ ] Marcadores impresos en PVC sintra (15 cm), DICT_6X6_250, IDs únicos
- [ ] Service systemd habilitado y reiniciable
- [ ] Disco con espacio (~1 GB por semana de capturas)
- [ ] Sincronización temporal validada (timestamps UTC en metadata.json)
