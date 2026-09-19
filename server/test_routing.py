"""Self-check for the routing policy: python3 server/test_routing.py"""
import jev_server as j


def test_route_gate():
    # Below the gate the middle tier holds, except luna's clean tool steps...
    assert j.route(j.SOL, "low", 0.2) == (j.SOL, "low", "default", "hold(sol)")
    assert j.route(j.LUNA, "low", 0.2) == (j.SOL, "low", "default", "hold(sol)")
    step = {"step_type": "tool_step", "errored": False}
    assert j.route(j.LUNA, "low", 0.2, step)[3] == "hold(luna_step)"
    # ...and a frontier pick, which the gate never downgrades.
    assert j.route(j.ASTRA, "high", 0.2) == (j.ASTRA, "high", "default", "hold(astra)")
    assert j.route(j.ASTRA, "high", 0.9) == (j.ASTRA, "high", "default", "apply")


def test_dry_chain():
    frontier = j.dry_chain(j.ASTRA, None)
    assert [m for m, _ in frontier] == list(j.DRY_FRONTIER)
    assert {e for _, e in frontier} == {"high"}
    standard = j.dry_chain(j.LUNA, "max")
    assert [m for m, _ in standard] == list(j.DRY_STANDARD)
    assert {e for _, e in standard} == {"max"}
    # Flat-rate plans first, pay-per-token OpenRouter last.
    for chain in (j.DRY_FRONTIER, j.DRY_STANDARD):
        assert chain[-1].startswith("openrouter/") and not chain[0].startswith("openrouter/")


def test_completed_keeps_created_response_id():
    # The router's caller edge announces one id and completes with another on
    # synthesized streams; its own adapter refuses that, so the relay pins it.
    sse = (
        'data: {"type":"response.created","response":{"id":"resp_A"}}\n\n'
        'data: {"type":"response.output_text.delta","delta":"OK"}\n\n'
        'data: {"type":"response.completed","response":{"id":"resp_B","output":[]}}\n\n'
        'data: [DONE]\n\n'
    ).encode()
    for size in (len(sse), 7):  # whole stream, then split mid-event
        m = j.SummaryMarker(" · tag · ")
        out = "".join(m.feed(sse[i:i + size]) for i in range(0, len(sse), size)) + m.flush()
        events = [j.json.loads(l[6:]) for l in out.split("\n") if l.startswith("data: {")]
        assert [e["type"] for e in events] == ["response.created", "response.output_text.delta", "response.completed"]
        assert events[-1]["response"]["id"] == "resp_A"
        assert "data: [DONE]" in out
    # Matching ids (native streams) keep theirs.
    same = sse.replace(b"resp_B", b"resp_A")
    m = j.SummaryMarker(" · tag · ")
    out = m.feed(same) + m.flush()
    done = [j.json.loads(l[6:]) for l in out.split("\n") if '"response.completed"' in l]
    assert done[0]["response"]["id"] == "resp_A"


def test_output_index_resequenced_when_upstream_skips_one():
    # Synthesized streams sometimes open a tool call at index 1 and never open
    # item 0; the router's adapter only accepts 0, 1, 2... in order of appearance.
    sse = (
        'data: {"type":"response.output_item.added","output_index":1,"item":{"id":"fc","type":"function_call"}}\n\n'
        'data: {"type":"response.function_call_arguments.delta","output_index":1,"item_id":"fc","delta":"{}"}\n\n'
        'data: {"type":"response.output_item.done","output_index":1,"item":{"id":"fc","type":"function_call"}}\n\n'
        'data: {"type":"response.output_item.done","output_index":0,"item":{"id":"m","type":"message"}}\n\n'
    ).encode()
    m = j.SummaryMarker(" · tag · ")
    out = m.feed(sse) + m.flush()
    events = [j.json.loads(l[6:]) for l in out.split("\n") if l.startswith("data: {")]
    assert [e["output_index"] for e in events] == [0, 0, 0, 1]
    # In-order streams are left byte-exact.
    ordered = sse.replace(b'"output_index":1', b'"output_index":7').replace(b'"output_index":0', b'"output_index":1').replace(b'"output_index":7', b'"output_index":0')
    m = j.SummaryMarker(" · tag · ")
    assert (m.feed(ordered) + m.flush()).replace("\n\n\n", "\n\n") == ordered.decode()


if __name__ == "__main__":
    test_route_gate()
    test_dry_chain()
    test_completed_keeps_created_response_id()
    test_output_index_resequenced_when_upstream_skips_one()
    print("ok")
