import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { StatusBadge, Badge } from '../ui/Badge';
import type { Series } from '../../types';

interface SeriesCardProps {
  series: Series;
}

function CoverPlaceholder({ title }: { title: string }) {
  const initials = title
    .split(' ')
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase() ?? '')
    .join('');

  // Deterministic gradient based on title
  const hue = title.split('').reduce((acc, c) => acc + c.charCodeAt(0), 0) % 360;

  return (
    <div
      className="w-full h-full flex items-center justify-center"
      style={{
        background: `linear-gradient(135deg, hsl(${hue}, 45%, 18%) 0%, hsl(${(hue + 40) % 360}, 40%, 12%) 100%)`,
      }}
    >
      <span className="text-3xl font-bold text-white/50 select-none">{initials}</span>
    </div>
  );
}

export function SeriesCard({ series }: SeriesCardProps) {
  const navigate = useNavigate();
  const remoteUrl = useMemo(() => {
    if (!series.cover_filename) return null;
    return `https://uploads.mangadex.org/covers/${series.mangadex_id}/${series.cover_filename}.512.jpg`;
  }, [series.mangadex_id, series.cover_filename]);

  const localUrl = series.cover_filename
    ? `${window.location.origin}/covers/${series.cover_filename}`
    : null;

  const [src, setSrc] = useState<string | null>(() => localUrl ?? remoteUrl);
  const [imgFailed, setImgFailed] = useState(false);

  const downloaded = series.downloaded_count ?? 0;
  const total = series.chapter_count ?? 0;
  const progressPct = total > 0 ? Math.round((downloaded / total) * 100) : 0;

  return (
    <div
      onClick={() => navigate(`/series/${series.id}`)}
      className="group relative bg-mangarr-card border border-mangarr-border rounded-lg overflow-hidden cursor-pointer
                 transition-all duration-200 hover:scale-[1.03] hover:border-mangarr-accent/50
                 hover:shadow-[0_0_20px_rgba(92,157,255,0.15)]"
    >
      {/* Cover image (2:3 aspect ratio) */}
      <div className="relative w-full" style={{ paddingBottom: '150%' }}>
        <div className="absolute inset-0 bg-mangarr-input">
          {src && !imgFailed ? (
            <img
              src={src}
              alt={series.title}
              className="w-full h-full object-cover"
              loading="lazy"
              onError={() => {
                if (localUrl && remoteUrl && src === localUrl) {
                  setSrc(remoteUrl);
                  return;
                }
                setImgFailed(true);
              }}
            />
          ) : (
            <CoverPlaceholder title={series.title} />
          )}
        </div>

        {/* Gradient overlay at bottom */}
        <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent" />

        {/* Status badge and provider badge */}
        <div className="absolute top-2 left-2 right-2 flex items-start justify-between gap-1">
          <div>
            {series.status && (
              <StatusBadge status={series.status} size="sm" />
            )}
          </div>
          <Badge variant="info" size="sm">
            {series.metadata_provider === 'mangadex' ? 'MDex' : series.metadata_provider === 'mangabaka' ? 'Baka' : series.metadata_provider}
          </Badge>
        </div>

        {/* Title + chapter info overlay */}
        <div className="absolute bottom-0 left-0 right-0 p-2.5">
          <p className="text-white text-xs font-semibold leading-tight line-clamp-2 mb-1">
            {series.title}
          </p>
          {total > 0 && (
            <div className="flex items-center gap-1.5">
              <div className="flex-1 h-0.5 bg-white/20 rounded-full overflow-hidden">
                <div
                  className="h-full bg-mangarr-accent rounded-full transition-all duration-300"
                  style={{ width: `${progressPct}%` }}
                />
              </div>
              <span className="text-white/60 text-[10px] shrink-0">
                {downloaded}/{total}
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
