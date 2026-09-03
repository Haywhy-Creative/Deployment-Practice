import { API_BASE_URL } from './api';

let refreshPromise: Promise<string | null> | null = null;

/**
 * Safely parses JSON response bodies without throwing SyntaxErrors on 204 or empty HTML responses.
 */
export const safeParseJson = async <T = any>(response: Response): Promise<T> => {
  if (response.status === 204) return {} as T;

  const text = await response.text();
  try {
    return text ? JSON.parse(text) : ({} as T);
  } catch {
    throw new Error(`Server returned invalid JSON format (Status ${response.status}).`);
  }
};

/**
 * Deduplicates concurrent refresh requests when multiple endpoints fail simultaneously.
 */
const refreshAccessToken = async (): Promise<string | null> => {
  if (refreshPromise) return refreshPromise;

  refreshPromise = (async () => {
    const refreshToken = localStorage.getItem('refreshToken');
    if (!refreshToken) return null;

    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      if (response.ok) {
        const data = await safeParseJson(response);
        const newAccessToken = data.access_token || data.token;

        if (newAccessToken) {
          localStorage.setItem('accessToken', newAccessToken);
          return newAccessToken;
        }
      }
    } catch (err) {
      console.error('Network error during token refresh:', err);
    }

    // Clear session on failure and redirect
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
    window.location.href = '/login';
    return null;
  })();

  const token = await refreshPromise;
  refreshPromise = null;
  return token;
};

/**
 * Core fetch wrapper with Bearer token injection, auto-refresh on 401, and automatic retries.
 */
export const fetchWithAuth = async (
  url: string,
  options: RequestInit = {}
): Promise<Response> => {
  let accessToken = localStorage.getItem('accessToken');

  const headers = new Headers(options.headers || {});
  if (accessToken && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${accessToken}`);
  }
  
  // Set Content-Type unless payload is FormData
  if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }

  // Initial Request
  let response = await fetch(url, { ...options, headers });

  // Handle Token Expiration (401 Unauthorized)
  if (response.status === 401) {
    const newAccessToken = await refreshAccessToken();

    if (newAccessToken) {
      headers.set('Authorization', `Bearer ${newAccessToken}`);
      response = await fetch(url, { ...options, headers });
    }
  }

  return response;
};

/**
 * Convenient shorthand helper methods for API requests with auto-parsing & error handling.
 */
export const api = {
  get: async <T = any>(endpoint: string): Promise<T> => {
    const response = await fetchWithAuth(`${API_BASE_URL}${endpoint}`, { method: 'GET' });
    const data = await safeParseJson<T>(response);
    if (!response.ok) throw new Error((data as any).message || 'GET request failed');
    return data;
  },

  post: async <T = any>(endpoint: string, body?: any): Promise<T> => {
    const response = await fetchWithAuth(`${API_BASE_URL}${endpoint}`, {
      method: 'POST',
      body: body ? JSON.stringify(body) : undefined,
    });
    const data = await safeParseJson<T>(response);
    if (!response.ok) throw new Error((data as any).message || 'POST request failed');
    return data;
  },
};