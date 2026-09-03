import type { SQLiteDatabase } from 'expo-sqlite';

const DATABASE_VERSION = 2;

interface VersionRow {
  user_version: number;
}

export async function migrarBaseDeDatos(db: SQLiteDatabase): Promise<void> {
  await db.execAsync('PRAGMA journal_mode = WAL; PRAGMA foreign_keys = ON;');
  const row = await db.getFirstAsync<VersionRow>('PRAGMA user_version');
  const versionActual = row?.user_version ?? 0;

  if (versionActual >= DATABASE_VERSION) {
    return;
  }

  await db.withTransactionAsync(async () => {
    if (versionActual === 0) {
      await db.execAsync(`
        CREATE TABLE IF NOT EXISTS animal (
          id INTEGER PRIMARY KEY NOT NULL,
          arete TEXT NOT NULL UNIQUE,
          nombre TEXT,
          categoria TEXT
        );

        CREATE TABLE IF NOT EXISTS estimacion (
          id INTEGER PRIMARY KEY NOT NULL,
          animal_id INTEGER NOT NULL,
          peso_kg REAL NOT NULL,
          area_cm2 REAL NOT NULL,
          version_modelo TEXT NOT NULL,
          ruta_foto TEXT NOT NULL,
          timestamp TEXT NOT NULL,
          FOREIGN KEY (animal_id) REFERENCES animal(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_estimacion_animal_timestamp
          ON estimacion(animal_id, timestamp DESC);
      `);
    }

    if (versionActual === 1) {
      // SQLite cannot alter a foreign key in place: rebuild the table with
      // ON DELETE CASCADE so borrarEstimacion can drop an emptied animal.
      await db.execAsync(`
        CREATE TABLE estimacion_nueva (
          id INTEGER PRIMARY KEY NOT NULL,
          animal_id INTEGER NOT NULL,
          peso_kg REAL NOT NULL,
          area_cm2 REAL NOT NULL,
          version_modelo TEXT NOT NULL,
          ruta_foto TEXT NOT NULL,
          timestamp TEXT NOT NULL,
          FOREIGN KEY (animal_id) REFERENCES animal(id) ON DELETE CASCADE
        );

        INSERT INTO estimacion_nueva (
          id, animal_id, peso_kg, area_cm2, version_modelo, ruta_foto, timestamp
        )
        SELECT id, animal_id, peso_kg, area_cm2, version_modelo, ruta_foto, timestamp
        FROM estimacion;

        DROP TABLE estimacion;
        ALTER TABLE estimacion_nueva RENAME TO estimacion;

        CREATE INDEX IF NOT EXISTS idx_estimacion_animal_timestamp
          ON estimacion(animal_id, timestamp DESC);
      `);
    }

    await db.execAsync(`PRAGMA user_version = ${DATABASE_VERSION}`);
  });
}
