import { StatusBar } from 'expo-status-bar';
import { useState } from 'react';
import {
  ActivityIndicator,
  Pressable,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';

import { MODELS, PHOTOS } from './src/assets';
import { evaluateVerdict, runBenchmark } from './src/benchmark';
import { exportBenchmarkReport } from './src/export';
import type {
  BenchmarkProgress,
  BenchmarkReport,
  ExportState,
} from './src/types';

export default function App() {
  const [report, setReport] = useState<BenchmarkReport | null>(null);
  const [progress, setProgress] = useState<BenchmarkProgress | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [exportState, setExportState] = useState<ExportState>('pending');
  const [error, setError] = useState<string | null>(null);

  const startBenchmark = async () => {
    setError(null);
    setReport(null);
    setExportState('pending');
    setIsRunning(true);

    try {
      const nextReport = await runBenchmark(setProgress);
      setReport(nextReport);
    } catch (cause) {
      setError(toMessage(cause));
    } finally {
      setIsRunning(false);
    }
  };

  const exportJson = async () => {
    if (report == null) {
      return;
    }

    setError(null);
    setExportState('pending');
    setIsExporting(true);

    try {
      await exportBenchmarkReport(report);
      setExportState('passed');
    } catch (cause) {
      setExportState('failed');
      setError(toMessage(cause));
    } finally {
      setIsExporting(false);
    }
  };

  const verdict = report == null ? null : evaluateVerdict(report, exportState);

  return (
    <SafeAreaView style={styles.safeArea}>
      <StatusBar style="dark" />
      <ScrollView contentContainerStyle={styles.container}>
        <Text style={styles.title}>Benchmark de vision bovina</Text>
        <Text style={styles.description}>
          10 fotos locales, 1 calentamiento + 5 inferencias medidas por foto y modelo.
          Requiere un development build; Expo Go no es compatible con LiteRT JSI.
        </Text>

        <Pressable
          accessibilityRole="button"
          disabled={isRunning || isExporting}
          onPress={startBenchmark}
          style={[styles.primaryButton, (isRunning || isExporting) && styles.buttonDisabled]}
        >
          <Text style={styles.primaryButtonText}>
            {isRunning ? 'Corriendo benchmark...' : 'Correr benchmark'}
          </Text>
        </Pressable>

        {progress != null && (
          <View style={styles.progress}>
            {isRunning && <ActivityIndicator color="#123b2b" />}
            <View style={styles.progressText}>
              <Text style={styles.mono}>
                {progress.completed}/{progress.total} tareas
              </Text>
              <Text>
                {progress.phase}
                {progress.photo == null ? '' : `: ${progress.photo}`}
                {progress.model == null ? '' : ` (${progress.model})`}
              </Text>
            </View>
          </View>
        )}

        {error != null && (
          <View style={styles.errorBox}>
            <Text style={styles.errorText}>{error}</Text>
          </View>
        )}

        {report != null && verdict != null && (
          <>
            <View
              style={[
                styles.verdict,
                verdict.status === 'GO' ? styles.goVerdict : styles.noGoVerdict,
              ]}
            >
              <Text style={styles.verdictTitle}>{verdict.status}</Text>
              <Text style={styles.verdictSubtext}>
                Resultado para {report.device.model_name ?? report.device.model_id ?? 'dispositivo desconocido'}
              </Text>
            </View>

            <Section title="Criterios GO / NO-GO">
              {verdict.criteria.map((criterion) => (
                <View key={criterion.name} style={styles.criterion}>
                  <Text style={criterion.passed ? styles.pass : styles.fail}>
                    {criterion.passed ? 'PASS' : 'FAIL'}
                  </Text>
                  <View style={styles.criterionText}>
                    <Text style={styles.rowTitle}>{criterion.name}</Text>
                    <Text style={styles.detail}>{criterion.detail}</Text>
                  </View>
                </View>
              ))}
            </Section>

            <Section title="Resumen de inferencia (solo 5 corridas medidas)">
              <View style={styles.tableHeader}>
                <Text style={[styles.tableCell, styles.mono]}>modelo</Text>
                <Text style={[styles.tableCell, styles.mono]}>n</Text>
                <Text style={[styles.tableCell, styles.mono]}>p50 ms</Text>
                <Text style={[styles.tableCell, styles.mono]}>p95 ms</Text>
              </View>
              {MODELS.map((model) => {
                const stats = report.summary[model.id];
                return (
                  <View key={model.id} style={styles.tableRow}>
                    <Text style={[styles.tableCell, styles.mono]}>{model.label}</Text>
                    <Text style={[styles.tableCell, styles.mono]}>{stats.count}</Text>
                    <Text style={[styles.tableCell, styles.mono]}>{formatMs(stats.p50_ms)}</Text>
                    <Text style={[styles.tableCell, styles.mono]}>{formatMs(stats.p95_ms)}</Text>
                  </View>
                );
              })}
              <Text style={styles.detail}>
                ArUco ID 0: {report.summary.aruco_decoded}/{report.summary.aruco_total}. Backend:{' '}
                {report.aruco_backend.name}.
              </Text>
            </Section>

            <Section title="Segmentacion por foto">
              {report.segmentation.map((measurement) => (
                <View key={`${measurement.foto}-${measurement.modelo}`} style={styles.resultRow}>
                  <Text style={styles.rowTitle}>
                    {photoLabel(measurement.foto)} / {measurement.modelo}
                  </Text>
                  <Text style={styles.detail}>
                    vacas={measurement.cow_dets} | area={measurement.mask_area_px} px original | post=
                    {formatMs(measurement.postprocess_ms)} ms | conf=
                    {measurement.selected_confidence == null
                      ? 'n/a'
                      : measurement.selected_confidence.toFixed(3)}
                  </Text>
                </View>
              ))}
            </Section>

            <Section title="ArUco por foto">
              {report.aruco.map((measurement) => (
                <View key={measurement.foto} style={styles.resultRow}>
                  <Text style={styles.rowTitle}>{photoLabel(measurement.foto)}</Text>
                  <Text style={styles.detail}>
                    {measurement.decoded ? 'ID 0 decodificado' : 'sin ID 0'} | {formatMs(measurement.aruco_ms)}
                    {' ms'} | esquinas {measurement.subpixel_corners ? 'subpixel' : 'pixel'}
                  </Text>
                </View>
              ))}
            </Section>

            <Pressable
              accessibilityRole="button"
              disabled={isRunning || isExporting}
              onPress={exportJson}
              style={[styles.secondaryButton, (isRunning || isExporting) && styles.buttonDisabled]}
            >
              <Text style={styles.secondaryButtonText}>
                {isExporting ? 'Abriendo compartir...' : 'Exportar JSON'}
              </Text>
            </Pressable>
            <Text style={styles.exportHint}>
              Genera y comparte benchmark_results.json con las 120 corridas crudas, ArUco y mascaras.
            </Text>
          </>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>{title}</Text>
      {children}
    </View>
  );
}

function photoLabel(id: string): string {
  return PHOTOS.find((photo) => photo.id === id)?.label ?? id;
}

function formatMs(value: number): string {
  return value.toFixed(1);
}

function toMessage(cause: unknown): string {
  return cause instanceof Error ? cause.message : String(cause);
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: '#f5f6f2',
  },
  container: {
    gap: 14,
    padding: 16,
    paddingBottom: 32,
  },
  title: {
    color: '#123b2b',
    fontSize: 24,
    fontWeight: '700',
  },
  description: {
    color: '#4c544e',
    fontSize: 14,
    lineHeight: 20,
  },
  primaryButton: {
    alignItems: 'center',
    backgroundColor: '#123b2b',
    borderRadius: 6,
    padding: 14,
  },
  primaryButtonText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '700',
  },
  secondaryButton: {
    alignItems: 'center',
    borderColor: '#123b2b',
    borderRadius: 6,
    borderWidth: 1,
    padding: 14,
  },
  secondaryButtonText: {
    color: '#123b2b',
    fontSize: 16,
    fontWeight: '700',
  },
  buttonDisabled: {
    opacity: 0.5,
  },
  progress: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: 10,
  },
  progressText: {
    flex: 1,
    gap: 2,
  },
  mono: {
    fontFamily: 'monospace',
  },
  errorBox: {
    backgroundColor: '#ffe9e7',
    borderColor: '#a92c21',
    borderRadius: 6,
    borderWidth: 1,
    padding: 12,
  },
  errorText: {
    color: '#7b1a12',
  },
  verdict: {
    borderRadius: 6,
    padding: 14,
  },
  goVerdict: {
    backgroundColor: '#dff3e7',
    borderColor: '#177245',
    borderWidth: 1,
  },
  noGoVerdict: {
    backgroundColor: '#ffe9e7',
    borderColor: '#a92c21',
    borderWidth: 1,
  },
  verdictTitle: {
    color: '#1a2520',
    fontSize: 24,
    fontWeight: '800',
  },
  verdictSubtext: {
    color: '#4c544e',
    marginTop: 2,
  },
  section: {
    backgroundColor: '#ffffff',
    borderColor: '#d8ddd6',
    borderRadius: 6,
    borderWidth: 1,
    gap: 8,
    padding: 12,
  },
  sectionTitle: {
    color: '#123b2b',
    fontSize: 16,
    fontWeight: '700',
  },
  criterion: {
    alignItems: 'flex-start',
    flexDirection: 'row',
    gap: 8,
  },
  criterionText: {
    flex: 1,
  },
  pass: {
    color: '#177245',
    fontFamily: 'monospace',
    fontWeight: '700',
  },
  fail: {
    color: '#a92c21',
    fontFamily: 'monospace',
    fontWeight: '700',
  },
  rowTitle: {
    color: '#1a2520',
    fontWeight: '600',
  },
  detail: {
    color: '#4c544e',
    fontSize: 13,
    lineHeight: 18,
  },
  tableHeader: {
    backgroundColor: '#edf0ea',
    flexDirection: 'row',
    paddingVertical: 6,
  },
  tableRow: {
    borderTopColor: '#edf0ea',
    borderTopWidth: 1,
    flexDirection: 'row',
    paddingVertical: 6,
  },
  tableCell: {
    flex: 1,
    fontSize: 12,
    textAlign: 'center',
  },
  resultRow: {
    borderTopColor: '#edf0ea',
    borderTopWidth: 1,
    gap: 2,
    paddingTop: 8,
  },
  exportHint: {
    color: '#4c544e',
    fontSize: 12,
    textAlign: 'center',
  },
});
