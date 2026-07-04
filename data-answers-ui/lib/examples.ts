import type { ExampleScenario } from "./types";

export const EXAMPLE_SCENARIOS: ExampleScenario[] = [
  {
    label: "Happy path",
    description: "Grounded total revenue question",
    question: "What was total revenue last month?",
    userId: "u1",
    regions: "US, EU",
  },
  {
    label: "Clarification",
    description: "Ambiguous revenue metric",
    question: "What was revenue last month?",
    userId: "u1",
    regions: "US, EU",
  },
  {
    label: "Out of scope",
    description: "No matching metric in registry",
    question: "How many unicorns do we have?",
    userId: "u1",
    regions: "US, EU",
  },
  {
    label: "Policy deny",
    description: "Principal with no allowed regions",
    question: "What was total revenue last month?",
    userId: "u2",
    regions: "",
  },
];
