import { auth } from '@/utils/firebase'

const CONFIGURED_API_URL =
  import.meta.env.VITE_API_URL ||
  import.meta.env.VITE_BACKEND_URL ||
  "";

// Prefer same-origin by default:
// - Dev: Vite proxy forwards /api -> backend (no browser CORS)
// - Prod: reverse proxy/nginx forwards /api
const API_BASE_URL =
  CONFIGURED_API_URL ||
  "";

/**
 * Get a fresh Firebase ID token from the current user.
 * Falls back to localStorage for non-Firebase flows.
 * Firebase automatically refreshes expired tokens (1h lifetime).
 */
async function getAuthToken() {
  if (auth.currentUser) {
    try {
      // getIdToken(true) forces refresh if expired; false uses cached if valid
      return await auth.currentUser.getIdToken(false);
    } catch (e) {
      console.warn("Firebase getIdToken failed, falling back to localStorage:", e);
    }
  }
  // Fallback: try localStorage (set at login time)
  const directToken = localStorage.getItem("accessToken");
  if (directToken) return directToken;

  const session = localStorage.getItem("userSession");
  if (session) {
    try {
      return JSON.parse(session).token;
    } catch (_) {}
  }
  return null;
}

/**
 * Get the user session from localStorage (optional UI cache)
 */
export function getUserSession() {
  const session = localStorage.getItem("userSession");
  return session ? JSON.parse(session) : null;
}

/**
 * Check session status from backend (Bearer token)
 */
export async function fetchSessionStatus() {
  const token = await getAuthToken();
  if (!token) return null;

  const res = await fetch(`${API_BASE_URL}/api/auth/session-status`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!res.ok) return null;

  const data = await res.json();
  localStorage.setItem("userSession", JSON.stringify(data));
  localStorage.setItem("sessionSavedAt", new Date().toISOString());
  return data;
}

/**
 * Make an authenticated API request
 *
 * @param {string} endpoint - API endpoint (e.g., '/api/weather/forecast')
 * @param {Object} options - Fetch options (method, body, etc.)
 * @returns {Promise<any>} - Response data
 */
export async function apiRequest(endpoint, options = {}) {
  const url = endpoint.startsWith("http")
    ? endpoint
    : `${API_BASE_URL}${endpoint}`;

  const isFormData =
    typeof FormData !== "undefined" && options.body instanceof FormData;

  const headers = { ...(options.headers || {}) };

  if (!isFormData && !headers["Content-Type"] && !headers["content-type"]) {
    headers["Content-Type"] = "application/json";
  }
  if (isFormData) {
    delete headers["Content-Type"];
    delete headers["content-type"];
  }

  // Always fetch a fresh token — Firebase caches it internally if still valid
  const token = await getAuthToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const config = { ...options, headers };

  if (options.body && !isFormData && typeof options.body === "object") {
    config.body = JSON.stringify(options.body);
  }

  try {
    const response = await fetch(url, config);

    if (response.status === 401) {
      console.error("Authentication failed - session expired or invalid");
      localStorage.removeItem("accessToken");
      localStorage.removeItem("userSession");
      localStorage.removeItem("sessionSavedAt");
      window.location.href = import.meta.env.BASE_URL || '/';
      throw new Error("Session expired. Please login again.");
    }

    if (response.status === 403) {
      throw new Error("Admin access required");
    }

    if (!response.ok) {
      const error = await response
        .json()
        .catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || `API Error: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error("API Request failed:", error);
    throw error;
  }
}

/**
 * Convenience methods for common HTTP methods
 */
export const api = {
  get: (endpoint, options = {}) =>
    apiRequest(endpoint, { ...options, method: "GET" }),

  post: (endpoint, body, options = {}) =>
    apiRequest(endpoint, { ...options, method: "POST", body }),

  put: (endpoint, body, options = {}) =>
    apiRequest(endpoint, { ...options, method: "PUT", body }),

  delete: (endpoint, options = {}) =>
    apiRequest(endpoint, { ...options, method: "DELETE" }),
};

export default api;
