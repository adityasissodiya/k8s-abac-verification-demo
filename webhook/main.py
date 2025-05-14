#!/usr/bin/env python3
import json, os
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

PDP_URL = os.getenv("PDP_URL", "https://authzforce-pdp-service.authzforce.svc/services/pdp")
VERIFY_TLS = os.getenv("VERIFY_TLS", "/etc/webhook/ca.crt")  # CA to trust

def make_xacml_request(ar):
    # Build minimal XACML-JSON from AdmissionReview
    req = ar["request"]
    kind = req["object"]["kind"]
    namespace = req["requestNamespace"] or ""
    op = req["operation"].lower()
    attrs = {
        "Request": {
            "AccessSubject": {
                "attributes": [{
                    "AttributeId": "urn:k8s:subject:namespace",
                    "Value": namespace
                }]
            },
            "Action": {
                "attributes": [{
                    "AttributeId": "urn:k8s:action:operation",
                    "Value": op
                }]
            },
            "Resource": {
                "attributes": [
                    { "AttributeId": "urn:k8s:resource:kind", "Value": kind }
                ]
            },
            "Environment": { "attributes": [] }
        }
    }
    # If a Pod creation, extract .spec.containers[].imageRegistry
    if kind == "Pod" and op == "create":
        images = [c["image"] for c in req["object"]["spec"]["containers"]]
        # assume registry is prefix before "/"
        registry = images[0].split("/")[0]
        attrs["Request"]["Resource"]["attributes"].append({
            "AttributeId": "urn:k8s:resource:imageRegistry",
            "Value": registry
        })
    return attrs

@app.route("/validate", methods=["POST"])
def validate():
    review = request.get_json()
    xacml = make_xacml_request(review)
    # call PDP
    resp = requests.post(
        PDP_URL,
        json=xacml,
        headers={"Content-Type": "application/xacml+json"},
        verify=VERIFY_TLS
    )
    decision = resp.json()["Response"]["Decision"]
    allow = (decision == "Permit")
    uid = review["request"]["uid"]
    return jsonify({
        "apiVersion": "admission.k8s.io/v1",
        "kind": "AdmissionReview",
        "response": {
            "uid": uid,
            "allowed": allow,
            "status": {
                "code": 403 if not allow else 200,
                "message": f"Denied by ABAC policy: {decision}" if not allow else "Allowed"
            }
        }
    })

if __name__ == "__main__":
    # TLS key/cert mounted at /etc/webhook/tls.crt, tls.key
    app.run(host="0.0.0.0", port=8443, ssl_context=(
        "/etc/webhook/tls.crt",
        "/etc/webhook/tls.key"
    ))
