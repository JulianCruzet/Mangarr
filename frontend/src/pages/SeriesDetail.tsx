import { useMemo, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ArrowLeft,
  RefreshCw,
  FolderSync,
  Download,
  FileX,
  CheckCircle,
} from 'lucide-react';
import { seriesApi } from '../api/series';
import { TopBar } from '../components/layout/TopBar';
import { PageContainer } from '../components/layout/PageContainer';
import { Button } from '../components/ui/Button';
import { StatusBadge, ContentRatingBadge, Badge } from '../components/ui/Badge';
import { Spinner } from '../components/ui/Spinner';
import { useNotificationStore } from '../store/notificationStore';
import type { Chapter } from '../types';

function CoverImage({
  mangadexId,
  coverFilename,
  title,
}: {
  mangadexId: string;
  coverFilename: string | null;
  title: string;
}) {
  const hue = title.split('').reduce((acc, c) => acc + c.charCodeAt(0), 0) % 360;
  const initials = title
    .split(' ')
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase() ?? '')
    .join('');

  const remoteUrl = useMemo(() => {
    if (!coverFilename) return null;
    return `https://uploads.mangadex.org/covers/${mangadexId}/${coverFilename}.512.jpg`;
  }, [mangadexId, coverFilename]);

  const localUrl = coverFilename
    ? `${window.location.origin}/covers/${coverFilename}`
    : null;

  const [src, setSrc] = useState<string | null>(() => localUrl ?? remoteUrl);
  const [failed, setFailed] = useState(false);

  if (!src || failed) {
    return (
      <div
        className="w-full h-full rounded-xl flex items-center justify-center"
        style={{
          background: `linear-gradient(135deg, hsl(${hue},45%,20%) 0%, hsl(${(hue + 40) % 360},40%,14%) 100%)`,
        }}
      >
        <span className="text-5xl font-bold text-white/30 select-none">{initials}</span>
      </div>
    );
  }

  return (
    <img
      src={src}
      alt={title}
      className="w-full h-full object-cover rounded-xl"
      onError={() => {
        if (localUrl && remoteUrl && src === localUrl) {
          setSrc(remoteUrl);
          return;
        }
        setFailed(true);
      }}
    />
  );
}

function parseFloat2(val: string | null): number {
  if (!val) return 0;
  return parseFloat(val) || 0;
}

function sortChapters(chapters: Chapter[]): Chapter[] {
  return [...chapters].sort((a, b) => parseFloat2(a.chapter_number) - parseFloat2(b.chapter_number));
}

interface ChapterRowProps {
  chapter: Chapter;
  index: number;
}

function ChapterRow({ chapter }: ChapterRowProps) {
  const isDownloaded = chapter.is_downloaded;

  return (
    <tr
      className={`border-b border-mangarr-border transition-colors hover:bg-mangarr-input/50 ${
        !isDownloaded ? 'opacity-50' : ''
      }`}
    >
      <td className="py-2.5 px-4 text-mangarr-muted text-sm font-mono w-20">
        {chapter.chapter_number ?? '—'}
      </td>
      <td className="py-2.5 px-4 text-sm">
        <span className={isDownloaded ? 'text-mangarr-text' : 'text-mangarr-muted'}>
          {chapter.title || (chapter.chapter_number ? `Chapter ${chapter.chapter_number}` : 'Unknown')}
        </span>
      </td>
      <td className="py-2.5 px-4 text-mangarr-muted text-sm w-24 hidden md:table-cell">
        {chapter.volume_number ? `Vol. ${chapter.volume_number}` : '—'}
      </td>
      <td className="py-2.5 px-4 text-mangarr-muted text-xs w-32 hidden lg:table-cell">
        {chapter.publish_at
          ? new Date(chapter.publish_at).toLocaleDateString()
          : '—'}
      </td>
      <td className="py-2.5 px-4 w-16 text-right">
        {isDownloaded ? (
          <CheckCircle className="w-4 h-4 text-mangarr-success inline-block" />
        ) : (
          <FileX className="w-4 h-4 text-mangarr-muted inline-block" />
        )}
      </td>
    </tr>
  );
}

