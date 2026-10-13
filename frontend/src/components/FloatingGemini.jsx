import React, { useState, useEffect, useRef } from "react";
import { aiApi, assessmentApi } from "../api/client";

/**
 * Floating Gemini AI Assistant Component.
 * Implements Master Prompt Requirement 5 & Spec Section 10:
 * - Floating "✦ Ask Gemini" button on every page after login
 * - Expandable slide-over (max ~920px wide)
 * - Context chip showing current page and concept
 * - Quick action pills
 * - Every reply labelled "[AI-generated]"
 * - STRICT SUPPRESSION: Automatically disables during active scored tests.
 */
export default function FloatingGemini({ currentConceptId = null, currentConceptName = null, pageContext = "Dashboard" }) {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([
    {
      sender: "ai",
      text: "Hello! I am your Gemini pedagogical assistant. I can explain complex syllabus concepts, clarify mistakes, or draft practice reps. What would you like to explore?",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [testSuppressed, setTestSuppressed] = useState(false);
  const [suppressedTestType, setSuppressedTestType] = useState(null);

  const messagesEndRef = useRef(null);

  // Periodically check if learner has an active scored assessment
  useEffect(() => {
    let isMounted = true;
    const checkActiveTest = async () => {
      try {
        const status = await assessmentApi.getActive();
        if (isMounted) {
          setTestSuppressed(status.has_active_test);
          setSuppressedTestType(status.type);
        }
      } catch (err) {
        // Ignore in unauthenticated state
      }
    };

    checkActiveTest();
    const interval = setInterval(checkActiveTest, 4000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  useEffect(() => {
    if (isOpen) {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isOpen]);

  const sendMessage = async (customPrompt = null) => {
    const textToSend = customPrompt || input;
    if (!textToSend.trim() || loading || testSuppressed) return;

    const userMsg = { sender: "user", text: textToSend };
    setMessages((prev) => [...prev, userMsg]);
    if (!customPrompt) setInput("");
    setLoading(true);

    try {
      const res = await aiApi.ask(textToSend, currentConceptId, pageContext);
      setMessages((prev) => [
        ...prev,
        {
          sender: "ai",
          text: res.reply,
          label: res.label || "AI-generated",
        },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          sender: "ai",
          text: err.status === 403
            ? `⚠️ Assistant Blocked: ${err.message}`
            : (err.message && err.message.includes("AI assistant unavailable") ? "AI assistant unavailable, retry" : "AI assistant unavailable, retry"),
          isError: true,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleQuickAction = (actionText) => {
    let prompt = actionText;
    if (actionText === "Explain simply") {
      prompt = currentConceptName
        ? `Explain ${currentConceptName} simply using an intuitive real-world analogy.`
        : "Explain the core prerequisites of this syllabus in simple terms.";
    } else if (actionText === "Why was my answer wrong?") {
      prompt = "Can you diagnose why common misconceptions occur on this topic?";
    } else if (actionText === "What should I study next?") {
      prompt = "Based on my learning path, which foundational prerequisite should I master next?";
    } else if (actionText === "Practice questions") {
      prompt = `Provide a guided practice question testing ${currentConceptName || "key concepts"}.`;
    }
    sendMessage(prompt);
  };

  return (
    <>
      {/* Floating Button */}
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        className="fixed bottom-6 right-6 z-40 flex items-center space-x-2 px-5 py-3.5 rounded-full font-semibold text-sm bg-gradient-to-r from-purple-600 via-indigo-600 to-rose-500 text-white shadow-xl hover:shadow-purple-500/30 hover:scale-105 transition-all focus:outline-none focus:ring-4 focus:ring-purple-300"
      >
        <span className="text-amber-300 text-base">✦</span>
        <span>Ask Gemini</span>
        {testSuppressed && (
          <span className="w-2.5 h-2.5 bg-rose-400 rounded-full animate-ping" title="Disabled during scored test" />
        )}
      </button>

      {/* Slide-over Overlay */}
      {isOpen && (
        <div className="fixed inset-0 z-50 overflow-hidden bg-black/40 backdrop-blur-sm flex justify-end">
          <div className="w-full max-w-3xl bg-white dark:bg-gray-900 h-full shadow-2xl flex flex-col border-l border-purple-100 dark:border-purple-900/40 animate-slide-in">
            {/* Header */}
            <div className="p-5 border-b border-gray-100 dark:border-gray-800 flex items-center justify-between bg-gradient-to-r from-purple-50/50 to-indigo-50/50 dark:from-gray-900 dark:to-purple-950/20">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-600 to-indigo-600 flex items-center justify-center text-white font-bold text-lg shadow-md shadow-purple-500/20">
                  ✦
                </div>
                <div>
                  <h3 className="font-bold text-gray-900 dark:text-white flex items-center space-x-2">
                    <span>Gemini AI Assistant</span>
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-purple-100 dark:bg-purple-900/50 text-purple-700 dark:text-purple-300 font-mono">
                      Flash 2.0
                    </span>
                  </h3>
                  <div className="flex items-center space-x-2 mt-0.5">
                    <span className="text-xs text-gray-400">Context:</span>
                    <span className="text-xs px-2 py-0.5 rounded-md bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-purple-700 dark:text-purple-300 font-medium">
                      {currentConceptName ? `${currentConceptName} (${pageContext})` : pageContext}
                    </span>
                  </div>
                </div>
              </div>

              <button
                type="button"
                onClick={() => setIsOpen(false)}
                className="w-8 h-8 rounded-lg flex items-center justify-center text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
              >
                ✕
              </button>
            </div>

            {/* Test Suppression Warning Banner */}
            {testSuppressed && (
              <div className="bg-rose-50 dark:bg-rose-950/40 border-b border-rose-200 dark:border-rose-900 p-4 text-xs text-rose-700 dark:text-rose-300 flex items-start space-x-2">
                <span className="text-base">🚫</span>
                <div>
                  <strong>Assistant Strictly Suppressed During Scored Test ({suppressedTestType})</strong>
                  <p className="mt-0.5 text-rose-600 dark:text-rose-400">
                    To maintain psychometric evaluation integrity and prevent answer disclosure, Gemini is completely disabled during active scored tests.
                  </p>
                </div>
              </div>
            )}

            {/* Quick Actions */}
            <div className="p-3 border-b border-gray-100 dark:border-gray-800 bg-gray-50/50 dark:bg-gray-800/30 flex items-center space-x-2 overflow-x-auto text-xs">
              <span className="text-gray-400 shrink-0 font-medium ml-2">Quick:</span>
              {[
                "Explain simply",
                "Why was my answer wrong?",
                "What should I study next?",
                "Practice questions",
              ].map((action) => (
                <button
                  key={action}
                  type="button"
                  disabled={testSuppressed}
                  onClick={() => handleQuickAction(action)}
                  className="px-3 py-1.5 rounded-lg border border-purple-200 dark:border-purple-800 bg-white dark:bg-gray-800 text-purple-700 dark:text-purple-300 hover:bg-purple-50 dark:hover:bg-purple-900/30 shrink-0 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {action}
                </button>
              ))}
            </div>

            {/* Message Feed */}
            <div className="flex-1 overflow-y-auto p-6 space-y-4">
              {messages.map((m, idx) => (
                <div
                  key={idx}
                  className={`flex ${m.sender === "user" ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`max-w-[85%] rounded-2xl p-4 text-sm leading-relaxed ${
                      m.sender === "user"
                        ? "bg-purple-600 text-white rounded-br-none shadow-md shadow-purple-500/10"
                        : m.isError
                        ? "bg-rose-50 dark:bg-rose-950/30 text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-900"
                        : "bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-200 rounded-bl-none border border-gray-200/50 dark:border-gray-700"
                    }`}
                  >
                    <div className="whitespace-pre-wrap">{m.text}</div>
                    {m.sender === "ai" && !m.isError && (
                      <div className="mt-2 text-[10px] text-gray-400 dark:text-gray-500 italic">
                        [AI-generated response · Grounded in syllabus metadata]
                      </div>
                    )}
                  </div>
                </div>
              ))}
              {loading && (
                <div className="flex justify-start">
                  <div className="bg-gray-100 dark:bg-gray-800 rounded-2xl p-4 text-sm text-gray-500 dark:text-gray-400 flex items-center space-x-2">
                    <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce" />
                    <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce [animation-delay:0.2s]" />
                    <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce [animation-delay:0.4s]" />
                    <span className="ml-2 text-xs">Synthesizing pedagogical explanation…</span>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Input Bar */}
            <form
              onSubmit={(e) => {
                e.preventDefault();
                sendMessage();
              }}
              className="p-4 border-t border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900 flex items-center space-x-3"
            >
              <input
                type="text"
                disabled={testSuppressed || loading}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder={
                  testSuppressed
                    ? "Assistant disabled during active scored assessment"
                    : "Ask about concepts, exam strategies, or prerequisite rationale…"
                }
                className="flex-1 px-4 py-3 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-purple-500 disabled:opacity-50 disabled:cursor-not-allowed"
              />
              <button
                type="submit"
                disabled={testSuppressed || loading || !input.trim()}
                className="px-5 py-3 rounded-xl font-semibold text-sm bg-purple-600 hover:bg-purple-700 text-white transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              >
                Send
              </button>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
