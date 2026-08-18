import { describe, expect, it } from "vitest";

import {
  cn,
  formatDateTime,
  formatRelativeTime,
  getErrorMessage,
  titleCase,
} from "./utils";

describe("cn", () => {
  it("joins class names", () => {
    expect(cn("a", "b")).toBe("a b");
  });

  it("drops falsy values", () => {
    expect(cn("a", false && "b", undefined, null, "c")).toBe("a c");
  });

  it("resolves conflicting Tailwind utilities in favor of the later one", () => {
    // This is the whole reason tailwind-merge is used instead of plain clsx:
    // a later "flex-row" must win over an earlier "flex-col", not just get
    // appended alongside it.
    expect(cn("flex-col", "flex-row")).toBe("flex-row");
    expect(cn("p-2", "p-4")).toBe("p-4");
  });
});

describe("formatDateTime", () => {
  it("returns an em dash for nullish input", () => {
    expect(formatDateTime(null)).toBe("—");
    expect(formatDateTime(undefined)).toBe("—");
    expect(formatDateTime("")).toBe("—");
  });

  it("returns an em dash for an unparsable date", () => {
    expect(formatDateTime("not a date")).toBe("—");
  });

  it("formats a valid ISO date string", () => {
    const formatted = formatDateTime("2026-08-17T14:05:00Z");
    expect(formatted).toContain("2026");
    expect(formatted).toContain("Aug");
  });
});

describe("formatRelativeTime", () => {
  it("returns an em dash for nullish input", () => {
    expect(formatRelativeTime(null)).toBe("—");
    expect(formatRelativeTime(undefined)).toBe("—");
  });

  it("returns an em dash for an unparsable date", () => {
    expect(formatRelativeTime("not a date")).toBe("—");
  });

  it("describes a moment a few minutes in the past", () => {
    const fiveMinutesAgo = new Date(Date.now() - 5 * 60 * 1000).toISOString();
    expect(formatRelativeTime(fiveMinutesAgo)).toMatch(/minutes? ago/);
  });

  it("describes a moment a few minutes in the future", () => {
    const inFiveMinutes = new Date(Date.now() + 5 * 60 * 1000).toISOString();
    expect(formatRelativeTime(inFiveMinutes)).toMatch(/in \d+ minutes?/);
  });
});

describe("getErrorMessage", () => {
  it("extracts the message from an Error instance", () => {
    expect(getErrorMessage(new Error("boom"))).toBe("boom");
  });

  it("passes through a plain string", () => {
    expect(getErrorMessage("already a string")).toBe("already a string");
  });

  it("falls back to a generic message for anything else", () => {
    expect(getErrorMessage({ weird: "shape" })).toBe(
      "Something went wrong. Please try again.",
    );
    expect(getErrorMessage(null)).toBe("Something went wrong. Please try again.");
  });
});

describe("titleCase", () => {
  it("title-cases a snake_case identifier", () => {
    expect(titleCase("click_house")).toBe("Click House");
  });

  it("title-cases a single lowercase word", () => {
    expect(titleCase("postgres")).toBe("Postgres");
  });

  it("collapses repeated separators", () => {
    expect(titleCase("foo__bar")).toBe("Foo Bar");
  });
});
