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


if __name__ == "__main__":
    test_route_gate()
    test_dry_chain()
    print("ok")
