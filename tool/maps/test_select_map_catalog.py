#!/usr/bin/env python3
"""Quick tests for map selector semantics."""
from select_map_catalog import parse_selector, matches

def ok(expr):
    assert expr, "selector test failed"

def main():
    include, exclude = parse_selector("ir")
    ok(include == {"IR"} and not exclude)
    include, exclude = parse_selector("ALL/ir")
    ok(include is None and exclude == {"IR"})
    include, exclude = parse_selector("all/ir/az")
    ok(include is None and exclude == {"IR", "AZ"})
    iran = {"code": "IR", "country_code": "IR"}
    ir_north = {"code": "IR-NORTH", "country_code": "IR"}
    az = {"code": "AZ", "country_code": "AZ"}
    ok(matches(iran, {"IR"}, set()))
    ok(matches(ir_north, {"IR"}, set()))
    ok(not matches(az, {"IR"}, set()))
    ok(not matches(iran, None, {"IR"}))
    ok(not matches(ir_north, None, {"IR"}))
    ok(matches(az, None, {"IR"}))
    print("selector tests: PASS")

if __name__ == "__main__":
    main()
