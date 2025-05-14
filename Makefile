test-cli:
	cd cli && . .venv/bin/activate && python verify_policies.py --input fixtures/
