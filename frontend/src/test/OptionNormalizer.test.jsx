import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { toOptionList } from "../utils/options";
import AssessmentRunner from "../components/AssessmentRunner";

describe("toOptionList Normalizer Helper", () => {
  it("converts object options to [{key, text}] format", () => {
    const input = {
      A: "Option A text",
      B: "Option B text",
      C: "Option C text",
      D: "Option D text",
    };
    const output = toOptionList(input);
    expect(output).toEqual([
      { key: "A", text: "Option A text" },
      { key: "B", text: "Option B text" },
      { key: "C", text: "Option C text" },
      { key: "D", text: "Option D text" },
    ]);
  });

  it("passes through array of {key, text} objects properly", () => {
    const input = [
      { key: "A", text: "First choice" },
      { key: "B", text: "Second choice" },
    ];
    const output = toOptionList(input);
    expect(output).toEqual([
      { key: "A", text: "First choice" },
      { key: "B", text: "Second choice" },
    ]);
  });

  it("converts array of plain strings to keyed [{key, text}]", () => {
    const input = ["Alpha item", "Beta item", "Gamma item", "Delta item"];
    const output = toOptionList(input);
    expect(output).toEqual([
      { key: "A", text: "Alpha item" },
      { key: "B", text: "Beta item" },
      { key: "C", text: "Gamma item" },
      { key: "D", text: "Delta item" },
    ]);
  });

  it("parses valid JSON string format", () => {
    const jsonInput = JSON.stringify({ A: "JSON Alpha", B: "JSON Beta" });
    const output = toOptionList(jsonInput);
    expect(output).toEqual([
      { key: "A", text: "JSON Alpha" },
      { key: "B", text: "JSON Beta" },
    ]);
  });

  it("returns empty array safely on null, undefined or empty values", () => {
    expect(toOptionList(null)).toEqual([]);
    expect(toOptionList(undefined)).toEqual([]);
    expect(toOptionList("")).toEqual([]);
    expect(toOptionList("invalid json string")).toEqual([]);
  });
});

describe("Question Component Resilience with Object and Array Options", () => {
  beforeEach(() => {
    global.requestAnimationFrame = (cb) => {
      cb();
      return 1;
    };
    global.cancelAnimationFrame = vi.fn();
  });

  it("renders AssessmentRunner with object options {A, B, C, D} without crash", () => {
    const items = [
      {
        question_id: 1,
        concept_id: 10,
        concept_name: "Percentages & Ratios",
        question_text: "What is 20% of 250?",
        options: {
          A: "50",
          B: "60",
          C: "45",
          D: "55",
        },
        source: "gemini",
      },
    ];

    render(
      <AssessmentRunner
        assessmentId={100}
        items={items}
        onSubmitted={vi.fn()}
        title="Diagnostic"
      />
    );

    expect(screen.getByText("What is 20% of 250?")).toBeInTheDocument();
    expect(screen.getByText("50")).toBeInTheDocument();
    expect(screen.getByText("60")).toBeInTheDocument();
    expect(screen.getByText("✨ AI-Generated")).toBeInTheDocument();
  });

  it("renders AssessmentRunner with array options [{key, text}] without crash", () => {
    const items = [
      {
        question_id: 2,
        concept_id: 11,
        concept_name: "Time and Work",
        question_text: "If A can do a job in 10 days, what is A's 1-day work?",
        options: [
          { key: "A", text: "1/10" },
          { key: "B", text: "1/5" },
          { key: "C", text: "10" },
          { key: "D", text: "None of these" },
        ],
        source: "curated",
      },
    ];

    render(
      <AssessmentRunner
        assessmentId={101}
        items={items}
        onSubmitted={vi.fn()}
        title="Weekly Test"
      />
    );

    expect(screen.getByText("If A can do a job in 10 days, what is A's 1-day work?")).toBeInTheDocument();
    expect(screen.getByText("1/10")).toBeInTheDocument();
    expect(screen.getByText("📚 Question Bank")).toBeInTheDocument();
  });
});
