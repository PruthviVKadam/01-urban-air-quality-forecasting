import { describe, expect, it } from "vitest";

import { isStale, relativeTime } from "./freshness";

describe("freshness", () => {
  const now = new Date("2026-06-23T12:00:00Z").getTime();

  it("formats recent timestamps", () => {
    const tenMinAgo = new Date(now - 10 * 60_000).toISOString();
    expect(relativeTime(tenMinAgo, now)).toBe("10 min ago");
  });

  it("flags data older than the 3h threshold as stale (HL1)", () => {
    const fourHoursAgo = new Date(now - 4 * 3_600_000).toISOString();
    const oneHourAgo = new Date(now - 1 * 3_600_000).toISOString();
    expect(isStale(fourHoursAgo, 3, now)).toBe(true);
    expect(isStale(oneHourAgo, 3, now)).toBe(false);
  });
});
