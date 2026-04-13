import { useEffect, useCallback } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
  Play,
  StopCircle,
  Search,
  CheckCircle2,
  XCircle,
  Clock,
  FileQuestion,
} from 'lucide-react';
import { scannerApi } from '../api/scanner';
import { seriesApi } from '../api/series';
import { TopBar } from '../components/layout/TopBar';
import { PageContainer } from '../components/layout/PageContainer';
import { Button } from '../components/ui/Button';
import { Spinner } from '../components/ui/Spinner';
import { Modal } from '../components/ui/Modal';
import { useScanStore } from '../store/scanStore';
import { useNotificationStore } from '../store/notificationStore';
import { useState } from 'react';
import type { ImportedFile, Series } from '../types';

function formatDate(iso: string | null): string {
  if (!iso) return '—';
  return new Date(iso).toLocaleString();
}

function formatBytes(bytes: number): string {
  const units = ['B', 'KB', 'MB', 'GB'];
  let val = bytes;
  let i = 0;
  while (val >= 1024 && i < units.length - 1) { val /= 1024; i++; }
  return `${val.toFixed(1)} ${units[i]}`;
}

interface MatchModalProps {
  file: ImportedFile;
  series: Series[];
  onMatch: (seriesId: number, chapterId?: number) => void;
  onClose: () => void;
  isMatching: boolean;
}

function MatchModal({ file, series, onMatch, onClose, isMatching }: MatchModalProps) {
  const [selectedSeriesId, setSelectedSeriesId] = useState<number | ''>('');

  return (
    <Modal
      isOpen
      onClose={onClose}
      title="Match File to Series"
      size="md"
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button
            loading={isMatching}
            disabled={selectedSeriesId === ''}
            onClick={() => selectedSeriesId !== '' && onMatch(selectedSeriesId)}
          >
            Match
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <div className="bg-mangarr-input border border-mangarr-border rounded-lg p-3">
          <p className="text-mangarr-muted text-xs mb-1">File</p>
          <p className="text-mangarr-text text-sm font-mono break-all">{file.file_name}</p>
          {file.parsed_series_title && (
            <p className="text-mangarr-muted text-xs mt-1">
              Parsed: <span className="text-mangarr-text">{file.parsed_series_title}</span>
              {file.parsed_chapter_number && (
                <> · Ch. {file.parsed_chapter_number}</>
              )}
            </p>
          )}
        </div>

        <div className="space-y-1.5">
          <label className="text-mangarr-text text-sm font-medium block">Assign to Series</label>
          <select
            value={selectedSeriesId}
            onChange={(e) => setSelectedSeriesId(e.target.value === '' ? '' : Number(e.target.value))}
            className="select-base w-full text-sm"
          >
            <option value="">— Select a series —</option>
            {series.map((s) => (
              <option key={s.id} value={s.id}>
                {s.title}
              </option>
            ))}
          </select>
        </div>
      </div>
    </Modal>
  );
}