export function SeriesDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const addToast = useNotificationStore((s) => s.addToast);
  const [monitorEdit, setMonitorEdit] = useState(false);
  const [monitorVal, setMonitorVal] = useState<'all' | 'future' | 'none'>('all');

  const seriesId = Number(id);

  const { data: series, isLoading, error } = useQuery({
    queryKey: ['series', seriesId],
    queryFn: () => seriesApi.get(seriesId),
    enabled: !isNaN(seriesId),
  });

  const { mutate: refreshMeta, isPending: isRefreshing } = useMutation({
    mutationFn: () => seriesApi.refreshMetadata(seriesId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['series', seriesId] });
      addToast('Metadata refreshed', 'success');
    },
    onError: (err) => addToast(`Refresh failed: ${(err as Error).message}`, 'error'),
  });

  const { mutate: organize, isPending: isOrganizing } = useMutation({
    mutationFn: () => seriesApi.organizeFiles(seriesId),
    onSuccess: (res) => addToast(res.message || 'Files organized', 'success'),
    onError: (err) => addToast(`Organize failed: ${(err as Error).message}`, 'error'),
  });

  const { mutate: updateMonitor, isPending: isUpdatingMonitor } = useMutation({
    mutationFn: (val: 'all' | 'future' | 'none') =>
      seriesApi.update(seriesId, { monitor_status: val }),
    onSuccess: (updated) => {
      queryClient.setQueryData(['series', seriesId], (old: typeof series) =>
        old ? { ...old, monitor_status: updated.monitor_status } : old,
      );
      queryClient.invalidateQueries({ queryKey: ['series'] });
      setMonitorEdit(false);
      addToast('Monitor status updated', 'success');
    },
    onError: (err) => addToast(`Update failed: ${(err as Error).message}`, 'error'),
  });

  if (isLoading) {
    return (
      <div className="flex flex-col h-full">
        <TopBar title="Series" />
        <div className="flex items-center justify-center flex-1">
          <Spinner size="lg" />
        </div>
      </div>
    );
  }

  if (error || !series) {
    return (
      <div className="flex flex-col h-full">
        <TopBar title="Series" />
        <PageContainer>
          <div className="bg-mangarr-danger/10 border border-mangarr-danger/30 rounded-lg p-4">
            <p className="text-mangarr-danger text-sm">
              {error ? `Error: ${(error as Error).message}` : 'Series not found.'}
            </p>
          </div>
        </PageContainer>
      </div>
    );
  }

  const chapters = series.chapters ?? series.volumes?.flatMap((v) => v.chapters) ?? [];
  const sortedChapters = sortChapters(chapters);
  const downloadedCount = chapters.filter((c) => c.is_downloaded).length;
  const totalCount = chapters.length;

  let tags: string[] = [];
  try {
    tags = series.tags_json ? JSON.parse(series.tags_json) : [];
  } catch {
    tags = [];
  }

  const progressPct = totalCount > 0 ? Math.round((downloadedCount / totalCount) * 100) : 0;

  return (
    <div className="flex flex-col h-full">
      <TopBar
        title={series.title}
        rightContent={
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate(-1)}
            leftIcon={<ArrowLeft className="w-4 h-4" />}
          >
            Back
          </Button>
        }
      />
      <PageContainer>
        {/* Hero section */}
        <div className="flex flex-col md:flex-row gap-6 mb-8">
          {/* Cover */}
          <div
            className="w-full md:w-44 shrink-0 rounded-xl overflow-hidden border border-mangarr-border shadow-lg"
            style={{ aspectRatio: '2/3' }}
          >
            <CoverImage
              mangadexId={series.mangadex_id}
              coverFilename={series.cover_filename}
              title={series.title}
            />
          </div>

          {/* Info */}
          <div className="flex-1 min-w-0">
            <h1 className="text-2xl font-bold text-mangarr-text mb-1">{series.title}</h1>
            {series.year && (
              <p className="text-mangarr-muted text-sm mb-3">{series.year}</p>
            )}

            {/* Badges */}
            <div className="flex flex-wrap gap-2 mb-4">
              <StatusBadge status={series.status} />
              {series.content_rating && (
                <ContentRatingBadge rating={series.content_rating} />
              )}
              {series.original_language && (
                <Badge variant="muted">{series.original_language.toUpperCase()}</Badge>
              )}
            </div>

            {/* Description */}
            {series.description && (
              <p className="text-mangarr-muted text-sm leading-relaxed mb-4 line-clamp-4 max-w-2xl">
                {series.description}
              </p>
            )}

            {/* Tags */}
            {tags.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mb-4">
                {tags.map((tag) => (
                  <span
                    key={tag}
                    className="text-xs text-mangarr-muted bg-mangarr-input border border-mangarr-border px-2 py-0.5 rounded"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            )}

            {/* Progress */}
            {totalCount > 0 && (
              <div className="mb-4 max-w-xs">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-mangarr-muted text-xs">
                    {downloadedCount} of {totalCount} chapters downloaded
                  </span>
                  <span className="text-mangarr-muted text-xs">{progressPct}%</span>
                </div>
                <div className="h-1.5 bg-mangarr-border rounded-full overflow-hidden">
                  <div
                    className="h-full bg-mangarr-accent rounded-full transition-all duration-500"
                    style={{ width: `${progressPct}%` }}
                  />
                </div>
              </div>
            )}

            {/* Monitor status */}
            <div className="flex items-center gap-2 mb-5">
              <span className="text-mangarr-muted text-sm">Monitor:</span>
              {monitorEdit ? (
                <div className="flex items-center gap-2">
                  <select
                    defaultValue={series.monitor_status}
                    onChange={(e) => setMonitorVal(e.target.value as typeof monitorVal)}
                    className="select-base text-xs py-1"
                  >
                    <option value="all">All Chapters</option>
                    <option value="future">Future Only</option>
                    <option value="none">None</option>
                  </select>
                  <Button
                    size="sm"
                    loading={isUpdatingMonitor}
                    onClick={() => updateMonitor(monitorVal)}
                  >
                    Save
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => setMonitorEdit(false)}
                  >
                    Cancel
                  </Button>
                </div>
              ) : (
                <button
                  onClick={() => {
                    setMonitorVal(series.monitor_status);
                    setMonitorEdit(true);
                  }}
                  className="text-mangarr-accent text-sm hover:underline capitalize"
                >
                  {series.monitor_status === 'all'
                    ? 'All Chapters'
                    : series.monitor_status === 'future'
                    ? 'Future Only'
                    : 'None'}
                </button>
              )}
            </div>

            {/* Action buttons */}
            <div className="flex flex-wrap gap-2">
              <Button
                variant="secondary"
                size="sm"
                loading={isRefreshing}
                onClick={() => refreshMeta()}
                leftIcon={<RefreshCw className="w-4 h-4" />}
              >
                Refresh Metadata
              </Button>
              <Button
                variant="secondary"
                size="sm"
                loading={isOrganizing}
                onClick={() => organize()}
                leftIcon={<FolderSync className="w-4 h-4" />}
              >
                Organize Files
              </Button>
            </div>
          </div>
        </div>

        {/* Chapters table */}
        <div className="bg-mangarr-card border border-mangarr-border rounded-xl overflow-hidden">
          <div className="flex items-center justify-between px-5 py-3 border-b border-mangarr-border">
            <h2 className="text-mangarr-text font-semibold text-sm">
              Chapters
            </h2>
            <div className="flex items-center gap-3">
              <span className="text-mangarr-muted text-xs">
                {downloadedCount}/{totalCount} downloaded
              </span>
              <Badge variant={downloadedCount === totalCount && totalCount > 0 ? 'success' : 'muted'}>
                <Download className="w-3 h-3 mr-1" />
                {progressPct}%
              </Badge>
            </div>
          </div>

          {sortedChapters.length === 0 ? (
            <div className="py-12 text-center text-mangarr-muted">
              <p className="text-sm">No chapters found.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left">
                <thead>
                  <tr className="border-b border-mangarr-border bg-mangarr-input/30">
                    <th className="py-2 px-4 text-mangarr-muted text-xs font-medium uppercase tracking-wider">
                      #
                    </th>
                    <th className="py-2 px-4 text-mangarr-muted text-xs font-medium uppercase tracking-wider">
                      Title
                    </th>
                    <th className="py-2 px-4 text-mangarr-muted text-xs font-medium uppercase tracking-wider hidden md:table-cell">
                      Volume
                    </th>
                    <th className="py-2 px-4 text-mangarr-muted text-xs font-medium uppercase tracking-wider hidden lg:table-cell">
                      Published
                    </th>
                    <th className="py-2 px-4 text-mangarr-muted text-xs font-medium uppercase tracking-wider text-right">
                      Status
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {sortedChapters.map((chapter, i) => (
                    <ChapterRow key={chapter.id} chapter={chapter} index={i} />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </PageContainer>
    </div>
  );
}
