import "@testing-library/jest-dom/vitest";

// jsdom doesn't implement matchMedia — needed by ThemeContext (and anything
// that renders it, e.g. AppShell) whenever a test doesn't stub it itself.
if (typeof window !== "undefined" && !window.matchMedia) {
  window.matchMedia = (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  });
}
