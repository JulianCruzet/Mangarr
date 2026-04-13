import { useEffect } from 'react';
import { createPortal } from 'react-dom';
import { X, CheckCircle, AlertCircle, Info } from 'lucide-react';
import clsx from 'clsx';
import { useNotificationStore, type Toast as ToastItem } from '../../store/notificationStore';

const TOAST_DURATION = 4000;

const typeConfig: Record<
  ToastItem['type'],
  { icon: React.ReactNode; classes: string }
> = {
  success: {
    icon: <CheckCircle className="w-5 h-5 text-mangarr-success shrink-0" />,
    classes: 'border-mangarr-success/30 bg-mangarr-success/10',
  },
  error: {
    icon: <AlertCircle className="w-5 h-5 text-mangarr-danger shrink-0" />,
    classes: 'border-mangarr-danger/30 bg-mangarr-danger/10',
  },
  info: {
    icon: <Info className="w-5 h-5 text-mangarr-accent shrink-0" />,
    classes: 'border-mangarr-accent/30 bg-mangarr-accent/10',
  },
};

function ToastItem({ toast }: { toast: ToastItem }) {
  const removeToast = useNotificationStore((s) => s.removeToast);
  const config = typeConfig[toast.type];

  useEffect(() => {
    const timer = setTimeout(() => removeToast(toast.id), TOAST_DURATION);
    return () => clearTimeout(timer);
  }, [toast.id, removeToast]);

  return (
    <div
      className={clsx(
        'flex items-start gap-3 px-4 py-3 rounded-lg border',
        'bg-mangarr-card shadow-xl min-w-[280px] max-w-[420px]',
        'animate-slide-up',
        config.classes,
      )}
      role="alert"
    >
      {config.icon}
      <p className="flex-1 text-sm text-mangarr-text leading-snug">{toast.message}</p>
      <button
        onClick={() => removeToast(toast.id)}
        className="shrink-0 p-0.5 text-mangarr-muted hover:text-mangarr-text transition-colors"
        aria-label="Dismiss notification"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  );
}

export function ToastContainer() {
  const toasts = useNotificationStore((s) => s.toasts);

  if (toasts.length === 0) return null;

  return createPortal(
    <div
      className="fixed bottom-4 right-4 z-[100] flex flex-col gap-2 items-end"
      aria-live="polite"
      aria-label="Notifications"
    >
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} />
      ))}
    </div>,
    document.body,
  );
}
