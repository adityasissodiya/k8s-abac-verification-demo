import subprocess
import tempfile
import os

def run_smt(smt_code, z3_path="z3"):
    """
    Write smt_code to a temp file, call `z3 -smt2 temp.smt2`, capture output.
    Returns (sat:bool, model:str or None).
    """
    with tempfile.NamedTemporaryFile("w", suffix=".smt2", delete=False) as f:
        f.write(smt_code)
        fname = f.name

    try:
        proc = subprocess.run([z3_path, "-smt2", fname],
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,
                              text=True,
                              timeout=10)
    finally:
        os.unlink(fname)

    out = proc.stdout.strip().splitlines()
    if not out:
        raise RuntimeError("Z3 returned no output; stderr: " + proc.stderr)

    result = out[0]
    if result == "sat":
        return True, "\n".join(out[1:])
    elif result == "unsat":
        return False, None
    else:
        raise RuntimeError(f"Unexpected Z3 result: {result}\nFull output:\n{proc.stdout}")
