import { Loader2 } from 'lucide-react';
import { useScanStore } from '../../store/scanStore';

interface TopBarProps {
  title: string;
  rightContent?: React.ReactNode;
}

export function TopBar({ title, rightContent }: TopBarProps) {
  const scanStatus = useScanStore((s) => s.status);
  const isScanning = scanStatus?.status === 'running';

  return (
    <header className="h-14 bg-mangarr-card border-b border-mangarr-border flex items-center px-6 gap-4 shrink-0">
      <h1 className="text-mangarr-text font-semibold text-lg flex-1">{title}</h1>

      <div className="flex items-center gap-4">
        {isScanning && (
          <div className="flex items-center gap-2 text-mangarr-warning text-sm">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span>Scanning...</span>
            {scanStatus.total_files > 0 && (
              <span className="text-mangarr-muted text-xs">
                ({scanStatus.processed_files}/{scanStatus.total_files})
              </span>
            )}
          </div>
        )}
        {rightContent}
      </div>
    </header>
  );
}
