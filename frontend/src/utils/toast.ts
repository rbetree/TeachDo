export type ToastType = 'success' | 'error' | 'info';

const dispatch = (type: ToastType, message: string) => {
  if (typeof window === 'undefined') return;
  window.dispatchEvent(new CustomEvent('toast', { detail: { type, message } }));
};

export const toast = {
  success: (message: string) => dispatch('success', message),
  error: (message: string) => dispatch('error', message),
  info: (message: string) => dispatch('info', message),
};
