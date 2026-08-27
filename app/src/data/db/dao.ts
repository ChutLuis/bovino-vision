import * as SQLite from 'expo-sqlite';
import type { SQLiteDatabase } from 'expo-sqlite';

import { migrarBaseDeDatos } from './schema';

export interface Animal {
  id: number;
  arete: string;
  nombre: string | null;
  categoria: string | null;
}

export interface AnimalConResumen extends Animal {
  estimaciones_count: number;
  ultimo_peso_kg: number | null;
  ultima_estimacion: string | null;
}

export interface NuevaEstimacion {
  animal_id: number;
  peso_kg: number;
  area_cm2: number;
  version_modelo: string;
  ruta_foto: string;
  timestamp: string;
}

export interface Estimacion extends NuevaEstimacion {
  id: number;
}

export interface FilaExportacion {
  arete: string;
  nombre: string | null;
  categoria: string | null;
  peso_kg: number;
  area_cm2: number;
  version_modelo: string;
  ruta_foto: string;
  timestamp: string;
}

let databasePromise: Promise<SQLiteDatabase> | null = null;

export async function guardarAnimal(input: Omit<Animal, 'id'>): Promise<Animal> {
  const arete = input.arete.trim();

  if (arete.length === 0) {
    throw new Error('El arete es obligatorio.');
  }

  const db = await obtenerBaseDeDatos();
  await db.runAsync(
    `INSERT INTO animal (arete, nombre, categoria)
     VALUES (?, ?, ?)
     ON CONFLICT(arete) DO UPDATE SET
       nombre = COALESCE(excluded.nombre, animal.nombre),
       categoria = COALESCE(excluded.categoria, animal.categoria)`,
    arete,
    textoOpcional(input.nombre),
    textoOpcional(input.categoria),
  );

  const animal = await db.getFirstAsync<Animal>(
    'SELECT id, arete, nombre, categoria FROM animal WHERE arete = ?',
    arete,
  );

  if (animal == null) {
    throw new Error('No se pudo recuperar el animal guardado.');
  }

  return animal;
}

export async function guardarEstimacion(input: NuevaEstimacion): Promise<Estimacion> {
  const db = await obtenerBaseDeDatos();
  const result = await db.runAsync(
    `INSERT INTO estimacion (
      animal_id, peso_kg, area_cm2, version_modelo, ruta_foto, timestamp
    ) VALUES (?, ?, ?, ?, ?, ?)`,
    input.animal_id,
    input.peso_kg,
    input.area_cm2,
    input.version_modelo,
    input.ruta_foto,
    input.timestamp,
  );
  const id = Number(result.lastInsertRowId);
  const estimacion = await db.getFirstAsync<Estimacion>(
    `SELECT id, animal_id, peso_kg, area_cm2, version_modelo, ruta_foto, timestamp
     FROM estimacion WHERE id = ?`,
    id,
  );

  if (estimacion == null) {
    throw new Error('No se pudo recuperar la estimacion guardada.');
  }

  return estimacion;
}

export async function listarAnimales(): Promise<AnimalConResumen[]> {
  const db = await obtenerBaseDeDatos();
  return db.getAllAsync<AnimalConResumen>(`
    SELECT
      animal.id,
      animal.arete,
      animal.nombre,
      animal.categoria,
      COUNT(estimacion.id) AS estimaciones_count,
      (
        SELECT peso_kg FROM estimacion
        WHERE animal_id = animal.id
        ORDER BY timestamp DESC LIMIT 1
      ) AS ultimo_peso_kg,
      (
        SELECT timestamp FROM estimacion
        WHERE animal_id = animal.id
        ORDER BY timestamp DESC LIMIT 1
      ) AS ultima_estimacion
    FROM animal
    LEFT JOIN estimacion ON estimacion.animal_id = animal.id
    GROUP BY animal.id
    ORDER BY animal.arete COLLATE NOCASE ASC
  `);
}

export async function listarEstimaciones(animalId: number): Promise<Estimacion[]> {
  const db = await obtenerBaseDeDatos();
  return db.getAllAsync<Estimacion>(
    `SELECT id, animal_id, peso_kg, area_cm2, version_modelo, ruta_foto, timestamp
     FROM estimacion WHERE animal_id = ? ORDER BY timestamp DESC`,
    animalId,
  );
}

export async function listarFilasExportacion(): Promise<FilaExportacion[]> {
  const db = await obtenerBaseDeDatos();
  return db.getAllAsync<FilaExportacion>(`
    SELECT
      animal.arete,
      animal.nombre,
      animal.categoria,
      estimacion.peso_kg,
      estimacion.area_cm2,
      estimacion.version_modelo,
      estimacion.ruta_foto,
      estimacion.timestamp
    FROM estimacion
    INNER JOIN animal ON animal.id = estimacion.animal_id
    ORDER BY estimacion.timestamp DESC
  `);
}

async function obtenerBaseDeDatos(): Promise<SQLiteDatabase> {
  if (databasePromise == null) {
    databasePromise = SQLite.openDatabaseAsync('wakx.db').then(async (db) => {
      await migrarBaseDeDatos(db);
      return db;
    });
  }

  try {
    return await databasePromise;
  } catch (error) {
    databasePromise = null;
    throw error;
  }
}

function textoOpcional(value: string | null): string | null {
  const texto = value?.trim() ?? '';
  return texto.length === 0 ? null : texto;
}
