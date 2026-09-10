# Entorno en NVIDIA Jetson Orin Nano

La Jetson Orin Nano fue la plataforma del prototipo de captura autónoma (`capture.py`, `detect_live.py`), probada
con JetPack 6.2.1 el 22 de mayo de 2026: smoke test E2E, YOLO26 y ArUco en la GPU del Orin. El código Python es el
mismo que en PC; lo que cambia es el entorno: el stack de JetPack 6.2 exige torch 2.5 (no 2.3), cuSPARSELt instalada
aparte, numpy fijado en 1.x, opencv-contrib-python ≤ 4.12 y torchvision compilado desde fuente. Cada punto se explica
abajo con su razón.

## 0. Prerrequisitos

- Jetson Orin Nano con JetPack 6.2.x (CUDA 12.6, cuDNN 9.3, TensorRT 10.3 preinstalados).
- Cámara USB (Logitech C270 o equivalente).
- Internet solo durante la instalación; la captura en finca es offline.

```bash
sudo apt-cache show nvidia-jetpack | grep -E "Version|Package" | head -4
cat /etc/nv_tegra_release | head -2      # esperado: R36 (release), REVISION: 4.x (L4T 36.4.x)
```

## 1. Repositorio y cámara

```bash
git clone https://github.com/ChutLuis/bovino-vision.git ~/bovino-vision
cd ~/bovino-vision/pipeline
ls /dev/video*
v4l2-ctl --list-devices
v4l2-ctl --device=/dev/video0 --list-formats-ext | head -20
```

Si la C270 no es `video0`, cambia `camera.index` en `config.yaml`.

## 2. Entorno Python

JetPack 6.2 trae Python 3.10.

```bash
python3 -m venv ~/venv-bovino
source ~/venv-bovino/bin/activate
pip install --upgrade pip
```

## 3. PyTorch 2.5 de NVIDIA (compatible con cuDNN 9)

No sirve `pip install torch` genérico (CPU-only en ARM) ni el wheel `torch 2.3` de los foros de NVIDIA (compilado
contra cuDNN 8, que JetPack 6.2 ya no incluye: falla con `ImportError: libcudnn.so.8`).

```bash
pip install --no-cache https://developer.download.nvidia.com/compute/redist/jp/v61/pytorch/torch-2.5.0a0+872d972e41.nv24.08.17622132-cp310-cp310-linux_aarch64.whl
python3 -c "import torch; print(torch.__version__, torch.cuda.is_available())"
```

En este punto `import torch` falla con `ImportError: libcusparseLt.so.0`; es lo esperado y se resuelve en el paso 4.

## 4. cuSPARSELt 0.7.1

El wheel de torch 2.5 depende de cuSPARSELt y JetPack 6.2 no la instala.

```bash
cd ~
wget https://developer.download.nvidia.com/compute/cusparselt/0.7.1/local_installers/cusparselt-local-tegra-repo-ubuntu2204-0.7.1_1.0-1_arm64.deb
sudo dpkg -i cusparselt-local-tegra-repo-ubuntu2204-0.7.1_1.0-1_arm64.deb
sudo cp /var/cusparselt-local-tegra-repo-ubuntu2204-0.7.1/cusparselt-*-keyring.gpg /usr/share/keyrings/
sudo apt-get update
sudo apt-get install -y libcusparselt0 libcusparselt-dev
python3 -c "import torch; print('torch:', torch.__version__); print('CUDA:', torch.cuda.is_available()); print('Device:', torch.cuda.get_device_name(0))"
```

Esperado: `torch: 2.5.0a0+872d972e41.nv24.08`, `CUDA: True`, `Device: Orin`.

## 5. numpy 1.x

El wheel de NVIDIA se compiló contra la ABI de numpy 1.x. Con numpy 2.x cada `import torch` avisa de ABI y fallan
operaciones de tensor.

```bash
pip install 'numpy<2'
python3 -c "import torch, numpy; print('numpy:', numpy.__version__); print('torch:', torch.__version__, 'CUDA:', torch.cuda.is_available())"
```

## 6. torchvision 0.20 desde fuente

NVIDIA no publica un wheel de torchvision para JetPack 6.2 que case con torch 2.5, y el de PyPI para aarch64 es
CPU-only. Compilar tarda unos 25 minutos en el Orin Nano y se hace una vez.

```bash
sudo apt-get install -y libjpeg-dev zlib1g-dev libpython3-dev libopenblas-dev libavcodec-dev libavformat-dev libswscale-dev
cd ~
git clone --branch release/0.20 https://github.com/pytorch/vision torchvision-build
cd torchvision-build
export BUILD_VERSION=0.20.0
pip install . --no-build-isolation
cd ~
python3 -c "
import torch, torchvision, torchvision.ops
print('torchvision:', torchvision.__version__, 'from:', torchvision.__file__)
print('nms registered:', 'nms' in dir(torchvision.ops))
"
```

