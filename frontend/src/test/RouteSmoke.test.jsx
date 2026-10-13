import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import App from "../App";

// Mock fetch globally for all API endpoints to avoid unhandled network calls
beforeEach(() => {
  global.fetch = vi.fn().mockImplementation((url) => {
    const urlStr = String(url);
    if (urlStr.includes("/auth/google") || urlStr.includes("/auth/refresh")) {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => ({
          access_token: "mock-token",
          refresh_token: "mock-refresh",
          user: { id: 1, name: "Test User", email: "test@example.com", target_id: 7 },
        }),
      });
    }
    if (urlStr.includes("/me/profile") || urlStr.includes("/me")) {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => ({
          user_id: 1,
          name: "Test Learner",
          email: "learner@test.com",
          target_id: 7,
          target_name: "Banking (IBPS PO)",
          current_level: "intermediate",
        }),
      });
    }
    if (urlStr.includes("/diagnostic/start") || urlStr.includes("/assessments/start")) {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => ({
          assessment_id: 101,
          type: "initial",
          target_id: 7,
          items: [],
        }),
      });
    }
    if (urlStr.includes("/weekly-test/status")) {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => ({
          is_due: false,
          is_overdue: false,
          status: "pending",
        }),
      });
    }
    // Generic fallback
    return Promise.resolve({
      ok: true,
      status: 200,
      json: async () => ({}),
    });
  });

  // Mock localStorage with auth token
  localStorage.setItem("palp_access_token", "mock-access-token-123");
});

describe("Frontend Route Smoke Test", () => {
  const routesToTest = [
    "/",
    "/login",
    "/onboarding",
    "/dashboard",
    "/weak-topics",
    "/root-cause",
    "/progress",
    "/learning-path",
    "/resources",
    "/schedule",
    "/assessments",
    "/diagnostic/instructions",
    "/diagnostic",
    "/weekly-test",
    "/special-test",
    "/verification",
    "/followup",
    "/practice",
    "/settings",
    "/ai-analysis",
    "/result/1",
    "/weekly-test/result/1",
  ];

  routesToTest.forEach((route) => {
    it(`renders route "${route}" without crashing or throwing a render error`, async () => {
      window.history.pushState({}, "Test page", route);
      const { container } = render(<App />);
      expect(container).toBeDefined();
    });
  });

  it("renders DiagnosticRunner with loaded items and AssessmentRunner without ReferenceError", async () => {
    const mockAssessment = {
      assessment_id: 42,
      items: [
        {
          question_id: 1,
          concept_id: 1,
          concept_name: "Percentages",
          order_index: 0,
          question_text: "What is 20% of 100?",
          options: [{ key: "A", text: "20" }, { key: "B", text: "30" }],
        },
      ],
    };
    window.history.pushState({ assessment: mockAssessment }, "Diagnostic", "/diagnostic");
    const { container } = render(<App />);
    expect(container).toBeDefined();
  });
});
