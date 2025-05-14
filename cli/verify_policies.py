#!/usr/bin/env python3
import argparse
import sys
from utils import load_fixtures
from model_builder import (
    build_smt_for_registry,
    build_smt_for_wildcard,
    build_smt_for_tenant
)
from solver_interface import run_smt

def detect_case(fixture):
    """Heuristic: decide which case this fixture is for."""
    kind = fixture.get("case")
    if kind == "registry": return "registry"
    if kind == "wildcard": return "wildcard"
    if kind == "tenant":   return "tenant"
    raise ValueError("Unknown case in fixture: " + repr(kind))

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", "-i", required=True,
                   help="Path to fixture YAML (file or dir)")
    p.add_argument("--equivalence", action="store_true",
                   help="Also check ABAC⊂RBAC and RBAC⊂ABAC")
    p.add_argument("--verbose", "-v", action="store_true")
    args = p.parse_args()

    fixtures = load_fixtures(args.input)
    if not fixtures:
        print("No fixtures found in", args.input, file=sys.stderr)
        sys.exit(1)

    status = 0
    for fx in fixtures:
        case = detect_case(fx)
        print(f"--- Checking {fx.get('name','<unnamed>')} ({case}) ---")
        if case == "registry":
            smt = build_smt_for_registry(fx)
        elif case == "wildcard":
            smt = build_smt_for_wildcard(fx)
        else:
            smt = build_smt_for_tenant(fx)

        sat, model = run_smt(smt)
        if sat:
            print("VIOLATION detected! Counterexample:")
            if args.verbose:
                print(model)
            status = 1
        else:
            print("No violation (unsat).")
        print()

    sys.exit(status)

if __name__ == "__main__":
    main()
