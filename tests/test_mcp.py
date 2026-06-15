import json
from tools.mcp_server import handle_request, TOOLS


class MockStdout:
    def __init__(self):
        self.output = []

    def write(self, text):
        self.output.append(text)

    def flush(self):
        pass


def test_mcp_initialize(monkeypatch):
    mock_stdout = MockStdout()
    monkeypatch.setattr("sys.stdout", mock_stdout)

    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {}
    }
    
    handle_request(request)
    
    assert len(mock_stdout.output) == 1
    resp = json.loads(mock_stdout.output[0])
    assert resp["id"] == 1
    assert resp["result"]["protocolVersion"] == "2024-11-05"
    assert resp["result"]["serverInfo"]["name"] == "ceaseguard-mcp-server"


def test_mcp_tools_list(monkeypatch):
    mock_stdout = MockStdout()
    monkeypatch.setattr("sys.stdout", mock_stdout)

    request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {}
    }
    
    handle_request(request)
    
    assert len(mock_stdout.output) == 1
    resp = json.loads(mock_stdout.output[0])
    assert resp["id"] == 2
    tools = resp["result"]["tools"]
    assert len(tools) == len(TOOLS)
    assert tools[0]["name"] == "classify_document"
    assert tools[1]["name"] == "search_cease_requests"


def test_mcp_tool_call_not_found(monkeypatch):
    mock_stdout = MockStdout()
    monkeypatch.setattr("sys.stdout", mock_stdout)

    request = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "non_existent_tool",
            "arguments": {}
        }
    }
    
    handle_request(request)
    
    assert len(mock_stdout.output) == 1
    resp = json.loads(mock_stdout.output[0])
    assert resp["id"] == 3
    assert "error" in resp
    assert resp["error"]["code"] == -32601
