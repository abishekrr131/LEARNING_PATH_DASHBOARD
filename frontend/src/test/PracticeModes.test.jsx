import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import { BrowserRouter, MemoryRouter } from "react-router-dom";
import { ThemeProvider } from "../context/ThemeContext";
import PracticeMode from "../pages/PracticeMode";
import * as client from "../api/client";

// Mock AuthContext
vi.mock("../context/AuthContext", () => ({
  useAuth: () => ({
    user: { id: 1, email: "test@google.com", name: "Tester" },
    profile: { id: 1, target_id: 7, target_name: "Banking & Financial Services (IBPS PO)" },
  }),
}));

const mockUntimedItems = [
  {
    question_id: 201,
    concept_id: 10,
    concept_name: "Simplification",
    topic_name: "Simplification & Approximation",
    skill_name: "Quantitative Aptitude",
    question_text: "What is 25% of 400 + 15?",
    options: { A: "115", B: "105", C: "125", D: "95" },
    correct_option: "A",
    explanation: "25% of 400 is 100. 100 + 15 = 115.",
  },
  {
    question_id: 202,
    concept_id: 11,
    concept_name: "Percentages",
    topic_name: "Percentages & Ratio",
    skill_name: "Quantitative Aptitude",
    question_text: "If x is 20% more than 50, find x.",
    options: { A: "60", B: "70", C: "55", D: "65" },
    correct_option: "A",
    explanation: "20% of 50 is 10. 50 + 10 = 60.",
  },
];

const mockCombinedItems = Array.from({ length: 40 }, (_, idx) => ({
  question_id: 300 + idx,
  concept_id: 10 + (idx % 5),
  concept_name: `Concept ${idx + 1}`,
  topic_name: `Topic ${idx + 1}`,
  skill_name:
    idx < 14
      ? "Quantitative Aptitude"
      : idx < 26
      ? "Reasoning Ability"
      : "English Language",
  question_text: `Combined Mock Question ${idx + 1}?`,
  options: { A: "Option 1", B: "Option 2", C: "Option 3", D: "Option 4" },
  correct_option: "A",
  explanation: `Explanation for Question ${idx + 1}`,
}));

const mockSpeedItems = [
  {
    question_id: 401,
    concept_id: 15,
    concept_name: "Profit & Loss",
    topic_name: "Profit & Loss",
    skill_name: "Quantitative Aptitude",
    question_text: "Cost price is 100, Selling price is 120. Find Profit %.",
    options: { A: "20%", B: "25%", C: "15%", D: "10%" },
    correct_option: "A",
    explanation: "Profit = 20 / 100 = 20%.",
  },
];

const mockSubQuestions = {
  question_id: 401,
  topic_name: "Profit & Loss",
  concept_name: "Profit & Loss",
  has_sub_questions: true,
  sub_questions: [
    {
      id: 501,
      stage: "formula_recall",
      order: 1,
      stem: "What is the formula for Profit %?",
      options: { A: "(Profit / CP) * 100", B: "(Profit / SP) * 100" },
      correct_option: "A",
    },
    {
      id: 502,
      stage: "substitution",
      order: 2,
      stem: "Substitute SP=120 and CP=100 into Profit formula.",
      options: { A: "120 - 100 = 20", B: "100 - 120 = -20" },
      correct_option: "A",
    },
    {
      id: 503,
      stage: "calculation",
      order: 3,
      stem: "Compute (20 / 100) * 100.",
      options: { A: "20%", B: "25%" },
      correct_option: "A",
    },
  ],
};

