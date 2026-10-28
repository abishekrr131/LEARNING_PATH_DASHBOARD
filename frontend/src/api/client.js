/**
 * HTTP Client and API functions for Personalized Learning Path Dashboard (RCT-GAT).
 */

const API_BASE =
  `${import.meta.env.VITE_API_BASE_URL || ""}/api`;

export function getAuthToken() {
  return localStorage.getItem("palp_access_token");
}

export function setAuthToken(token) {
  if (token) {
    localStorage.setItem("palp_access_token", token);
  } else {
    localStorage.removeItem("palp_access_token");
  }
}

export async function apiRequest(endpoint, options = {}) {
  const token = getAuthToken();
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  // Set timeout with AbortController
  // Auth and Diagnostic endpoints can take longer on Render free-tier cold starts (up to 45s)
  const timeoutMs = options.timeoutMs || (endpoint.startsWith("/auth") || endpoint.startsWith("/diagnostic/start") ? 45000 : 25000);
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  let response;
  try {
    response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers,
      signal: controller.signal,
    });
  } catch (fetchErr) {
    clearTimeout(timeoutId);
    if (fetchErr.name === "AbortError") {
      throw new Error(
        "Request timed out. The server may be waking up from sleep (Render free tier). Please retry."
      );
    }
    throw new Error(fetchErr.message || "Network connection failed. Please check your internet connection.");
  }
  clearTimeout(timeoutId);

  if (response.status === 204) {
    return null;
  }

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    if (response.status === 401 && !endpoint.startsWith("/auth")) {
      setAuthToken(null);
      localStorage.removeItem("palp_refresh_token");
      if (
        typeof window !== "undefined" &&
        !window.location.pathname.startsWith("/login")
      ) {
        window.location.href = "/login?reason=session_expired";
      }
    }
    const errorMsg = data.detail || response.statusText || "Request failed";
    const err = new Error(errorMsg);
    err.status = response.status;
    err.data = data;
    throw err;
  }

  return data;
}

// --- Auth Endpoints ---
export const authApi = {
  loginWithGoogle: (idToken) =>
    apiRequest("/auth/google", {
      method: "POST",
      body: JSON.stringify({ id_token: idToken }),
    }),
  refreshToken: (refreshToken) =>
    apiRequest("/auth/refresh", {
      method: "POST",
      body: JSON.stringify({ refresh_token: refreshToken }),
    }),
};

// --- Target & Curriculum Endpoints ---
export const targetApi = {
  list: () => apiRequest("/targets"),
  getDetail: (id) => apiRequest(`/targets/${id}`),
  getGraph: (id) => apiRequest(`/targets/${id}/graph`),
};

// --- Profile & Compliance Endpoints ---
export const profileApi = {
  get: () => apiRequest("/me"),
  update: (data) =>
    apiRequest("/me/profile", {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  export: () => apiRequest("/me/export"),
  delete: () => apiRequest("/me", { method: "DELETE" }),
};

// --- Assessment & Special Test Endpoints ---
export const assessmentApi = {
  getActive: () => apiRequest("/assessments/active"),
  start: (data) =>
    apiRequest("/assessments/start", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  get: (id) => apiRequest(`/assessments/${id}`),
  submit: (id, responses) =>
    apiRequest(`/assessments/${id}/submit`, {
      method: "POST",
      body: JSON.stringify({ responses }),
    }),
  nextSpecialBlock: (id, data) =>
    apiRequest(`/assessments/${id}/next-block`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  blockEndSpecial: (id, data) =>
    apiRequest(`/assessments/${id}/block-end`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  getSubQuestions: (questionId, payload = {}) =>
    apiRequest("/assessments/root-cause/sub-questions", {
      method: "POST",
      body: JSON.stringify({ question_id: questionId, ...payload }),
    }),
  evaluateRootCause: (data) =>
    apiRequest("/assessments/root-cause/evaluate", {
      method: "POST",
      body: JSON.stringify(data),
    }),
};

// --- Dedicated Initial Diagnostic Endpoints ---
export const diagnosticApi = {
  getStatus: () => apiRequest("/diagnostic/status"),
  start: (targetId, retake = false) =>
    apiRequest("/diagnostic/start", {
      method: "POST",
      body: JSON.stringify({ target_id: targetId, retake }),
    }),
  submit: (assessmentId, responses) =>
    apiRequest("/diagnostic/submit", {
      method: "POST",
      body: JSON.stringify({ assessment_id: assessmentId, responses }),
    }),
};

// --- Weekly Progress Test Endpoints ---
export const weeklyTestApi = {
  getStatus: () => apiRequest("/weekly-test/status"),
  start: (targetId, forceUnlock = false) =>
    apiRequest("/weekly-test/start", {
      method: "POST",
      body: JSON.stringify({ target_id: targetId, force_unlock: forceUnlock }),
    }),
  submit: (assessmentId, responses) =>
    apiRequest("/weekly-test/submit", {
      method: "POST",
      body: JSON.stringify({ assessment_id: assessmentId, responses }),
    }),
};

// --- Analytics Endpoints ---
export const analyticsApi = {
  getMastery: () => apiRequest("/analytics/mastery"),
  getGaps: () => apiRequest("/analytics/gaps"),
  getRootCauses: (conceptId) => {
    const query = conceptId ? `?concept_id=${conceptId}` : "";
    return apiRequest(`/analytics/root-causes${query}`);
  },
  getWeeklySnapshots: () => apiRequest("/analytics/weekly-snapshots"),
  refreshWeekly: () =>
    apiRequest("/analytics/refresh-weekly", {
      method: "POST",
    }),
  getReadiness: () => apiRequest("/analytics/readiness"),
  getCareerMap: (targetId) => {
    const query = targetId ? `?target_id=${targetId}` : "";
    return apiRequest(`/analytics/career-map${query}`);
  },
  getMistakeHistory: () => apiRequest("/analytics/mistake-history"),
};

// --- Learning Path & Resources Endpoints ---
export const learningApi = {
  getPath: () => apiRequest("/learning/path"),
  getResources: (conceptId) => {
    const query = conceptId ? `?concept_id=${conceptId}` : "";
    return apiRequest(`/learning/resources${query}`);
  },
  getCareerMap: (targetId) => {
    const query = targetId ? `?target_id=${targetId}` : "";
    return apiRequest(`/learning/career-map${query}`);
  },
  getResourceDetail: (id) => apiRequest(`/learning/resources/${id}`),
};

// --- Study Schedule Endpoints ---
export const scheduleApi = {
  get: () => apiRequest("/schedule"),
  update: (id, data) =>
    apiRequest(`/schedule/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
};

// --- Gemini AI Endpoints (Strictly disabled during scored tests) ---
export const aiApi = {
  ask: (message, conceptId, pageContext) =>
    apiRequest("/ai/ask", {
      method: "POST",
      body: JSON.stringify({
        message,
        concept_id: conceptId,
        page_context: pageContext,
      }),
    }),
  explain: (conceptId) =>
    apiRequest("/ai/explain", {
      method: "POST",
      body: JSON.stringify({ concept_id: conceptId }),
    }),
  feedback: (assessmentId) =>
    apiRequest("/ai/feedback", {
      method: "POST",
      body: JSON.stringify({ assessment_id: assessmentId }),
    }),
  practice: (conceptId) =>
    apiRequest("/ai/practice", {
      method: "POST",
      body: JSON.stringify({ concept_id: conceptId }),
    }),
};
