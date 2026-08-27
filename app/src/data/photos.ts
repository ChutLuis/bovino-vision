import { Directory, File, Paths } from 'expo-file-system';

const photosDirectory = new Directory(Paths.document, 'wakx-fotos');

export async function guardarFotoPrivada(uri: string): Promise<string> {
  photosDirectory.create({ idempotent: true, intermediates: true });

  const origen = new File(uri);
  const extension = extensionSegura(origen.extension);
  const destino = new File(photosDirectory, `estimacion-${Date.now()}${extension}`);
  await origen.copy(destino);
  return destino.uri;
}

export function eliminarFotoPrivada(uri: string): void {
  const archivo = new File(uri);

  if (archivo.exists) {
    archivo.delete();
  }
}

function extensionSegura(extension: string): string {
  const normalizada = extension.toLowerCase();
  return normalizada === '.jpeg' || normalizada === '.jpg' ? normalizada : '.jpg';
}
