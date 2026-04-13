import { api } from './client';
import type { AppSettings } from '../types';

export const settingsApi = {
  get: (): Promise<AppSettings> =>
    api.get<AppSettings>('/settings'),

  update: (payload: Partial<AppSettings>): Promise<AppSettings> =>
    api.put<AppSettings>('/settings', payload),
};
