"""
Hull Forge as an MCP server (Model Context Protocol), standard library only.

It exposes ONE tool, `evaluate_design`, which runs the same physics check the agent uses.
Any MCP-capable assistant (for example Muse Code) can call it over stdio.

Run by an MCP client, not by hand. Example Muse Code entry in ~/.config/muse/settings.json:
  {"mcp_servers": {"hull-forge": {"command": "python3", "args": ["/FULL/PATH/TO/mcp_server.py"]}}}

Protocol: newline-delimited JSON-RPC 2.0 on stdin/stdout (logs go to stderr).
"""
import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from physics import evaluate_design, MATERIALS

SUPPORTED = ["2025-06-18", "2025-03-26", "2024-11-05"]
TOOL = {
    "name": "evaluate_design",
    "description": ("Simulate a submarine pressure hull over its whole service life (buckling, crushing, "
                    "fatigue, buoyancy). Returns pass/fail, safety factors, the dive on which it implodes, "
                    "and hull mass. Simplified teaching model, not engineering software."),
    "inputSchema": {
        "type": "object",
        "properties": {
            "material": {"type": "string", "enum": list(MATERIALS)},
            "shape": {"type": "string", "enum": ["cylinder", "sphere"]},
            "diameter_m": {"type": "number", "description": "Mean diameter in metres"},
            "thickness_mm": {"type": "number"},
            "length_m": {"type": "number", "description": "Cylinder only (default 3.0)"},
            "depth_m": {"type": "number", "description": "Operating depth in metres"},
            "planned_dives": {"type": "integer"},
            "crew": {"type": "integer"},
        },
        "required": ["material", "shape", "diameter_m", "thickness_mm", "depth_m", "planned_dives", "crew"],
    },
}


def reply(msg_id, result=None, error=None):
    out = {"jsonrpc": "2.0", "id": msg_id}
    out.update({"error": error} if error else {"result": result})
    sys.stdout.write(json.dumps(out) + "\n")
    sys.stdout.flush()


def handle(msg):
    method, mid, params = msg.get("method"), msg.get("id"), msg.get("params") or {}
    if mid is None:                       # notification (e.g. notifications/initialized): no reply
        return
    if method == "initialize":
        want = params.get("protocolVersion")
        reply(mid, {"protocolVersion": want if want in SUPPORTED else SUPPORTED[0],
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "hull-forge", "version": "1.0.0"}})
    elif method == "ping":
        reply(mid, {})
    elif method == "tools/list":
        reply(mid, {"tools": [TOOL]})
    elif method == "tools/call":
        if params.get("name") != "evaluate_design":
            reply(mid, error={"code": -32602, "message": f"Unknown tool: {params.get('name')}"})
            return
        try:
            result = evaluate_design(**params.get("arguments", {}))
            is_error = "error" in result
        except TypeError as e:
            result, is_error = {"error": f"Bad arguments: {e}"}, True
        reply(mid, {"content": [{"type": "text", "text": json.dumps(result, indent=2)}], "isError": is_error})
    else:
        reply(mid, error={"code": -32601, "message": f"Method not found: {method}"})


if __name__ == "__main__":
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            handle(json.loads(line))
        except json.JSONDecodeError:
            reply(None, error={"code": -32700, "message": "Parse error"})
        except Exception as e:            # never crash the server on one bad request
            print(f"hull-forge MCP error: {e}", file=sys.stderr)
