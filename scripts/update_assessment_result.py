"""Update AssessmentResult.jsx with empty stub check."""
import os

base_dir = "C:/Users/abish/.gemini/antigravity/scratch/personalized-learning-dashboard"
result_path = os.path.join(base_dir, "frontend", "src", "pages", "AssessmentResult.jsx")

with open(result_path, "r", encoding="utf-8") as f:
    text = f.read().replace("\r\n", "\n")

target = '''  if (!result) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-gray-950 flex flex-col items-center justify-center p-8 text-center">
        <h3 className="font-bold text-gray-900 dark:text-white">No Assessment Found</h3>
        <p className="text-xs text-gray-500 mt-2 mb-4">No record found for assessment session #{id}.</p>
        <Link to="/dashboard" className="px-4 py-2 bg-purple-600 text-white rounded-xl text-xs font-semibold">
          Go to Dashboard →
        </Link>
      </div>
    );
  }'''

replacement = '''  if (!result) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-gray-950 flex flex-col items-center justify-center p-8 text-center">
        <h3 className="font-bold text-gray-900 dark:text-white">No Assessment Found</h3>
        <p className="text-xs text-gray-500 mt-2 mb-4">No record found for assessment session #{id}.</p>
        <Link to="/dashboard" className="px-4 py-2 bg-purple-600 text-white rounded-xl text-xs font-semibold">
          Go to Dashboard →
        </Link>
      </div>
    );
  }

  const hasContent = Boolean(
    (result.items && result.items.length > 0) ||
    (result.question_results && result.question_results.length > 0) ||
    (result.correct_count != null && result.correct_count > 0)
  );

  if (!hasContent) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-gray-950 flex flex-col items-center justify-center p-8 text-center">
        <div className="p-8 max-w-md bg-white dark:bg-gray-900 rounded-3xl shadow-xl border border-gray-100 dark:border-gray-800 space-y-4">
          <div className="text-4xl">📝</div>
          <h3 className="text-lg font-black text-gray-900 dark:text-white">Diagnostic Not Yet Evaluated</h3>
          <p className="text-xs text-gray-500 dark:text-gray-400 leading-relaxed">
            No questions or responses were recorded for this assessment session. Complete the 10-question initial diagnostic to calibrate your personalized learning baseline.
          </p>
          <div className="pt-2 flex flex-col sm:flex-row gap-3 justify-center">
            <Link
              to="/diagnostic/instructions"
              className="px-5 py-2.5 bg-purple-600 hover:bg-purple-700 text-white font-bold text-xs rounded-xl shadow-md shadow-purple-500/20 transition-all text-center"
            >
              Start Initial Diagnostic →
            </Link>
            <Link
              to="/dashboard"
              className="px-4 py-2.5 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 font-semibold text-xs rounded-xl transition-all text-center"
            >
              Dashboard
            </Link>
          </div>
        </div>
      </div>
    );
  }'''

assert target in text, "Target not found in AssessmentResult.jsx"
text = text.replace(target, replacement)

with open(result_path, "w", encoding="utf-8") as f:
    f.write(text)

print("[OK] AssessmentResult.jsx updated with empty stub guard!")
