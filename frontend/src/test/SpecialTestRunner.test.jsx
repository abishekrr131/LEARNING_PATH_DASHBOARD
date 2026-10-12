import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, act } from "@testing-library/react";
import SpecialTestRunner from "../components/SpecialTestRunner";

const mockInitialItems = [
  {
    question_id: 201,
    concept_id: 10,
    concept_name: "Attention Mechanism",
    question_text: "What vector computes query-key alignment?",
    options: {
      A: "Softmax weights",
      B: "Feedforward output",
      C: "Positional encoding",
      D: "Layer norm",
    },
    difficulty_hint: 0.4,
  },
];

describe("SpecialTestRunner Timed Engine", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    global.requestAnimationFrame = (cb) => {
      cb();
      return 1;
    };
    global.cancelAnimationFrame = vi.fn();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders countdown ring with 30s limit for main question", () => {
    render(
      <SpecialTestRunner
        assessmentId={1}
        initialItems={mockInitialItems}
        onCompleted={vi.fn()}
      />
    );

    expect(screen.getByText("30s")).toBeInTheDocument();
    expect(screen.getByText("What vector computes query-key alignment?")).toBeInTheDocument();
    expect(screen.getByText(/Main 1\/1/i)).toBeInTheDocument();
  });

  it("decrements timer and enters coral warning zone in last 5 seconds", () => {
    const { container } = render(
      <SpecialTestRunner
        assessmentId={1}
        initialItems={mockInitialItems}
        onCompleted={vi.fn()}
      />
    );

    // Fast-forward 26 seconds (4s left)
    act(() => {
      vi.advanceTimersByTime(26000);
    });

    // Timer is <= 5, renders 4s with coral class text-rose-500
    expect(screen.getByText("4s")).toBeInTheDocument();
    const coralElements = container.querySelectorAll(".text-rose-500");
    expect(coralElements.length).toBeGreaterThan(0);
  });
});
