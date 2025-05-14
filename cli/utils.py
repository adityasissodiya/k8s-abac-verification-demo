import yaml
from pathlib import Path

def load_fixtures(path):
    """
    Load one or more YAML files from a file or directory.
    Returns a list of dicts (parsed YAML documents).
    """
    p = Path(path)
    yamls = []
    if p.is_dir():
        for f in sorted(p.glob("*.yaml")):
            yamls.extend(yaml.safe_load_all(f.read_text()))
    else:
        yamls.extend(yaml.safe_load_all(p.read_text()))
    return yamls

def dump_smt_to_file(smt_code, out_path):
    Path(out_path).write_text(smt_code)
