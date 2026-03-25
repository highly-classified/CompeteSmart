/**
 * Optimized fetch wrapper for authenticated requests to the CompeteSmart backend.
 * Handles JWT injection from localStorage and redirects to /auth on 401.
 */
export async function authenticatedFetch(url: string, options: RequestInit = {}) {
  const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
  const backendBase = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

  // Ensure URL is absolute or prefix with backendBase
  const fullUrl = url.startsWith("http") ? url : `${backendBase}${url.startsWith("/") ? "" : "/"}${url}`;

  const headers = {
    ...options.headers,
    "Authorization": token ? `Bearer ${token}` : "",
  } as any;

  try {
    const response = await fetch(fullUrl, { ...options, headers });

    if (response.status === 401) {
      console.warn("Session expired or invalid. Redirecting to login...");
      if (typeof window !== "undefined") {
        localStorage.removeItem("token");
        window.location.href = "/auth";
      }
    }

    return response;
  } catch (error) {
    console.error("API Fetch Error:", error);
    throw error;
  }
}
