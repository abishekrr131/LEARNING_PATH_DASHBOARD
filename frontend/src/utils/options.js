/**
 * Normalizes question options into a uniform array of { key: string, text: string }.
 *
 * Accepts:
 *  - Object: { A: "text", B: "text", ... }
 *  - Array of objects: [{ key: "A", text: "text" }, ...] or [{ key: "A", label: "text" }]
 *  - Array of strings: ["Option 1", "Option 2"] -> assigns keys 'A', 'B', 'C', 'D'...
 *  - JSON string of any of the above
 *  - Null / undefined / empty -> returns []
 */
export function toOptionList(rawOptions) {
  if (!rawOptions) {
    return [];
  }

  let options = rawOptions;

  // Handle JSON string input
  if (typeof options === "string") {
    try {
      options = JSON.parse(options);
    } catch {
      return [];
    }
  }

  // Handle Array format
  if (Array.isArray(options)) {
    return options.map((item, idx) => {
      const fallbackKey = String.fromCharCode(65 + idx); // 'A', 'B', 'C', ...

      if (item && typeof item === "object") {
        const key = item.key !== undefined ? String(item.key) : fallbackKey;
        const text =
          item.text !== undefined
            ? String(item.text)
            : item.label !== undefined
            ? String(item.label)
            : item.value !== undefined
            ? String(item.value)
            : String(item);
        return { key, text };
      }

      return {
        key: fallbackKey,
        text: String(item ?? ""),
      };
    });
  }

  // Handle Object format { A: "...", B: "..." }
  if (typeof options === "object") {
    return Object.entries(options).map(([key, text]) => ({
      key: String(key),
      text: typeof text === "object" && text !== null ? text.text || text.label || JSON.stringify(text) : String(text ?? ""),
    }));
  }

  return [];
}
