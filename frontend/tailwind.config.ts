import type { Config } from 'tailwindcss';

export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        surface: 'rgb(var(--color-surface) / <alpha-value>)',
        'surface-hover': 'rgb(var(--color-surface-hover) / <alpha-value>)',
        panel: 'rgb(var(--color-panel) / <alpha-value>)',
        'panel-hover': 'rgb(var(--color-panel-hover) / <alpha-value>)',
        ink: 'rgb(var(--color-ink) / <alpha-value>)',
        'ink-hover': 'rgb(var(--color-ink-hover) / <alpha-value>)',
        'ink-disabled': 'rgb(var(--color-ink-disabled) / <alpha-value>)',
        muted: 'rgb(var(--color-muted) / <alpha-value>)',
        'muted-hover': 'rgb(var(--color-muted-hover) / <alpha-value>)',
        accent: 'rgb(var(--color-accent) / <alpha-value>)',
        'accent-hover': 'rgb(var(--color-accent-hover) / <alpha-value>)',
        'accent-focus': 'rgb(var(--color-accent-focus) / <alpha-value>)',
        'accent-disabled': 'rgb(var(--color-accent-disabled) / <alpha-value>)',
        'accent-active': 'rgb(var(--color-accent-active) / <alpha-value>)',
        error: 'rgb(var(--color-error) / <alpha-value>)',
        'error-bg': 'rgb(var(--color-error-bg) / <alpha-value>)',
        'error-border': 'rgb(var(--color-error-border) / <alpha-value>)',
        success: 'rgb(var(--color-success) / <alpha-value>)',
        'success-bg': 'rgb(var(--color-success-bg) / <alpha-value>)',
        'success-border': 'rgb(var(--color-success-border) / <alpha-value>)',
        warning: 'rgb(var(--color-warning) / <alpha-value>)',
        'warning-bg': 'rgb(var(--color-warning-bg) / <alpha-value>)',
        'warning-border': 'rgb(var(--color-warning-border) / <alpha-value>)',
        'gradient-edge': 'rgb(var(--color-gradient-edge) / <alpha-value>)',
      },
      fontFamily: {
        sans: ['Nunito Sans', 'ui-sans-serif', 'system-ui'],
        mono: ['JetBrains Mono', 'ui-monospace', 'SFMono-Regular'],
      },
      boxShadow: {
        quiet: '0 18px 50px rgb(15 23 42 / 0.12)',
      },
    },
  },
  plugins: [],
} satisfies Config;
