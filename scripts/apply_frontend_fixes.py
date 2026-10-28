"""Apply frontend fixes for Google Auth, AssessmentRunner, WeakTopics, and AssessmentResult."""
import os

base_dir = "C:/Users/abish/.gemini/antigravity/scratch/personalized-learning-dashboard"

# 1. Update frontend/src/api/client.js
client_path = os.path.join(base_dir, "frontend", "src", "api", "client.js")
with open(client_path, "r", encoding="utf-8") as f:
    client_text = f.read().replace("\r\n", "\n")

old_api_req = '''export async function apiRequest(endpoint, options = {}) {
  const token = getAuthToken();
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (response.status === 204) {
    return null;
  }

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    if (response.status === 401) {
      setAuthToken(null);
      localStorage.removeItem("palp_refresh_token");
      if (
        typeof window !== "undefined" &&
        !window.location.pathname.startsWith("/login") &&
        !endpoint.startsWith("/auth")
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
}'''

new_api_req = '''export async function apiRequest(endpoint, options = {}) {
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
}'''

if old_api_req in client_text:
    client_text = client_text.replace(old_api_req, new_api_req)
    with open(client_path, "w", encoding="utf-8") as f:
        f.write(client_text)
    print("[OK] frontend/src/api/client.js updated with timeout & error handling")
else:
    print("client.js already updated or pattern mismatch")


# 2. Update frontend/src/context/AuthContext.jsx
auth_ctx_path = os.path.join(base_dir, "frontend", "src", "context", "AuthContext.jsx")
with open(auth_ctx_path, "r", encoding="utf-8") as f:
    auth_ctx_text = f.read().replace("\r\n", "\n")

old_login_google = '''  const loginWithGoogle = async (idToken) => {
    setLoading(true);
    try {
      const data = await authApi.loginWithGoogle(idToken);
      setAuthToken(data.access_token);
      localStorage.setItem("palp_refresh_token", data.refresh_token);
      const userProfile = await fetchProfile();
      return { success: true, profile: userProfile };
    } catch (err) {
      return { success: false, error: err.message };
    } finally {
      setLoading(false);
    }
  };'''

new_login_google = '''  const loginWithGoogle = async (idToken) => {
    setLoading(true);
    try {
      const data = await authApi.loginWithGoogle(idToken);
      if (!data?.access_token) {
        throw new Error("No access token received from authentication server.");
      }
      setAuthToken(data.access_token);
      if (data.refresh_token) {
        localStorage.setItem("palp_refresh_token", data.refresh_token);
      }

      // If user object returned by backend, populate session immediately
      if (data.user) {
        setUser({
          id: data.user.id,
          email: data.user.email,
          name: data.user.name,
          target_id: data.user.target_id,
          role: data.user.role,
        });
        setProfile(data.user);
        return { success: true, profile: data.user, user: data.user };
      }

      // Fallback: fetch profile from /me
      const userProfile = await fetchProfile();
      return { success: true, profile: userProfile };
    } catch (err) {
      setAuthToken(null);
      localStorage.removeItem("palp_refresh_token");
      setUser(null);
      setProfile(null);
      return { success: false, error: err.message };
    } finally {
      setLoading(false);
    }
  };'''

if old_login_google in auth_ctx_text:
    auth_ctx_text = auth_ctx_text.replace(old_login_google, new_login_google)
    with open(auth_ctx_path, "w", encoding="utf-8") as f:
        f.write(auth_ctx_text)
    print("[OK] frontend/src/context/AuthContext.jsx updated with immediate session hydration")
else:
    print("AuthContext.jsx already updated or pattern mismatch")


# 3. Update frontend/src/pages/Login.jsx
login_path = os.path.join(base_dir, "frontend", "src", "pages", "Login.jsx")
with open(login_path, "r", encoding="utf-8") as f:
    login_text = f.read().replace("\r\n", "\n")

old_login_state = '''  const [error, setError] = useState(null);
  const [inProgress, setInProgress] = useState(false);
  const navigate = useNavigate();

  const handleGoogleCredential = async (idToken) => {
    setError(null);
    setInProgress(true);
    try {
      const result = await loginWithGoogle(idToken);

      if (result.success) {
        // If user already completed onboarding and has chosen a target, route to Dashboard, else Onboarding
        const hasTarget = Boolean(
          result.profile?.target_id ||
          (result.user && result.user.target_id)
        );
        if (hasTarget) {
          navigate("/dashboard");
        } else {
          navigate("/onboarding");
        }
      } else {
        setError(result.error || "Google authentication failed. Please retry.");
      }
    } catch (err) {
      setError(err.message || "An unexpected error occurred during Google Sign-in");
    } finally {
      setInProgress(false);
    }
  };'''

