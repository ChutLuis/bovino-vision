import { Asset } from 'expo-asset';
import {
  loadTensorflowModel,
  type TfliteModel,
} from 'react-native-fast-tflite';

import {
  DETECTION_ROWS,
  DETECTION_ROW_SIZE,
  INPUT_SIZE,
  MASK_CHANNELS,
  MASK_SIZE,
} from './config';

export async function loadBundledModel(assetModule: number): Promise<TfliteModel> {
  const asset = Asset.fromModule(assetModule);
  await asset.downloadAsync();

  if (asset.localUri == null) {
    throw new Error(`No se pudo obtener una URI local para ${asset.name}.`);
  }

  const model = await loadTensorflowModel({ url: asset.localUri }, []);
  assertModelContract(model);
  return model;
}

function assertModelContract(model: TfliteModel): void {
  const input = model.inputs[0];
  const output0 = model.outputs[0];
  const output1 = model.outputs[1];

  if (
    input == null ||
    input.dataType !== 'float32' ||
    !sameShape(input.shape, [1, 3, INPUT_SIZE, INPUT_SIZE])
  ) {
    throw new Error(
      `Contrato de entrada inesperado: ${describeTensor(input)}. Se esperaba float32 [1,3,640,640].`,
    );
  }

  if (
    output0 == null ||
    output0.dataType !== 'float32' ||
    !sameShape(output0.shape, [1, DETECTION_ROWS, DETECTION_ROW_SIZE])
  ) {
    throw new Error(
      `Contrato de salida 0 inesperado: ${describeTensor(output0)}. Se esperaba float32 [1,300,38].`,
    );
  }

  if (
    output1 == null ||
    output1.dataType !== 'float32' ||
    !sameShape(output1.shape, [1, MASK_CHANNELS, MASK_SIZE, MASK_SIZE])
  ) {
    throw new Error(
      `Contrato de salida 1 inesperado: ${describeTensor(output1)}. Se esperaba float32 [1,32,160,160].`,
    );
  }
}

function sameShape(actual: number[], expected: number[]): boolean {
  return actual.length === expected.length && actual.every((value, index) => value === expected[index]);
}

function describeTensor(
  tensor: { dataType: string; shape: number[] } | undefined,
): string {
  if (tensor == null) {
    return 'ausente';
  }

  return `${tensor.dataType} [${tensor.shape.join(',')}]`;
}
