import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  FolderOpen,
  Trash2,
  CheckCircle,
  XCircle,
  HardDrive,
  Plus,
  AlertCircle,
} from 'lucide-react';
import { libraryApi } from '../api/library';
import { TopBar } from '../components/layout/TopBar';
import { PageContainer } from '../components/layout/PageContainer';
import { Button } from '../components/ui/Button';
import { Modal } from '../components/ui/Modal';
import { Spinner } from '../components/ui/Spinner';
import { useNotificationStore } from '../store/notificationStore';
import type { RootFolder } from '../types';

function formatBytes(bytes: number | null): string {
  if (bytes === null || bytes === undefined) return '—';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let val = bytes;
  let i = 0;
  while (val >= 1024 && i < units.length - 1) {
    val /= 1024;
    i++;
  }
  return `${val.toFixed(1)} ${units[i]}`;
}

interface DeleteConfirmModalProps {
  folder: RootFolder;
  onConfirm: () => void;
  onClose: () => void;
  isDeleting: boolean;
}

function DeleteConfirmModal({ folder, onConfirm, onClose, isDeleting }: DeleteConfirmModalProps) {
  return (
    <Modal
      isOpen
      onClose={onClose}
      title="Remove Root Folder"
      size="sm"
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button variant="danger" loading={isDeleting} onClick={onConfirm}>
            Remove
          </Button>
        </>
      }
    >
      <div className="flex items-start gap-3">
        <AlertCircle className="w-5 h-5 text-mangarr-warning shrink-0 mt-0.5" />
        <div>
          <p className="text-mangarr-text text-sm mb-1">
            Are you sure you want to remove this root folder?
          </p>
          <p className="text-mangarr-muted text-xs font-mono bg-mangarr-input border border-mangarr-border rounded px-2 py-1 inline-block">
            {folder.path}
          </p>
          <p className="text-mangarr-muted text-xs mt-2">
            This will not delete any files from disk, only remove the folder from Mangarr.
          </p>
        </div>
      </div>
    </Modal>
  );
}

interface AddFolderFormProps {
  onSuccess: () => void;
}

function AddFolderForm({ onSuccess }: AddFolderFormProps) {
  const [path, setPath] = useState('');
  const [label, setLabel] = useState('');
  const [validating, setValidating] = useState(false);
  const [validationResult, setValidationResult] = useState<{
    valid: boolean;
    message: string;
    freeSpace: number | null;
  } | null>(null);

  const addToast = useNotificationStore((s) => s.addToast);
  const queryClient = useQueryClient();

  const { mutate: addFolder, isPending: isAdding } = useMutation({
    mutationFn: () => libraryApi.addFolder({ path, label }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['folders'] });
      addToast('Root folder added', 'success');
      setPath('');
      setLabel('');
      setValidationResult(null);
      onSuccess();
    },
    onError: (err) => addToast(`Failed to add folder: ${(err as Error).message}`, 'error'),
  });

  const handleValidate = async () => {
    if (!path.trim()) return;
    setValidating(true);
    setValidationResult(null);
    try {
      const result = await libraryApi.validatePath(path);
      if (result.valid) {
        setValidationResult({
          valid: true,
          message: 'Path is valid and accessible.',
          freeSpace: result.free_space,
        });
      } else {
        setValidationResult({
          valid: false,
          message: result.error ?? 'Path is not accessible.',
          freeSpace: null,
        });
      }
    } catch (err) {
      setValidationResult({
        valid: false,
        message: (err as Error).message,
        freeSpace: null,
      });
    } finally {
      setValidating(false);
    }
  };

  return (
    <div className="bg-mangarr-card border border-mangarr-border rounded-xl p-5">
      <h3 className="text-mangarr-text font-semibold text-sm mb-4 flex items-center gap-2">
        <Plus className="w-4 h-4" />
        Add Root Folder
      </h3>
      <div className="space-y-4">
        <div className="space-y-1.5">
          <label className="text-mangarr-text text-sm font-medium block">Path</label>
          <div className="flex gap-2">
            <input
              type="text"
              value={path}
              onChange={(e) => {
                setPath(e.target.value);
                setValidationResult(null);
              }}
              placeholder="/mnt/media/manga"
              className="input-base flex-1 text-sm font-mono"
            />
            <Button
              variant="secondary"
              size="sm"
              loading={validating}
              onClick={handleValidate}
              disabled={!path.trim()}
            >
              Validate
            </Button>
          </div>
          {validationResult && (
            <div
              className={`flex items-center gap-2 text-xs p-2 rounded-md border ${
                validationResult.valid
                  ? 'text-mangarr-success bg-mangarr-success/10 border-mangarr-success/30'
                  : 'text-mangarr-danger bg-mangarr-danger/10 border-mangarr-danger/30'
              }`}
            >
              {validationResult.valid ? (
                <CheckCircle className="w-3.5 h-3.5 shrink-0" />
              ) : (
                <XCircle className="w-3.5 h-3.5 shrink-0" />
              )}
              <span>{validationResult.message}</span>
              {validationResult.freeSpace !== null && (
                <span className="ml-auto text-mangarr-muted">
                  {formatBytes(validationResult.freeSpace)} free
                </span>
              )}
            </div>
          )}
        </div>

        <div className="space-y-1.5">
          <label className="text-mangarr-text text-sm font-medium block">
            Label{' '}
            <span className="text-mangarr-muted font-normal">(optional)</span>
          </label>
          <input
            type="text"
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            placeholder="e.g. External Drive"
            className="input-base w-full text-sm"
          />
        </div>

        <Button
          onClick={() => addFolder()}
          loading={isAdding}
          disabled={!path.trim()}
          leftIcon={<Plus className="w-4 h-4" />}
        >
          Add Folder
        </Button>
      </div>
    </div>
  );
}

