import { describe, expect, it } from "vitest";

import { categoryStyle, pollutantLabel } from "./aqi";

describe("categoryStyle", () => {
  it("pairs every AQI category with a distinct shape (non-color cue, G4)", () => {
    const categories = [
      "good",
      "moderate",
      "unhealthy_sensitive",
      "unhealthy",
      "very_unhealthy",
      "hazardous",
    ] as const;
    const shapes = categories.map((c) => categoryStyle(c).shape);
    expect(new Set(shapes).size).toBe(categories.length);
  });

  it("labels pollutants with proper subscripts", () => {
    expect(pollutantLabel("pm25")).toBe("PM₂.₅");
    expect(pollutantLabel("o3")).toBe("O₃");
  });
});
