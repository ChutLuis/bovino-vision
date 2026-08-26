import type { ModelId } from './types';

export interface ModelAsset {
  id: ModelId;
  label: string;
  asset: number;
}

export interface PhotoAsset {
  id: string;
  label: string;
  source: string;
  asset: number;
}

export const MODELS: readonly ModelAsset[] = [
  {
    id: 'fp32',
    label: 'FP32',
    asset: require('../assets/models/yolo26n_seg_fp32.tflite'),
  },
  {
    id: 'w8a32',
    label: 'w8a32',
    asset: require('../assets/models/yolo26n_seg_w8a32.tflite'),
  },
];

export const PHOTOS: readonly PhotoAsset[] = [
  {
    id: '01_camelia',
    label: 'Camelia',
    source: 'WhatsApp Image 2026-06-05 at 08.08.01.jpeg',
    asset: require('../assets/photos/photo_01_camelia.jpeg'),
  },
  {
    id: '02_paulina',
    label: 'Paulina',
    source: 'WhatsApp Image 2026-06-05 at 08.08.25.jpeg',
    asset: require('../assets/photos/photo_02_paulina.jpeg'),
  },
  {
    id: '03_nohelia',
    label: 'Nohelia',
    source: 'WhatsApp Image 2026-06-05 at 08.00.21.jpeg',
    asset: require('../assets/photos/photo_03_nohelia.jpeg'),
  },
  {
    id: '04_ford',
    label: 'Ford',
    source: 'WhatsApp Image 2026-06-05 at 08.01.11.jpeg',
    asset: require('../assets/photos/photo_04_ford.jpeg'),
  },
  {
    id: '05_karina',
    label: 'Karina',
    source: 'WhatsApp Image 2026-06-05 at 08.02.30.jpeg',
    asset: require('../assets/photos/photo_05_karina.jpeg'),
  },
  {
    id: '06_selena',
    label: 'Selena',
    source: 'WhatsApp Image 2026-06-05 at 08.00.07.jpeg',
    asset: require('../assets/photos/photo_06_selena.jpeg'),
  },
  {
    id: '07_chiquita',
    label: 'Chiquita',
    source: 'WhatsApp Image 2026-06-05 at 08.01.47.jpeg',
    asset: require('../assets/photos/photo_07_chiquita.jpeg'),
  },
  {
    id: '08_mafer',
    label: 'Mafer',
    source: 'WhatsApp Image 2026-06-05 at 08.03.46.jpeg',
    asset: require('../assets/photos/photo_08_mafer.jpeg'),
  },
  {
    id: '09_daniela',
    label: 'Daniela',
    source: 'WhatsApp Image 2026-06-05 at 08.07.45.jpeg',
    asset: require('../assets/photos/photo_09_daniela.jpeg'),
  },
  {
    id: '10_mariita',
    label: 'Mariita',
    source: 'WhatsApp Image 2026-06-05 at 08.11.54.jpeg',
    asset: require('../assets/photos/photo_10_mariita.jpeg'),
  },
];
