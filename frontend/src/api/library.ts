import { api } from './client';
import type { RootFolder, ImportedFile, PathValidationResult } from '../types';

export interface AddFolderPayload {
  path: string;
  label: string;
}

export interface UpdateFolderPayload {
  label?: string;
}

export interface UnmatchedFilesResponse {
  files: ImportedFile[];
  total: number;
}

export interface MatchFilePayload {
  series_id: number;
  chapter_id?: number;
}

export const libraryApi = {
  getFolders: (): Promise<RootFolder[]> =>
    api.get<RootFolder[]>('/library/folders'),

  getFolder: (id: number): Promise<RootFolder> =>
    api.get<RootFolder>(`/library/folders/${id}`),

  addFolder: (payload: AddFolderPayload): Promise<RootFolder> =>
    api.post<RootFolder>('/library/folders', payload),

  updateFolder: (id: number, payload: UpdateFolderPayload): Promise<RootFolder> =>
    api.put<RootFolder>(`/library/folders/${id}`, payload),

  deleteFolder: (id: number): Promise<void> =>
    api.delete<void>(`/library/folders/${id}`),

  validatePath: (path: string): Promise<PathValidationResult> => {
    const query = new URLSearchParams({ path });
    return api.get<PathValidationResult>(`/library/folders/validate-path?${query.toString()}`);
  },

  getUnmatchedFiles: (): Promise<ImportedFile[]> =>
    api.get<ImportedFile[]>('/library/unmatched'),

  matchFile: (fileId: number, payload: MatchFilePayload): Promise<ImportedFile> =>
    api.post<ImportedFile>(`/library/files/${fileId}/match`, payload),

  getImportedFiles: (): Promise<ImportedFile[]> =>
    api.get<ImportedFile[]>('/library/files'),
};
