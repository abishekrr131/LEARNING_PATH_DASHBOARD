"""Update App.jsx and Resources.jsx for Study Material detail routing and smart navigation."""
import os

app_path = "C:/Users/abish/.gemini/antigravity/scratch/personalized-learning-dashboard/frontend/src/App.jsx"
resources_path = "C:/Users/abish/.gemini/antigravity/scratch/personalized-learning-dashboard/frontend/src/pages/Resources.jsx"

# 1. Update App.jsx
with open(app_path, "r", encoding="utf-8") as f:
    app_text = f.read().replace("\r\n", "\n")

if "StudyMaterialDetail" not in app_text:
    # Add import
    import_target = 'import Resources from "./pages/Resources";'
    import_replacement = 'import Resources from "./pages/Resources";\nimport StudyMaterialDetail from "./pages/StudyMaterialDetail";'
    assert import_target in app_text, "Cannot find Resources import in App.jsx"
    app_text = app_text.replace(import_target, import_replacement)

    # Add route
    route_target = """            <Route
              path="/resources"
              element={
                <ProtectedRoute>
                  <Resources />
                </ProtectedRoute>
              }
            />"""
    route_replacement = """            <Route
              path="/resources"
              element={
                <ProtectedRoute>
                  <Resources />
                </ProtectedRoute>
              }
            />
            <Route
              path="/resources/:id"
              element={
                <ProtectedRoute>
                  <StudyMaterialDetail />
                </ProtectedRoute>
              }
            />"""
    assert route_target in app_text, "Cannot find /resources route in App.jsx"
    app_text = app_text.replace(route_target, route_replacement)

    with open(app_path, "w", encoding="utf-8") as f:
        f.write(app_text)
    print("[OK] App.jsx updated with StudyMaterialDetail route")
else:
    print("App.jsx already has StudyMaterialDetail")


# 2. Update Resources.jsx
with open(resources_path, "r", encoding="utf-8") as f:
    res_text = f.read().replace("\r\n", "\n")

# Update imports to include Link
import_old = 'import { useSearchParams } from "react-router-dom";'
import_new = 'import { useSearchParams, Link } from "react-router-dom";'
if import_old in res_text:
    res_text = res_text.replace(import_old, import_new)

# Update card title to be clickable Link when internal
old_title_snippet = """                    <h3 className="font-bold text-gray-900 dark:text-white text-base line-clamp-2 leading-snug">
                      {res.title}
                    </h3>"""

new_title_snippet = """                    {(() => {
                      const url = res.url || "";
                      const isInternal =
                        res.is_internal ||
                        !url ||
                        url.includes("learn.internal") ||
                        url.startsWith("/") ||
                        url.startsWith("internal:");

                      if (isInternal && (res.id || res.concept_id)) {
                        return (
                          <Link
                            to={`/resources/${res.id || res.concept_id}`}
                            className="font-bold text-gray-900 dark:text-white text-base line-clamp-2 leading-snug hover:text-purple-600 dark:hover:text-purple-400 transition-colors"
                          >
                            {res.title}
                          </Link>
                        );
                      }

                      return (
                        <h3 className="font-bold text-gray-900 dark:text-white text-base line-clamp-2 leading-snug">
                          {res.title}
                        </h3>
                      );
                    })()}"""

if old_title_snippet in res_text:
    res_text = res_text.replace(old_title_snippet, new_title_snippet)

# Update Study Now button snippet
old_btn_snippet = """                    <a
                      href={res.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center space-x-1 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-xl text-xs font-semibold shadow-sm transition-colors"
                    >
                      <span>Study Now</span>
                      <span>↗</span>
                    </a>"""

new_btn_snippet = """                    {(() => {
                      const url = res.url || "";
                      const isInternal =
                        res.is_internal ||
                        !url ||
                        url.includes("learn.internal") ||
                        url.startsWith("/") ||
                        url.startsWith("internal:");
                      const hasExternalUrl =
                        !isInternal && /^https?:\\/\\//i.test(url);

                      if (hasExternalUrl) {
                        return (
                          <a
                            href={url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center space-x-1 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-xl text-xs font-semibold shadow-sm transition-colors"
                          >
                            <span>Study Online</span>
                            <span>↗</span>
                          </a>
                        );
                      }

                      if (res.id || res.concept_id) {
                        return (
                          <Link
                            to={`/resources/${res.id || res.concept_id}`}
                            className="inline-flex items-center space-x-1 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-xl text-xs font-semibold shadow-sm transition-colors"
                          >
                            <span>Study Notes</span>
                            <span>→</span>
                          </Link>
                        );
                      }

                      return (
                        <button
                          disabled
                          className="inline-flex items-center space-x-1 px-4 py-2 bg-gray-100 dark:bg-gray-800 text-gray-400 dark:text-gray-500 rounded-xl text-xs font-semibold cursor-not-allowed border border-gray-200 dark:border-gray-700"
                        >
                          <span>Material Pending</span>
                        </button>
                      );
                    })()}"""

if old_btn_snippet in res_text:
    res_text = res_text.replace(old_btn_snippet, new_btn_snippet)

with open(resources_path, "w", encoding="utf-8") as f:
    f.write(res_text)

print("[OK] Resources.jsx updated with smart study navigation")
