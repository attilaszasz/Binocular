import '@testing-library/jest-dom/vitest';

// jsdom polyfill for Radix primitives (Switch, Tooltip use ResizeObserver)
globalThis.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};

// jsdom polyfill for pointer events (Radix Select uses hasPointerCapture)
if (!Element.prototype.hasPointerCapture) {
  Element.prototype.hasPointerCapture = () => false;
}

// jsdom polyfill for scrollTo / scrollIntoView (Radix Select uses them)
if (!Element.prototype.scrollTo) {
  Element.prototype.scrollTo = () => {};
}
if (!Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = () => {};
}

const storage = new Map<string, string>();

Object.defineProperty(window, 'localStorage', {
	value: {
		clear: () => storage.clear(),
		getItem: (key: string) => storage.get(key) ?? null,
		removeItem: (key: string) => storage.delete(key),
		setItem: (key: string, value: string) => storage.set(key, value),
	},
	configurable: true,
});