new_login_state = '''  const [error, setError] = useState(null);
  const [inProgress, setInProgress] = useState(false);
  const [statusMessage, setStatusMessage] = useState("");
  const navigate = useNavigate();

  const handleGoogleCredential = async (idToken) => {
    if (inProgress) return;
    setError(null);
    setInProgress(true);
    setStatusMessage("Verifying your Google credentials…");

    // After 4 seconds, inform user about Render cold start
    const coldStartTimer = setTimeout(() => {
      setStatusMessage("Connecting to server… (Render free tier may take up to 45s to wake up)");
    }, 4000);

    try {
      const result = await loginWithGoogle(idToken);
      clearTimeout(coldStartTimer);

      if (result.success) {
        const hasTarget = Boolean(
          result.profile?.target_id ||
          (result.user && result.user.target_id)
        );
        if (hasTarget) {
          navigate("/dashboard");
        } else {
          navigate("/onboarding");
        }
      } else {
        setError(result.error || "Google authentication failed. Please retry.");
      }
    } catch (err) {
      clearTimeout(coldStartTimer);
      setError(err.message || "An unexpected error occurred during Google Sign-in");
    } finally {
      clearTimeout(coldStartTimer);
      setInProgress(false);
      setStatusMessage("");
    }
  };'''

if old_login_state in login_text:
    login_text = login_text.replace(old_login_state, new_login_state)

old_login_spinner = '''              {(inProgress || loading) && (
                <div className="flex items-center justify-center space-x-2 text-xs text-purple-600 dark:text-purple-400 font-medium pt-1">
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                  </svg>
                  <span>Signing in with Google…</span>
                </div>
              )}'''

new_login_spinner = '''              {(inProgress || loading) && (
                <div className="flex flex-col items-center justify-center space-y-1 text-xs text-purple-600 dark:text-purple-400 font-medium pt-2">
                  <div className="flex items-center space-x-2">
                    <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                    </svg>
                    <span>{statusMessage || "Signing in with Google…"}</span>
                  </div>
                </div>
              )}'''

if old_login_spinner in login_text:
    login_text = login_text.replace(old_login_spinner, new_login_spinner)

with open(login_path, "w", encoding="utf-8") as f:
    f.write(login_text)
print("[OK] frontend/src/pages/Login.jsx updated with dynamic cold-start feedback")


# 4. Update frontend/src/components/AssessmentRunner.jsx
runner_path = os.path.join(base_dir, "frontend", "src", "components", "AssessmentRunner.jsx")
with open(runner_path, "r", encoding="utf-8") as f:
    runner_text = f.read().replace("\r\n", "\n")

old_runner_done = '  const done = index >= items.length;'
new_runner_done = '''  const totalItems = items && Array.isArray(items) ? items.length : 0;
  const done = totalItems > 0 && index >= totalItems;'''
if old_runner_done in runner_text:
    runner_text = runner_text.replace(old_runner_done, new_runner_done)

old_runner_effect = '    if (!done || responses.length !== items.length || submitting) return;'
new_runner_effect = '    if (!done || totalItems === 0 || responses.length !== totalItems || submitting) return;'
if old_runner_effect in runner_text:
    runner_text = runner_text.replace(old_runner_effect, new_runner_effect)

old_empty_guard = '''  const [showSkipConfirm, setShowSkipConfirm] = useState(false);'''
new_empty_guard = '''  const [showSkipConfirm, setShowSkipConfirm] = useState(false);

  if (!items || !Array.isArray(items) || items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-12 text-center bg-white dark:bg-gray-900 rounded-3xl border border-gray-100 dark:border-gray-800 shadow-sm space-y-3">
        <div className="text-3xl">⚠️</div>
        <h3 className="text-base font-bold text-gray-900 dark:text-white">No Questions Available</h3>
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 max-w-sm">
          No questions were found for this assessment session. Please retry or contact administrator.
        </p>
      </div>
    );
  }'''
if old_empty_guard in runner_text and "No Questions Available" not in runner_text:
    runner_text = runner_text.replace(old_empty_guard, new_empty_guard)

with open(runner_path, "w", encoding="utf-8") as f:
    f.write(runner_text)
print("[OK] frontend/src/components/AssessmentRunner.jsx updated with empty items auto-submit guard")


