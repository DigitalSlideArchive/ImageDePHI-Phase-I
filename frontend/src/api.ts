export const api = (url: string, {}) =>
  fetch(import.meta.env.VITE_API_URL + url, {});
