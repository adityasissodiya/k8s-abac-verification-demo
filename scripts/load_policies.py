#!/usr/bin/env python3
import argparse
import glob
import os
import subprocess
import sys

def run(cmd, **kwargs):
    print(f"> {' '.join(cmd)}")
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, **kwargs)
    if res.returncode:
        print(res.stdout, res.stderr, sep="\n", file=sys.stderr)
        sys.exit(res.returncode)
    return res

def main():
    parser = argparse.ArgumentParser(
        description="Load XACML policies into AuthzForce via Kubernetes ConfigMap"
    )
    parser.add_argument(
        "--namespace", "-n",
        default="authzforce",
        help="Kubernetes namespace where AuthzForce is deployed (default: authzforce)"
    )
    parser.add_argument(
        "--configmap", "-c",
        default="authzforce-policies",
        help="Name of the ConfigMap to create/update (default: authzforce-policies)"
    )
    parser.add_argument(
        "--deployment", "-d",
        default="authzforce-pdp",
        help="Name of the AuthzForce Deployment to restart (default: authzforce-pdp)"
    )
    parser.add_argument(
        "--policies-dir", "-p",
        default="runtime/policies",
        help="Directory containing XACML policy XML files (default: runtime/policies)"
    )
    args = parser.parse_args()

    # 1) Delete existing ConfigMap (ignore not found)
    run([
        "kubectl", "-n", args.namespace,
        "delete", "configmap", args.configmap,
        "--ignore-not-found"
    ])

    # 2) Build --from-file arguments for each .xml policy
    xml_files = sorted(glob.glob(os.path.join(args.policies_dir, "*.xml")))
    if not xml_files:
        print(f"No .xml policy files found in {args.policies_dir}", file=sys.stderr)
        sys.exit(1)

    create_cmd = [
        "kubectl", "-n", args.namespace,
        "create", "configmap", args.configmap
    ]
    for path in xml_files:
        fname = os.path.basename(path)
        create_cmd.append(f"--from-file={fname}={path}")

    # 3) Create the ConfigMap
    run(create_cmd)

    # 4) Rollout restart the PDP Deployment
    run([
        "kubectl", "-n", args.namespace,
        "rollout", "restart", f"deployment/{args.deployment}"
    ])

    print("\n Policies loaded and AuthzForce PDP restarted successfully.")

if __name__ == "__main__":
    main()
