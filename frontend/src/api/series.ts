import { api } from './client';
import type { Series, Volume, Chapter } from '../types';

export interface SeriesListParams {
  status?: string;
  sort?: string;
}

export interface AddSeriesPayload {
  mangadex_id: string;
  root_folder_id: number;
  monitor_status: 'all' | 'future' | 'none';
}

export interface UpdateSeriesPayload {
  monitor_status?: 'all' | 'future' | 'none';
  root_folder_id?: number;
}

export interface SeriesWithVolumes extends Series {
  volumes: Volume[];
  chapters: Chapter[];
}

interface SeriesListResponse {
  items: Series[];
  total: number;
}

export const seriesApi = {
  list: async (params?: SeriesListParams): Promise<Series[]> => {
    const query = new URLSearchParams();
    if (params?.status) query.set('status', params.status);
    if (params?.sort) query.set('sort', params.sort);
    const qs = query.toString();
    const response = await api.get<Series[] | SeriesListResponse>(`/series${qs ? `?${qs}` : ''}`);
    return Array.isArray(response) ? response : response.items;
  },

  get: (id: number): Promise<SeriesWithVolumes> =>
    api.get<SeriesWithVolumes>(`/series/${id}`),

  add: (payload: AddSeriesPayload): Promise<Series> =>
    api.post<Series>('/series', payload),

  update: (id: number, payload: UpdateSeriesPayload): Promise<Series> =>
    api.put<Series>(`/series/${id}`, payload),

  delete: (id: number): Promise<void> =>
    api.delete<void>(`/series/${id}`),

  refreshMetadata: (id: number): Promise<Series> =>
    api.post<Series>(`/series/${id}/refresh`),

  organizeFiles: (id: number): Promise<{ message: string }> =>
    api.post<{ message: string }>(`/series/${id}/organize`),

  getChapters: (id: number): Promise<Chapter[]> =>
    api.get<Chapter[]>(`/series/${id}/chapters`),
};