export function RootFolders() {
  const [deletingFolder, setDeletingFolder] = useState<RootFolder | null>(null);
  const addToast = useNotificationStore((s) => s.addToast);
  const queryClient = useQueryClient();

  const { data: folders = [], isLoading, error } = useQuery({
    queryKey: ['folders'],
    queryFn: () => libraryApi.getFolders(),
  });

  const { mutate: deleteFolder, isPending: isDeleting } = useMutation({
    mutationFn: (id: number) => libraryApi.deleteFolder(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['folders'] });
      addToast('Root folder removed', 'success');
      setDeletingFolder(null);
    },
    onError: (err) => addToast(`Failed to remove folder: ${(err as Error).message}`, 'error'),
  });

  return (
    <div className="flex flex-col h-full">
      <TopBar title="Root Folders" />
      <PageContainer className="max-w-3xl mx-auto w-full">
        {/* Folders table */}
        <div className="bg-mangarr-card border border-mangarr-border rounded-xl overflow-hidden mb-6">
          <div className="px-5 py-3 border-b border-mangarr-border">
            <h2 className="text-mangarr-text font-semibold text-sm flex items-center gap-2">
              <FolderOpen className="w-4 h-4" />
              Configured Folders
            </h2>
          </div>

          {isLoading ? (
            <div className="flex items-center justify-center py-10">
              <Spinner />
            </div>
          ) : error ? (
            <div className="p-5">
              <p className="text-mangarr-danger text-sm">
                Failed to load folders: {(error as Error).message}
              </p>
            </div>
          ) : folders.length === 0 ? (
            <div className="py-10 text-center">
              <FolderOpen className="w-10 h-10 mx-auto mb-3 text-mangarr-muted opacity-40" />
              <p className="text-mangarr-muted text-sm">No root folders configured.</p>
              <p className="text-mangarr-disabled text-xs mt-1">
                Add a folder below to get started.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left">
                <thead>
                  <tr className="border-b border-mangarr-border bg-mangarr-input/30">
                    <th className="py-2.5 px-5 text-mangarr-muted text-xs font-medium uppercase tracking-wider">
                      Path
                    </th>
                    <th className="py-2.5 px-4 text-mangarr-muted text-xs font-medium uppercase tracking-wider hidden md:table-cell">
                      Label
                    </th>
                    <th className="py-2.5 px-4 text-mangarr-muted text-xs font-medium uppercase tracking-wider hidden sm:table-cell">
                      Free Space
                    </th>
                    <th className="py-2.5 px-4 text-mangarr-muted text-xs font-medium uppercase tracking-wider">
                      Status
                    </th>
                    <th className="py-2.5 px-4 w-12" />
                  </tr>
                </thead>
                <tbody>
                  {folders.map((folder) => (
                    <tr
                      key={folder.id}
                      className="border-b border-mangarr-border hover:bg-mangarr-input/40 transition-colors"
                    >
                      <td className="py-3 px-5">
                        <div className="flex items-center gap-2">
                          <HardDrive className="w-4 h-4 text-mangarr-muted shrink-0" />
                          <span className="text-mangarr-text text-sm font-mono break-all">
                            {folder.path}
                          </span>
                        </div>
                      </td>
                      <td className="py-3 px-4 text-mangarr-muted text-sm hidden md:table-cell">
                        {folder.label || '—'}
                      </td>
                      <td className="py-3 px-4 text-mangarr-muted text-sm hidden sm:table-cell">
                        {formatBytes(folder.free_space)}
                      </td>
                      <td className="py-3 px-4">
                        {folder.free_space !== null ? (
                          <span className="flex items-center gap-1.5 text-mangarr-success text-xs">
                            <CheckCircle className="w-3.5 h-3.5" />
                            Accessible
                          </span>
                        ) : (
                          <span className="flex items-center gap-1.5 text-mangarr-danger text-xs">
                            <XCircle className="w-3.5 h-3.5" />
                            Unknown
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-4">
                        <button
                          onClick={() => setDeletingFolder(folder)}
                          className="p-1.5 rounded text-mangarr-muted hover:text-mangarr-danger hover:bg-mangarr-danger/10 transition-colors"
                          title="Remove folder"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Add folder form */}
        <AddFolderForm onSuccess={() => {}} />

        {/* Delete confirmation modal */}
        {deletingFolder && (
          <DeleteConfirmModal
            folder={deletingFolder}
            onConfirm={() => deleteFolder(deletingFolder.id)}
            onClose={() => setDeletingFolder(null)}
            isDeleting={isDeleting}
          />
        )}
      </PageContainer>
    </div>
  );
}
