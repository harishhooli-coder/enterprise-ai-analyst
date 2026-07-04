import type { ExampleScenario } from "./types";

export const EXAMPLE_SCENARIOS: ExampleScenario[] = [
  {
    label: "Total revenue last month",
    description: "Get a grounded revenue answer",
    question: "What was total revenue last month?",
    userId: "u1",
    regions: "US, EU",
  },
  {
    label: "Revenue (needs detail)",
    description: "See how ambiguous questions are handled",
    question: "What was revenue last month?",
    userId: "u1",
    regions: "US, EU",
  },
  {
    label: "Out-of-scope question",
    description: "Questions outside available metrics",
    question: "How many unicorns do we have?",
    userId: "u1",
    regions: "US, EU",
  },
  {
    label: "Access-restricted user",
    description: "User with no allowed regions",
    question: "What was total revenue last month?",
    userId: "u2",
    regions: "",
  },
];

export const SUGGESTED_PROMPTS = EXAMPLE_SCENARIOS.slice(0, 3).map(
  (example) => example.question,
);
