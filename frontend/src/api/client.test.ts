import { afterEach, describe, expect, it, vi } from "vitest";

import { api, ApiError, buildQuery } from "./client";

describe("buildQuery", () => {
  it("returns an empty string when there are no params", () => {
    expect(buildQuery({})).toBe("");
  });

  it("skips undefined and empty-string values", () => {
    expect(buildQuery({ a: undefined, b: "", c: "kept" })).toBe("?c=kept");
  });

  it("stringifies numeric values", () => {
    expect(buildQuery({ limit: 20, skip: 0 })).toBe("?limit=20&skip=0");
  });

  it("keeps a value of the number zero (only '' and undefined are skipped)", () => {
    expect(buildQuery({ skip: 0 })).toBe("?skip=0");
  });
});

function jsonResponse(body: unknown, status: number) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("api error handling", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("throws ApiError with the backend's string detail message", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse({ detail: "Source not found" }, 404)),
    );

    await expect(api.get("/sources/999")).rejects.toMatchObject({
      name: "ApiError",
      status: 404,
      message: "Source not found",
    });
  });

  it("joins FastAPI validation-error arrays into one message", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          jsonResponse(
            { detail: [{ msg: "field required" }, { msg: "must be positive" }] },
            422,
          ),
        ),
    );

    await expect(api.post("/sources/", {})).rejects.toMatchObject({
      status: 422,
      message: "field required; must be positive",
    });
  });

  it("falls back to a generic message when the error body isn't JSON", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(new Response("<html>502 Bad Gateway</html>", { status: 502 })),
    );

    await expect(api.get("/sources/")).rejects.toMatchObject({
      status: 502,
      message: "Request failed with status 502",
    });
  });

  it("resolves undefined for a 204 No Content response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(null, { status: 204 })),
    );

    await expect(api.delete("/sources/1")).resolves.toBeUndefined();
  });

  it("is a real Error subclass", () => {
    const error = new ApiError("boom", 500);
    expect(error).toBeInstanceOf(Error);
    expect(error.status).toBe(500);
  });
});
