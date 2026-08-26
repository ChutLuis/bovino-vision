import * as Device from 'expo-device';

import type { DeviceInfo } from './types';

export function collectDeviceInfo(): DeviceInfo {
  return {
    brand: Device.brand,
    manufacturer: Device.manufacturer,
    model_name: Device.modelName,
    model_id: Device.modelId == null ? null : String(Device.modelId),
    os_name: Device.osName,
    os_version: Device.osVersion,
    android_api_level: Device.platformApiLevel,
    supported_cpu_architectures: Device.supportedCpuArchitectures,
    total_memory_mb:
      Device.totalMemory == null
        ? null
        : Math.round(Device.totalMemory / (1024 * 1024)),
    is_physical_device: Device.isDevice,
  };
}

export function isGalaxyA25(device: DeviceInfo): boolean {
  const vendor = [device.brand, device.manufacturer].filter(Boolean).join(' ');
  const modelId = device.model_id ?? '';
  const modelName = device.model_name ?? '';

  return (
    /samsung/i.test(vendor) &&
    (/^sm-a256[a-z0-9-]*$/i.test(modelId) || /(^|\s)galaxy\s+a25(?:\s|$)/i.test(modelName))
  );
}
