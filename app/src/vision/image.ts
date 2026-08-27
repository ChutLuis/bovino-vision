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

  return decodeJpegBytes(await new File(asset.localUri).arrayBuffer());
}

// The benchmark only receives bundled assets. Product photos arrive as local URIs.
export async function decodeJpegUri(uri: string): Promise<DecodedImage> {
  return decodeJpegBytes(await new File(uri).arrayBuffer());
}

export function normalizeExifOrientation(
  image: DecodedImage,
  orientation: number | null | undefined,
): DecodedImage {
  if (orientation == null || orientation < 2 || orientation > 8) {
    return image;
  }

  const swapsDimensions = orientation >= 5 && orientation <= 8;
  const width = swapsDimensions ? image.height : image.width;
  const height = swapsDimensions ? image.width : image.height;
  const rgba = new Uint8Array(width * height * 4);

  for (let sourceY = 0; sourceY < image.height; sourceY += 1) {
    for (let sourceX = 0; sourceX < image.width; sourceX += 1) {
      const [targetX, targetY] = orientedPosition(
        sourceX,
        sourceY,
        image.width,
        image.height,
        orientation,
      );
      const sourceOffset = (sourceY * image.width + sourceX) * 4;
      const targetOffset = (targetY * width + targetX) * 4;

      rgba[targetOffset] = image.rgba[sourceOffset];
      rgba[targetOffset + 1] = image.rgba[sourceOffset + 1];
      rgba[targetOffset + 2] = image.rgba[sourceOffset + 2];
      rgba[targetOffset + 3] = image.rgba[sourceOffset + 3];
    }
  }

  return { width, height, rgba };
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

function decodeJpegBytes(bytes: ArrayBuffer): DecodedImage {
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

function orientedPosition(
  x: number,
  y: number,
  sourceWidth: number,
  sourceHeight: number,
  orientation: number,
): [number, number] {
  switch (orientation) {
    case 2:
      return [sourceWidth - 1 - x, y];
    case 3:
      return [sourceWidth - 1 - x, sourceHeight - 1 - y];
    case 4:
      return [x, sourceHeight - 1 - y];
    case 5:
      return [y, x];
    case 6:
      return [sourceHeight - 1 - y, x];
    case 7:
      return [sourceHeight - 1 - y, sourceWidth - 1 - x];
    case 8:
      return [y, sourceWidth - 1 - x];
    default:
      return [x, y];
  }
}
