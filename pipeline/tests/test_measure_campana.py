"""Funciones puras de measure_campana: focal, distancia, nivel, corrección de paralaje, selección a 3 m y estado.

No carga el modelo ni lee fotos.
"""
import pytest

import measure_campana as mc


def test_focal_px_por_telefono():
    assert mc.focal_px(4096, 23) == pytest.approx(2616.9, abs=0.05)   # Xiaomi 15 Ultra
    assert mc.focal_px(4080, 27) == pytest.approx(3060.0, abs=1e-9)   # Galaxy A25
    assert mc.F35_POR_ANCHO == {4096: 23, 4080: 27}


def test_distancia_por_semejanza():
    assert mc.distancia_m(130.8, 2616.9) == pytest.approx(3.001, abs=5e-4)
    # Con un marcador de otro tamaño la distancia escala en proporción al lado real.
    assert mc.distancia_m(130.8, 2616.9, marker_cm=30.0) == pytest.approx(2 * mc.distancia_m(130.8, 2616.9))


def test_nivel_distancia_cortes():
    assert mc.nivel_distancia(2.74) == 2.5
    assert mc.nivel_distancia(2.76) == 3.0
    assert mc.nivel_distancia(3.24) == 3.0
    assert mc.nivel_distancia(3.26) == 3.5
    assert mc.nivel_distancia(1.0) == 2.5
    assert mc.nivel_distancia(9.0) == 3.5


def test_correccion_paralaje():
    assert mc.DELTA_PARALAJE_M == 0.50
    assert mc.corregir_area(100.0, 3.0) == pytest.approx(136.11, abs=0.01)
    assert mc.corregir_area(100.0, 3.0, delta_m=0.0) == 100.0
    # Cuanto más lejos el marcador, menor la corrección relativa.
    assert mc.corregir_area(100.0, 3.5) < mc.corregir_area(100.0, 2.5)


def _fila(fila, foto, d, estado="ok"):
    return {"fila": fila, "foto": foto, "distancia_m": d, "estado": estado}


def test_seleccion_3m_toma_cinco_con_desempate_por_foto():
    filas = [
        _fila("7", "IMG_a.jpg", 3.01),
        _fila("7", "IMG_b.jpg", 2.98),
        _fila("7", "IMG_c.jpg", 3.03),
        _fila("7", "IMG_d.jpg", 2.96),
        _fila("7", "IMG_e_2.jpg", 3.125),   # |d − 3| = 0.125, empata con IMG_e_1
        _fila("7", "IMG_e_1.jpg", 2.875),   # gana el desempate por nombre de foto
        _fila("7", "IMG_g.jpg", 3.40),
    ]
    assert mc.seleccionar_3m(filas) == {"IMG_a.jpg", "IMG_b.jpg", "IMG_c.jpg", "IMG_d.jpg", "IMG_e_1.jpg"}


def test_seleccion_3m_menos_de_cinco_y_por_vaca():
    filas = [
        _fila("1", "IMG_1a.jpg", 2.5),
        _fila("1", "IMG_1b.jpg", 3.5),
        _fila("1", "IMG_1c.jpg", 3.0, estado="sin_marcador"),
        _fila("1", "IMG_1d.jpg", "", estado="sin_vaca"),
        _fila("2", "IMG_2a.jpg", 3.0, estado="silueta_cortada"),
    ] + [_fila("3", f"IMG_3{i}.jpg", 3.0 + 0.01 * i) for i in range(9)]
    elegidas = mc.seleccionar_3m(filas)
    assert {f for f in elegidas if f.startswith("IMG_1")} == {"IMG_1a.jpg", "IMG_1b.jpg"}
    assert not any(f.startswith("IMG_2") for f in elegidas)
    assert {f for f in elegidas if f.startswith("IMG_3")} == {f"IMG_3{i}.jpg" for i in range(5)}


def test_prioridad_estado():
    assert mc.clasificar_estado(hay_vaca=False, hay_marcador=False, cortada=False) == "sin_vaca"
    assert mc.clasificar_estado(hay_vaca=False, hay_marcador=True, cortada=True) == "sin_vaca"
    assert mc.clasificar_estado(hay_vaca=True, hay_marcador=False, cortada=True) == "sin_marcador"
    assert mc.clasificar_estado(hay_vaca=True, hay_marcador=True, cortada=True) == "silueta_cortada"
    assert mc.clasificar_estado(hay_vaca=True, hay_marcador=True, cortada=False) == "ok"


def test_silueta_cortada_por_tamano_o_borde():
    W, H = 4096, 3072
    assert not mc.silueta_cortada((500, 400, 3500, 2600), W, H)
    assert mc.silueta_cortada((2, 400, 3500, 2600), W, H)          # pegada al borde izquierdo
    assert mc.silueta_cortada((500, 400, W - 3, 2600), W, H)       # pegada al borde derecho
    assert mc.silueta_cortada((50, 400, 50 + int(0.98 * W), 2600), W, H)   # más ancha que 0.97·W
    assert mc.silueta_cortada((500, 10, 3500, 10 + int(0.98 * H)), W, H)   # más alta que 0.97·H


def test_lado_medio_de_un_cuadrado():
    cuadrado = [[0, 0], [130.8, 0], [130.8, 130.8], [0, 130.8]]
    assert mc.lado_medio_px(cuadrado) == pytest.approx(130.8)