# 5. Update frontend/src/pages/AssessmentInstructions.jsx
instr_path = os.path.join(base_dir, "frontend", "src", "pages", "AssessmentInstructions.jsx")
with open(instr_path, "r", encoding="utf-8") as f:
    instr_text = f.read().replace("\r\n", "\n")

old_instr_check = '''  const handleStartDiagnostic = async () => {
    if (existingStatus?.is_completed) {
      navigate(`/result/${existingStatus.assessment_id}`);
      return;
    }'''

new_instr_check = '''  const handleStartDiagnostic = async () => {
    if (existingStatus?.is_completed && existingStatus?.has_valid_responses) {
      navigate(`/result/${existingStatus.assessment_id}`);
      return;
    }'''

if old_instr_check in instr_text:
    instr_text = instr_text.replace(old_instr_check, new_instr_check)
    with open(instr_path, "w", encoding="utf-8") as f:
        f.write(instr_text)
    print("[OK] frontend/src/pages/AssessmentInstructions.jsx updated to allow starting if no valid responses")


# 6. Update frontend/src/pages/WeakTopics.jsx
weak_path = os.path.join(base_dir, "frontend", "src", "pages", "WeakTopics.jsx")
with open(weak_path, "r", encoding="utf-8") as f:
    weak_text = f.read().replace("\r\n", "\n")

old_weak_has_diag = 'const hasDiagnosticData = Boolean(data?.diagnostic_completed || (data?.total_attempts && data.total_attempts > 0));'
new_weak_has_diag = '''const hasDiagnosticData = Boolean(
    data?.diagnostic_completed &&
    diagPerf &&
    diagPerf.total_questions > 0
  );'''

if old_weak_has_diag in weak_text:
    weak_text = weak_text.replace(old_weak_has_diag, new_weak_has_diag)

old_diag_perf_render = '{diagPerf && ('
new_diag_perf_render = '{hasDiagnosticData && diagPerf && ('
if old_diag_perf_render in weak_text:
    weak_text = weak_text.replace(old_diag_perf_render, new_diag_perf_render)

with open(weak_path, "w", encoding="utf-8") as f:
    f.write(weak_text)
print("[OK] frontend/src/pages/WeakTopics.jsx updated to hide false 0% card when unassessed")


# 7. Update frontend/src/pages/AssessmentResult.jsx
result_path = os.path.join(base_dir, "frontend", "src", "pages", "AssessmentResult.jsx")
with open(result_path, "r", encoding="utf-8") as f:
    result_text = f.read().replace("\r\n", "\n")

# Check if result has items/questions
old_error_state = '''        {error && (
          <div className="p-6 bg-rose-50 dark:bg-rose-950/40 rounded-2xl border border-rose-200 dark:border-rose-900 text-xs text-rose-700 dark:text-rose-300">
            {error}
          </div>
        )}'''

new_error_state = '''        {error && (
          <div className="p-6 bg-rose-50 dark:bg-rose-950/40 rounded-2xl border border-rose-200 dark:border-rose-900 text-xs text-rose-700 dark:text-rose-300">
            {error}
          </div>
        )}

        {/* Empty stub fallback banner */}
        {!loading && !error && (!result || ((!result.items || result.items.length === 0) && (!result.question_results || result.question_results.length === 0))) && (
          <div className="p-8 text-center bg-white dark:bg-gray-900 rounded-3xl border border-dashed border-gray-300 dark:border-gray-800 space-y-4">
            <div className="text-3xl">📝</div>
            <h3 className="text-base font-bold text-gray-900 dark:text-white">Diagnostic Not Yet Evaluated</h3>
            <p className="text-xs text-gray-500 dark:text-gray-400 max-w-md mx-auto">
              No questions or responses were recorded for this diagnostic session. Complete the 10-question diagnostic to establish your personalized baseline.
            </p>
            <Link
              to="/diagnostic/instructions"
              className="inline-block px-5 py-2.5 bg-purple-600 hover:bg-purple-700 text-white font-bold text-xs rounded-xl shadow-md shadow-purple-500/20 transition-all"
            >
              Start Initial Diagnostic →
            </Link>
          </div>
        )}'''

if old_error_state in result_text and "Empty stub fallback banner" not in result_text:
    result_text = result_text.replace(old_error_state, new_error_state)
    with open(result_path, "w", encoding="utf-8") as f:
        f.write(result_text)
    print("[OK] frontend/src/pages/AssessmentResult.jsx updated with empty stub fallback")
