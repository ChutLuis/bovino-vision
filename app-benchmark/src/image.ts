import { Asset } from 'expo-asset';
import { File } from 'expo-file-system';
import { decode } from 'jpeg-js';

import { INPUT_SIZE } from './config';
import type { DecodedImage, PreparedImage } from './types';

export async function decodeBundledJpeg(assetModule: number): Promise<DecodedImage> {
  const asset = Asset.fromModule(assetModule);
  await asset.downloadAsync();

  if (asset.localUri == null) {
    throw new Error(`No se pudo obtener una URI local para ${asset.name}.`);
  }

  const bytes = await new File(asset.localUri).arrayBuffer();
  const decoded = decode(new Uint8Array(bytes), {
    useTArray: true,
    formatAsRGBA: true,
    tolerantDecoding: true,
    maxResolutionInMP: 20,
    maxMemoryUsageInMB: 128,
  });

  return {
    width: decoded.width,
    height: decoded.height,
    rgba: decoded.data,
  };
}

export function letterboxToNchw(image: DecodedImage): PreparedImage {
  const scale = Math.min(INPUT_SIZE / image.width, INPUT_SIZE / image.height);
  const contentWidth = Math.round(image.width * scale);
  const contentHeight = Math.round(image.height * scale);
  const padX = Math.floor((INPUT_SIZE - contentWidth) / 2);
  const padY = Math.floor((INPUT_SIZE - contentHeight) / 2);
  const planeSize = INPUT_SIZE * INPUT_SIZE;
  const input = new Float32Array(planeSize * 3);
  input.fill(114 / 255);

  for (let y = 0; y < contentHeight; y += 1) {
    const sourceY = Math.max(
      0,
      Math.min(image.height - 1, (y + 0.5) / scale - 0.5),
    );
    const y0 = Math.floor(sourceY);
    const y1 = Math.min(image.height - 1, y0 + 1);
    const wy = sourceY - y0;

    for (let x = 0; x < contentWidth; x += 1) {
      const sourceX = Math.max(
        0,
        Math.min(image.width - 1, (x + 0.5) / scale - 0.5),
      );
      const x0 = Math.floor(sourceX);
      const x1 = Math.min(image.width - 1, x0 + 1);
      const wx = sourceX - x0;
      const destination = (padY + y) * INPUT_SIZE + padX + x;
      const topLeft = (y0 * image.width + x0) * 4;
      const topRight = (y0 * image.width + x1) * 4;
      const bottomLeft = (y1 * image.width + x0) * 4;
      const bottomRight = (y1 * image.width + x1) * 4;

      for (let channel = 0; channel < 3; channel += 1) {
        const top =
          image.rgba[topLeft + channel] * (1 - wx) +
          image.rgba[topRight + channel] * wx;
        const bottom =
          image.rgba[bottomLeft + channel] * (1 - wx) +
          image.rgba[bottomRight + channel] * wx;
        input[channel * planeSize + destination] =
          (top * (1 - wy) + bottom * wy) / 255;
      }
    }
  }

  return {
    input,
    letterbox: {
      original_width: image.width,
      original_height: image.height,
      scale,
      content_width: contentWidth,
      content_height: contentHeight,
      pad_x: padX,
      pad_y: padY,
    },
  };
}

export function asArrayBuffer(values: Float32Array): ArrayBuffer {
  return values.buffer.slice(
    values.byteOffset,
    values.byteOffset + values.byteLength,
  ) as ArrayBuffer;
}
