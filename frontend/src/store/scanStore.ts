import { create } from 'zustand';
import type { ScanStatus } from '../types';

interface ScanStore {
  status: ScanStatus | null;
  setStatus: (s: ScanStatus | null) => void;
}

export const useScanStore = create<ScanStore>((set) => ({
  status: null,
  setStatus: (s) => set({ status: s }),
}));