export function Scanner() {
  const { status, setStatus } = useScanStore();
  const addToast = useNotificationStore((s) => s.addToast);
  const [matchingFile, setMatchingFile] = useState<ImportedFile | null>(null);
  const [isMatchingPending, setIsMatchingPending] = useState(false);

  // Poll scan status
  const { data: scanStatus, refetch: refetchStatus } = useQuery({
    queryKey: ['scan-status'],
    queryFn: () => scannerApi.getStatus(),
    refetchInterval: status?.status === 'running' ? 2000 : false,
  });

  useEffect(() => {
    if (scanStatus) setStatus(scanStatus);
  }, [scanStatus, setStatus]);

  const { data: unmatchedFiles = [], refetch: refetchUnmatched } = useQuery({
    queryKey: ['unmatched-files'],
    queryFn: () => scannerApi.getUnmatchedFiles(),
  });

  const { data: allSeries = [] } = useQuery({
    queryKey: ['series'],
    queryFn: () => seriesApi.list(),
  });

  const { mutate: startScan, isPending: isStarting } = useMutation({
    mutationFn: () => scannerApi.startScan(),
    onSuccess: (s) => {
      setStatus(s);
      addToast('Scan started', 'info');
      refetchStatus();
    },
    onError: (err) => addToast(`Scan failed to start: ${(err as Error).message}`, 'error'),
  });

  const { mutate: cancelScan, isPending: isCancelling } = useMutation({
    mutationFn: () => scannerApi.cancelScan(),
    onSuccess: () => {
      addToast('Scan cancelled', 'info');
      refetchStatus();
    },
    onError: (err) => addToast(`Cancel failed: ${(err as Error).message}`, 'error'),
  });

  const handleMatch = useCallback(
    async (seriesId: number) => {
      if (!matchingFile) return;
      setIsMatchingPending(true);
      try {
        await scannerApi.matchFile({ imported_file_id: matchingFile.id, series_id: seriesId });
        addToast('File matched successfully', 'success');
        refetchUnmatched();
        setMatchingFile(null);
      } catch (err) {
        addToast(`Match failed: ${(err as Error).message}`, 'error');
      } finally {
        setIsMatchingPending(false);
      }
    },
    [matchingFile, addToast, refetchUnmatched],
  );

  const currentStatus = scanStatus ?? status;
  const isRunning = currentStatus?.status === 'running';
  const progressPct =
    currentStatus && currentStatus.total_files > 0
      ? Math.round((currentStatus.processed_files / currentStatus.total_files) * 100)
      : 0;

  const statusConfig: Record<
    string,
    { icon: React.ReactNode; label: string; color: string }
  > = {
    idle: {
      icon: <Clock className="w-4 h-4" />,
      label: 'Idle',
      color: 'text-mangarr-muted',
    },
    running: {
      icon: <Spinner size="sm" />,
      label: 'Running',
      color: 'text-mangarr-warning',
    },
    completed: {
      icon: <CheckCircle2 className="w-4 h-4" />,
      label: 'Complete',
      color: 'text-mangarr-success',
    },
    cancelled: {
      icon: <StopCircle className="w-4 h-4" />,
      label: 'Cancelled',
      color: 'text-mangarr-muted',
    },
    error: {
      icon: <XCircle className="w-4 h-4" />,
      label: 'Error',
      color: 'text-mangarr-danger',
    },
  };

  const statusInfo = statusConfig[currentStatus?.status ?? 'idle'];

  return (
    <div className="flex flex-col h-full">
      <TopBar title="Scanner" />
      <PageContainer className="max-w-4xl mx-auto w-full space-y-6">
        {/* Scan status card */}
        <div className="bg-mangarr-card border border-mangarr-border rounded-xl p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-mangarr-text font-semibold text-sm flex items-center gap-2">
              <Search className="w-4 h-4" />
              Scan Status
            </h2>
            <div className="flex gap-2">
              {isRunning ? (
                <Button
                  variant="danger"
                  size="sm"
                  loading={isCancelling}
                  onClick={() => cancelScan()}
                  leftIcon={<StopCircle className="w-4 h-4" />}
                >
                  Cancel
                </Button>
              ) : (
                <Button
                  size="sm"
                  loading={isStarting}
                  onClick={() => startScan()}
                  leftIcon={<Play className="w-4 h-4" />}
                >
                  Scan All
                </Button>
              )}
            </div>
          </div>

          {/* Status row */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-4">
            <div className="bg-mangarr-input border border-mangarr-border rounded-lg p-3">
              <p className="text-mangarr-muted text-xs mb-1">Status</p>
              <div className={`flex items-center gap-1.5 text-sm font-medium ${statusInfo.color}`}>
                {statusInfo.icon}
                {statusInfo.label}
              </div>
            </div>
            <div className="bg-mangarr-input border border-mangarr-border rounded-lg p-3">
              <p className="text-mangarr-muted text-xs mb-1">Files Found</p>
              <p className="text-mangarr-text text-sm font-semibold">
                {currentStatus?.total_files ?? 0}
              </p>
            </div>
            <div className="bg-mangarr-input border border-mangarr-border rounded-lg p-3">
              <p className="text-mangarr-muted text-xs mb-1">Matched</p>
              <p className="text-mangarr-success text-sm font-semibold">
                {currentStatus?.matched ?? 0}
              </p>
            </div>
            <div className="bg-mangarr-input border border-mangarr-border rounded-lg p-3">
              <p className="text-mangarr-muted text-xs mb-1">Unmatched</p>
              <p className="text-mangarr-warning text-sm font-semibold">
                {currentStatus?.unmatched ?? 0}
              </p>
            </div>
          </div>

          {/* Progress bar */}
          {isRunning && currentStatus && currentStatus.total_files > 0 && (
            <div className="space-y-1.5">
              <div className="flex justify-between text-xs text-mangarr-muted">
                <span>
                  {currentStatus.processed_files} / {currentStatus.total_files} files processed
                </span>
                <span>{progressPct}%</span>
              </div>
              <div className="h-2 bg-mangarr-border rounded-full overflow-hidden">
                <div
                  className="h-full bg-mangarr-accent rounded-full transition-all duration-300"
                  style={{ width: `${progressPct}%` }}
                />
              </div>
            </div>
          )}

          {/* Started at */}
          {currentStatus?.started_at && (
            <p className="text-mangarr-disabled text-xs mt-3">
              Started: {formatDate(currentStatus.started_at)}
            </p>
          )}

          {/* Error */}
          {currentStatus?.error && (
            <div className="mt-3 bg-mangarr-danger/10 border border-mangarr-danger/30 rounded-lg p-3">
              <p className="text-mangarr-danger text-xs">{currentStatus.error}</p>
            </div>
          )}
        </div>

        {/* Unmatched files */}
        <div className="bg-mangarr-card border border-mangarr-border rounded-xl overflow-hidden">
          <div className="px-5 py-3 border-b border-mangarr-border flex items-center justify-between">
            <h2 className="text-mangarr-text font-semibold text-sm flex items-center gap-2">
              <FileQuestion className="w-4 h-4" />
              Unmatched Files
              {unmatchedFiles.length > 0 && (
                <span className="bg-mangarr-warning/20 text-mangarr-warning text-xs px-1.5 py-0.5 rounded-full border border-mangarr-warning/30">
                  {unmatchedFiles.length}
                </span>
              )}
            </h2>
          </div>

          {unmatchedFiles.length === 0 ? (
            <div className="py-10 text-center">
              <CheckCircle2 className="w-10 h-10 mx-auto mb-3 text-mangarr-success opacity-60" />
              <p className="text-mangarr-muted text-sm">All files are matched.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left">
                <thead>
                  <tr className="border-b border-mangarr-border bg-mangarr-input/30">
                    <th className="py-2.5 px-5 text-mangarr-muted text-xs font-medium uppercase tracking-wider">
                      Filename
                    </th>
                    <th className="py-2.5 px-4 text-mangarr-muted text-xs font-medium uppercase tracking-wider hidden md:table-cell">
                      Parsed Title
                    </th>
                    <th className="py-2.5 px-4 text-mangarr-muted text-xs font-medium uppercase tracking-wider hidden sm:table-cell">
                      Chapter
                    </th>
                    <th className="py-2.5 px-4 text-mangarr-muted text-xs font-medium uppercase tracking-wider hidden lg:table-cell">
                      Size
                    </th>
                    <th className="py-2.5 px-4 w-20 text-right" />
                  </tr>
                </thead>
                <tbody>
                  {unmatchedFiles.map((file) => (
                    <tr
                      key={file.id}
                      className="border-b border-mangarr-border hover:bg-mangarr-input/40 transition-colors"
                    >
                      <td className="py-3 px-5">
                        <p className="text-mangarr-text text-xs font-mono break-all max-w-xs">
                          {file.file_name}
                        </p>
                        <p className="text-mangarr-disabled text-xs mt-0.5 truncate max-w-xs">
                          {file.file_path}
                        </p>
                      </td>
                      <td className="py-3 px-4 text-mangarr-muted text-sm hidden md:table-cell">
                        {file.parsed_series_title ?? <span className="text-mangarr-disabled">—</span>}
                      </td>
                      <td className="py-3 px-4 text-mangarr-muted text-sm hidden sm:table-cell">
                        {file.parsed_chapter_number ?? <span className="text-mangarr-disabled">—</span>}
                      </td>
                      <td className="py-3 px-4 text-mangarr-muted text-xs hidden lg:table-cell">
                        {formatBytes(file.file_size)}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => setMatchingFile(file)}
                        >
                          Match
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {matchingFile && (
          <MatchModal
            file={matchingFile}
            series={allSeries}
            onMatch={handleMatch}
            onClose={() => setMatchingFile(null)}
            isMatching={isMatchingPending}
          />
        )}
      </PageContainer>
    </div>
  );
}
