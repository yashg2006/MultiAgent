import { describeUsage } from "../usage";

const base = { calls: 0, retries: 0, input_tokens: 0, output_tokens: 0, cost_usd: 0 };

describe("describeUsage", () => {
  it("says nothing when no model was called", () => {
    expect(describeUsage(null)).toEqual([]);
    expect(describeUsage(base)).toEqual([]);
  });

  it("reports calls only for the free mock provider (no tokens billed)", () => {
    expect(describeUsage({ ...base, calls: 5 })).toEqual(["5 model calls"]);
  });

  it("reports retries, tokens, and cost for a real provider", () => {
    expect(
      describeUsage({
        calls: 1,
        retries: 1,
        input_tokens: 1200,
        output_tokens: 300,
        cost_usd: 0.02,
      }),
    ).toEqual(["1 model call", "1 retry", "1,500 tokens", "$0.02"]);
  });

  it("rounds tiny costs to a readable bound", () => {
    expect(describeUsage({ ...base, calls: 3, input_tokens: 10, cost_usd: 0.000002 })).toContain(
      "under $0.01",
    );
  });
});
