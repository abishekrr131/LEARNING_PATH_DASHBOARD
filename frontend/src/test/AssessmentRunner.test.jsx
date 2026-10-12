import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import AssessmentRunner from "../components/AssessmentRunner";

const mockItems = [
  {
    question_id: 101,
    concept_id: 1,
    concept_name: "Overfitting & Regularization",
    question_text: "What technique directly penalizes large weights?",
    options: {
      A: "L2 Ridge Regularization",
      B: "Gradient Descent",
      C: "Data Augmentation",
      D: "Early Stopping",
    },
    difficulty_hint: 0.2,
  },
  {
    question_id: 102,
    concept_id: 2,
    concept_name: "Cross Validation",
    question_text: "What is K in K-fold cross validation?",
    options: {
      A: "Number of features",
      B: "Number of folds",
      C: "Learning rate",
      D: "Batch size",
    },
    difficulty_hint: 0.1,
  },
];

describe("AssessmentRunner Psychometric Capture Engine", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    global.requestAnimationFrame = (cb) => {
      cb();
      return 1;
    };
    global.cancelAnimationFrame = vi.fn();
  });

  it("renders the question and options with equal-weight skip button", () => {
    render(
      <AssessmentRunner
        assessmentId={1}
        items={mockItems}
        onSubmitted={vi.fn()}
        title="Diagnostic"
      />
    );

    expect(screen.getByText("Question 1 of 2")).toBeInTheDocument();
    expect(
      screen.getByText("What technique directly penalizes large weights?")
    ).toBeInTheDocument();
    expect(screen.getByText("L2 Ridge Regularization")).toBeInTheDocument();

    const skipButton = screen.getByRole("button", { name: /Skip Question/i });
    const nextButton = screen.getByRole("button", { name: /Next Question/i });

    expect(skipButton).toBeInTheDocument();
    expect(nextButton).toBeInTheDocument();
  });

  it("allows selecting an option and submitting the answer", async () => {
    const onSubmitted = vi.fn();
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ assessment_id: 1, score: 1.0, results: [] }),
    });

    render(
      <AssessmentRunner
        assessmentId={1}
        items={[mockItems[0]]}
        onSubmitted={onSubmitted}
      />
    );

    // Click option A
    const optionA = screen.getByText("L2 Ridge Regularization");
    fireEvent.click(optionA);

    // For single item test, button is "Submit & Finish"
    const submitButton = screen.getByRole("button", { name: /Submit & Finish/i });
    expect(submitButton).not.toBeDisabled();
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        "/api/assessments/1/submit",
        expect.objectContaining({
          method: "POST",
          body: expect.stringContaining('"selected_answer":"A"'),
        })
      );
    });
  });

  it("records skipped item as skipped=true and selected_answer=null", async () => {
    const onSubmitted = vi.fn();
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ assessment_id: 1, score: 0.0, results: [] }),
    });

    render(
      <AssessmentRunner
        assessmentId={1}
        items={[mockItems[0]]}
        onSubmitted={onSubmitted}
      />
    );

    const skipButton = screen.getByRole("button", { name: /Skip Question/i });
    fireEvent.click(skipButton);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        "/api/assessments/1/submit",
        expect.objectContaining({
          method: "POST",
          body: expect.stringContaining('"skipped":true'),
        })
      );
    });
  });
});
