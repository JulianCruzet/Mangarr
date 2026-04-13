import clsx from 'clsx';

interface PageContainerProps {
  children: React.ReactNode;
  className?: string;
}

export function PageContainer({ children, className }: PageContainerProps) {
  return (
    <main className={clsx('flex-1 overflow-y-auto p-6', className)}>
      {children}
    </main>
  );
}
