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

	try:
		fixtures = load_fixtures(args.input)
	except Exception as e:
		print(f"REJECTED: malformed input file ({e})", file=sys.stderr)
		sys.exit(1)
	if not fixtures:
		print("No fixtures found in", args.input, file=sys.stderr)
		sys.exit(1)

	status = 0
	for fx in fixtures:
		case = detect_case(fx)
		print(f"--- Checking {fx.get('name','<unnamed>')} ({case}) ---")
		# ──────── Attempt to build the SMT model ────────
		try:
			if case == "registry":
				smt = build_smt_for_registry(fx)
			elif case == "wildcard":
				smt = build_smt_for_wildcard(fx)
			else:
				smt = build_smt_for_tenant(fx)
		except KeyError as e:
			# Missing required field in the fixture
			print(f"REJECTED: malformed policy (missing key {e})")
			status = 1
			print()
			continue
		except Exception as e:
			# Any other parse/model‐building error
			print(f"REJECTED: malformed policy ({e})")
			status = 1
			print()
			continue

		# ──────── Run SMT and interpret results ────────
		try:
			sat, model = run_smt(smt)
		except RuntimeError as e:
			# Z3 returned “unknown” or another unexpected result
			print(f"ERROR: SMT solver failed ({e})")
			status = 1
			print()
			continue

		if sat:
			# solver found a violation
			print("INVALID: counterexample found")
			if args.verbose:
				print(model)
			status = 1
		else:
			# unsat ⇒ no violation
			print("VALID (no violation)")
		print()      
	sys.exit(status)

if __name__ == "__main__":
	main()
