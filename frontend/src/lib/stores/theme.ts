import { writable } from 'svelte/store';
import { browser } from '$app/environment';

type Theme = 'light' | 'dark';

const STORAGE_KEY = 'paqs-theme';

const theme = writable<Theme>('light');

if (browser) {
  const applyTheme = (value: Theme) => {
    document.documentElement.dataset.theme = value;
    document.body.classList.toggle('theme-dark', value === 'dark');
  };

  const stored = localStorage.getItem(STORAGE_KEY);
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)');
  const initial: Theme = stored === 'dark' || stored === 'light'
    ? stored
    : prefersDark.matches
      ? 'dark'
      : 'light';

  applyTheme(initial);
  theme.set(initial);

  prefersDark.addEventListener('change', (event) => {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved !== 'dark' && saved !== 'light') {
      const nextTheme: Theme = event.matches ? 'dark' : 'light';
      applyTheme(nextTheme);
      theme.set(nextTheme);
    }
  });

  theme.subscribe((value) => {
    applyTheme(value);
    localStorage.setItem(STORAGE_KEY, value);
  });
}

export const themeStore = theme;
export const toggleTheme = () => {
  theme.update((value) => (value === 'dark' ? 'light' : 'dark'));
};
