const test = require("node:test");
const assert = require("node:assert/strict");

require("../renderer/backend-client.js");

test("parseEventBlock extracts event type and payload", () => {
  const rawBlock = [
    "event: tool.result",
    'data: {"type":"tool.result","turn_count":2,"payload":{"tool_name":"list_dir"}}'
  ].join("\n");

  const parsed = globalThis.TinklerBackendClient.parseEventBlock(rawBlock);

  assert.deepEqual(parsed, {
    type: "tool.result",
    payload: {
      type: "tool.result",
      turn_count: 2,
      payload: {
        tool_name: "list_dir"
      }
    }
  });
});
