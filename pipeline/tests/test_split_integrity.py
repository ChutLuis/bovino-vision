"""Integridad del split por animal: inventario, alias por arete y ausencia de fuga en disco."""
import csv
import hashlib
from pathlib import Path

import pytest

import build_yolo_seg_dataset as b

ROOT = Path(__file__).resolve().parent.parent
DS = ROOT / "data/field/seg_dataset"
VAL_CLEAN = ROOT / "data/val_clean"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def test_inv_duplicated_aretes_are_declared_as_aliases():
    assert b.duplicated_aretes_without_alias() == {}


def test_alias_group_expands_val_animals():
    assert b.expand_val_animals({"KARINA"}) == {"KARINA", "IRIS"}
    assert b.expand_val_animals({"PERLA"}) == {"PERLA"}


def test_animal_id_from_folder():
    assert b.animal_id("3685") == "CHIQUITA"
    assert b.animal_id("6703_3") in b.ALIASES["236703"]
    assert b.animal_id("6706").startswith("unk_")


def test_train_stem_roundtrip():
    assert b.train_stem_to_animal("train_NICOL_ESTEFANIA__IMG_1") == "NICOL ESTEFANIA"
    assert b.train_stem_to_animal("train_rep1206_iris") == "IRIS"


@pytest.fixture
def on_disk():
    if not (DS / "images/train").exists() or not (VAL_CLEAN / "manifest.csv").exists():
        pytest.skip("sin data/field/seg_dataset o sin val_clean")
    train = sorted((DS / "images/train").iterdir())
    val = sorted((DS / "images/val").iterdir())
    val_names = {r["cow_id"] for r in csv.DictReader(open(VAL_CLEAN / "manifest.csv"))}
    return train, val, val_names


def test_no_leak_by_hash_on_disk(on_disk):
    train, val, _ = on_disk
    th = {sha(p) for p in train}
    assert not (th & {sha(p) for p in val}), "misma imagen en train y val"
    assert not (th & {sha(p) for p in (VAL_CLEAN / "images").iterdir()}), "imagen de val_clean en train"


def test_no_leak_by_name_or_arete_on_disk(on_disk):
    """Falla mientras el dataset en disco tenga un animal que comparta arete con uno de val.
    Solución: regenerar con build_yolo_seg_dataset.py (aplica ALIASES)."""
    train, _, val_names = on_disk
    val_animals = b.expand_val_animals(val_names)
    leaks = sorted({p.stem for p in train if b.train_stem_to_animal(p.stem) in val_animals})
    assert leaks == [], f"animales de val en train (nombre o arete compartido): {leaks}"


def test_no_unknown_identity_in_train_on_disk(on_disk):
    """Falla mientras haya carpetas unk_* en train. Solución: regenerar el dataset (o --include-unknown a sabiendas)."""
    train, _, _ = on_disk
    unk = sorted({b.train_stem_to_animal(p.stem) for p in train if b.train_stem_to_animal(p.stem).startswith("unk")})
    assert unk == [], f"animales sin identidad en train: {unk}"


def test_data_yaml_has_no_absolute_path():
    y = DS / "data.yaml"
    if not y.exists():
        pytest.skip("sin data.yaml")
    txt = y.read_text()
    assert "/home/" not in txt and not any(line.startswith("path:") and line.split(":", 1)[1].strip().startswith("/") for line in txt.splitlines()), \
        "data.yaml con ruta absoluta; regenerar con build_yolo_seg_dataset.py"