describe("PracticeMode: 3 Interactive Modes", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(client.targetApi, "getDetail").mockResolvedValue({
      id: 7,
      name: "Banking IBPS PO",
      skills: [
        {
          id: 1,
          name: "Quantitative Aptitude",
          topics: [{ id: 10, name: "Simplification" }],
        },
      ],
    });
  });

  afterEach(() => {
    cleanup();
  });

  it("1. Mode 1 - Practice (untimed): topic/count select, no timer, reveals worked explanation", async () => {
    vi.spyOn(client.assessmentApi, "start").mockResolvedValue({
      assessment_id: 88,
      type: "practice",
      items: mockUntimedItems,
    });

    const { unmount } = render(
      <ThemeProvider>
        <MemoryRouter initialEntries={["/practice"]}>
          <PracticeMode />
        </MemoryRouter>
      </ThemeProvider>
    );

    // Initial setup screen
    expect(screen.getByText("Practice & Mock Test Hub")).toBeInTheDocument();
    expect(screen.getByTestId("mode-tab-untimed")).toBeInTheDocument();

    // Click Start Practice
    fireEvent.click(screen.getByTestId("start-practice-btn"));

    await waitFor(() => {
      expect(screen.getByText("Question 1 of 2")).toBeInTheDocument();
    });

    // Check that NO timer is present
    expect(screen.queryByTestId("combined-countdown")).not.toBeInTheDocument();
    expect(screen.queryByTestId("speed-countdown")).not.toBeInTheDocument();

    // Check question stem and options
    expect(screen.getByText("What is 25% of 400 + 15?")).toBeInTheDocument();
    expect(screen.getByText("115")).toBeInTheDocument();

    // Select option A and click Check Answer
    fireEvent.click(screen.getByText("115"));
    fireEvent.click(screen.getByTestId("check-answer-btn"));

    // Check that worked explanation is revealed
    await waitFor(() => {
      expect(screen.getByTestId("worked-explanation-card")).toBeInTheDocument();
      expect(screen.getByText("25% of 400 is 100. 100 + 15 = 115.")).toBeInTheDocument();
      expect(screen.getByText("✓ Correct")).toBeInTheDocument();
    });

    // Click Next Question
    fireEvent.click(screen.getByTestId("next-untimed-btn"));
    await waitFor(() => {
      expect(screen.getByText("Question 2 of 2")).toBeInTheDocument();
      expect(screen.getByText("If x is 20% more than 50, find x.")).toBeInTheDocument();
    });
    unmount();
  });

  it("2. Mode 2 - Combined Test: 60-min countdown, 1..40 Question Palette, jump and section breakdown", async () => {
    vi.spyOn(client.assessmentApi, "start").mockResolvedValue({
      assessment_id: 89,
      type: "practice",
      items: mockCombinedItems,
      time_limit_sec: 3600,
    });

    const { unmount } = render(
      <ThemeProvider>
        <MemoryRouter initialEntries={["/practice?mode=combined"]}>
          <PracticeMode />
        </MemoryRouter>
      </ThemeProvider>
    );

    // Click Start Combined Test
    const startBtn = await screen.findByRole("button", { name: /Start Combined Test/i });
    fireEvent.click(startBtn);

    await waitFor(() => {
      // 60-min timer visible (displays 60:00 or 59:59)
      expect(screen.getByTestId("combined-countdown")).toBeInTheDocument();
      // Question Palette visible with buttons 1 to 40
      expect(screen.getByTestId("question-palette")).toBeInTheDocument();
      expect(screen.getByTestId("palette-btn-1")).toBeInTheDocument();
      expect(screen.getByTestId("palette-btn-40")).toBeInTheDocument();
    });

    // Jump to Question 15 via palette
    fireEvent.click(screen.getByTestId("palette-btn-15"));
    await waitFor(() => {
      expect(screen.getByText("Question 15 of 40")).toBeInTheDocument();
      expect(screen.getByText("Combined Mock Question 15?")).toBeInTheDocument();
    });

    // Flag Question 15 for review
    fireEvent.click(screen.getByTestId("flag-review-btn"));
    expect(screen.getByText("★ Flagged for Review")).toBeInTheDocument();

    // Select option A on question 15
    fireEvent.click(screen.getByTestId("option-btn-A"));

    // Submit combined test
    fireEvent.click(screen.getByTestId("submit-combined-test-btn"));

    // Verify section breakdown results
    await waitFor(() => {
      expect(screen.getByTestId("practice-results-view")).toBeInTheDocument();
      expect(screen.getByTestId("section-breakdown")).toBeInTheDocument();
      expect(screen.getByText("Section-Wise Performance Breakdown")).toBeInTheDocument();
      expect(screen.getByText("Quantitative Aptitude")).toBeInTheDocument();
      expect(screen.getByText("Reasoning Ability")).toBeInTheDocument();
      expect(screen.getByText("English Language")).toBeInTheDocument();
    });
    unmount();
  });

  it("3. Mode 3 - Speed Test: 90s timer, wrong answer triggers 3 sub-questions & root-cause gap", async () => {
    vi.spyOn(client.assessmentApi, "start").mockResolvedValue({
      assessment_id: 90,
      type: "practice",
      items: mockSpeedItems,
      time_limit_sec: 90,
    });
    vi.spyOn(client.assessmentApi, "getSubQuestions").mockResolvedValue(mockSubQuestions);
    vi.spyOn(client.assessmentApi, "evaluateRootCause").mockResolvedValue({
      question_id: 401,
      gap_type: "Calculation accuracy gap",
      study_task: "Practice arithmetic accuracy drills under time limits",
    });

    render(
      <ThemeProvider>
        <MemoryRouter initialEntries={["/practice?mode=speed"]}>
          <PracticeMode />
        </MemoryRouter>
      </ThemeProvider>
    );

    // Initial speed screen
    const startBtn = await screen.findByRole("button", { name: /Start Speed Drills/i });
    fireEvent.click(startBtn);

    await waitFor(() => {
      // 90s timer displayed
      expect(screen.getByTestId("speed-countdown")).toBeInTheDocument();
      expect(screen.getByText(/Speed Drill 1 of 1/i)).toBeInTheDocument();
    });

    // Deliberately choose wrong answer B (correct is A)
    fireEvent.click(screen.getByText("25%"));
    fireEvent.click(screen.getByTestId("submit-speed-answer-btn"));

    // Verify diagnostic sub-questions flow triggers
    await waitFor(() => {
      expect(screen.getByTestId("sub-questions-flow")).toBeInTheDocument();
      expect(screen.getByText("🚨 Root Cause Diagnosis Triggered")).toBeInTheDocument();
      expect(screen.getByText("Stage: formula_recall")).toBeInTheDocument();
      expect(screen.getByText("What is the formula for Profit %?")).toBeInTheDocument();
    });

    // Answer Stage 1 (Formula)
    fireEvent.click(screen.getByText("(Profit / CP) * 100"));
    fireEvent.click(screen.getByTestId("confirm-sub-btn"));

    // Answer Stage 2 (Substitution)
    await waitFor(() => {
      expect(screen.getByText("Stage: substitution")).toBeInTheDocument();
      expect(screen.getByText("120 - 100 = 20")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText("120 - 100 = 20"));
    fireEvent.click(screen.getByTestId("confirm-sub-btn"));

    // Answer Stage 3 (Calculation)
    await waitFor(() => {
      expect(screen.getByText("Stage: calculation")).toBeInTheDocument();
      expect(screen.getByText("Compute (20 / 100) * 100.")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText("25%")); // wrong calculation
    fireEvent.click(screen.getByTestId("confirm-sub-btn"));

    // Verify root cause evaluation banner
    await waitFor(() => {
      expect(screen.getByTestId("root-cause-result-banner")).toBeInTheDocument();
      expect(
        screen.getByText("Cognitive Gap Identified: Calculation accuracy gap")
      ).toBeInTheDocument();
      expect(
        screen.getByText("Practice arithmetic accuracy drills under time limits")
      ).toBeInTheDocument();
    });

    // Click Continue
    fireEvent.click(screen.getByTestId("continue-speed-btn"));

    // Verify causes found list in final report
    await waitFor(() => {
      expect(screen.getByTestId("practice-results-view")).toBeInTheDocument();
      expect(screen.getByTestId("causes-found-list")).toBeInTheDocument();
      expect(screen.getByText("Calculation accuracy gap")).toBeInTheDocument();
    });
  });
});
