import { describe, expect, it, vi } from "vitest";

import { withRetry } from "../../src/shared/retry";

describe("withRetry", () => {
  it("returns success on third attempt after two failures", async () => {
    let attempts = 0;

    const result = await withRetry(
      async () => {
        attempts += 1;

        if (attempts < 3) {
          throw new Error(`transient error ${attempts}`);
        }

        return "ok";
      },
      {
        maxAttempts: 3,
        initialDelayMs: 0,
      },
    );

    expect(result).toBe("ok");
    expect(attempts).toBe(3);
  });

  it("throws the original error after max attempts is exceeded", async () => {
    const originalError = new Error("service unavailable");
    const operation = vi.fn().mockRejectedValue(originalError);

    await expect(
      withRetry(operation, {
        maxAttempts: 3,
        initialDelayMs: 0,
      }),
    ).rejects.toBe(originalError);

    expect(operation).toHaveBeenCalledTimes(3);
  });
});