Usa `pip install .`, no `python3 setup.py install --user`: este último instala en `~/.local`, fuera del venv. Lo que
confirma el enlace con torch es `nms registered: True`, y hay que importar desde fuera de `~/torchvision-build/`.

## 7. Resto de dependencias

```bash
cd ~/bovino-vision/pipeline
pip install -r requirements.txt
pip install 'numpy<2' 'opencv-contrib-python<4.13'    # por si alguna dependencia subió numpy
```

`ultralytics` declara `opencv-python` y el pipeline necesita `opencv-contrib-python` (la versión sin contrib no trae
`aruco`). Si los dos quedan instalados se pisan el directorio `cv2/`; ante `AttributeError: module 'cv2' has no
attribute 'aruco'`:

```bash
pip uninstall -y opencv-python opencv-contrib-python
pip install 'opencv-contrib-python<4.13'
```

El aviso de pip "ultralytics requires opencv-python" es solo metadatos: ultralytics importa `cv2`, que
opencv-contrib-python provee.

## 8. `config.yaml` en la Jetson

```yaml
camera:
  index: 0          # o el que dé v4l2-ctl --list-devices
  width: 1280
  height: 720
  fps: 30

cow_detector:
  model: models/yolo26n.pt
  device: "cuda:0"  # explícito; en PC se deja "" (auto)
  min_confidence: 0.50
```

## 9. Pruebas

```bash
cd ~/bovino-vision/pipeline
cp /ruta/a/una/foto_con_vaca.jpg /tmp/test_cow.jpg
python3 tests/test_pipeline_smoke.py        # esperado: markers=1, cows>=1, "OK — pipeline smoke test passed"
python3 src/detect_live.py                  # visor en vivo; requiere monitor o X forwarding
python3 src/capture.py --max-bursts 3       # captura headless; escribe data/captures/aruco_*/
```

## 10. Problemas vistos en el despliegue real

| Síntoma | Causa | Solución |
|---|---|---|
| `ImportError: libcudnn.so.8` | Wheel torch 2.3 (cuDNN 8) en JetPack 6.2 (cuDNN 9) | Paso 3 |
| `ImportError: libcusparseLt.so.0` | cuSPARSELt no instalada | Paso 4 |
| `Failed to initialize NumPy: _ARRAY_API not found` o `Numpy is not available` | numpy 2.x con un torch compilado contra 1.x | `pip install 'numpy<2'` |
| `RuntimeError: operator torchvision::nms does not exist` | Se importa desde `~/torchvision-build/` | Importar desde otro directorio |
| `ModuleNotFoundError: No module named 'torchvision'` tras `setup.py install --user` | Quedó en `~/.local`, fuera del venv | `pip install .` sin `--user` |
| `AttributeError: module 'cv2' has no attribute 'aruco'` | opencv-python sin contrib pisó a opencv-contrib-python | Paso 7 |
| La cámara no abre | Permiso o índice | `sudo usermod -aG video $USER`; `v4l2-ctl --list-devices` |
| `cv2.imshow` cuelga | OpenCV sin GUI | La producción es headless; para depurar, `pip install opencv-python` con GUI |
| `pypi.jetson-ai-lab.dev` no resuelve | Red o DNS | Usar `developer.download.nvidia.com` directo |
| Marcadores no detectados a más de 3 m | Marcador pequeño en píxeles | Bajar `min_marker_size_px` o imprimir a 18–20 cm |
| FPS < 5 con CUDA disponible | Inferencia en CPU | `device: cuda:0` en `config.yaml`; comprobar con `nvidia-smi` |

## 11. Opcionales

TensorRT FP16 (2–4× FPS):

```bash
python3 -c "from ultralytics import YOLO; YOLO('models/yolo26n.pt').export(format='engine', half=True, device=0)"
# y en config.yaml: cow_detector.model: models/yolo26n.engine
```

Servicio systemd para operación continua (sustituir `USUARIO`):

```ini
[Unit]
Description=Captura de ráfagas para estimación de peso bovino
After=network.target

[Service]
Type=simple
User=USUARIO
WorkingDirectory=/home/USUARIO/bovino-vision/pipeline
Environment="PATH=/home/USUARIO/venv-bovino/bin:/usr/bin"
ExecStart=/home/USUARIO/venv-bovino/bin/python3 src/capture.py --config config.yaml
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload && sudo systemctl enable --now cow-capture && journalctl -u cow-capture -f
```
