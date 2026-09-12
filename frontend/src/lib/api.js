const API_BASE = import.meta.env.VITE_API_BASE || '';

export async function api(endpoint, options = {}) {
  const url = endpoint.startsWith('http') ? endpoint : `${API_BASE}${endpoint}`;
  const defaultHeaders = {
    'Content-Type': 'application/json',
  };
  const config = {
    ...options,
    headers: {
      ...defaultHeaders,
      ...options.headers,
    },
  };
  // Avoid JSON content-type header for FormData
  if (options.body instanceof FormData) {
    delete config.headers['Content-Type'];
  }
  return fetch(url, config);
}
