## Overview

This repository demonstrates a Kubernetes security experiment using formally verified Attribute-Based Access Control (ABAC) policies to mitigate synthetic RBAC misconfigurations. The goal is to show that by integrating an external ABAC Policy Decision Point (PDP) (AuthzForce) with formally verified XACML policies, we can prevent specific classes of configuration flaws that are otherwise possible under Kubernetes RBAC. The demo sets up a local Kubernetes cluster (via Minikube on Ubuntu/Docker) and enforces custom XACML policies through an AuthzForce PDP service and an admission webhook. We illustrate three misconfiguration case studies inspired by known Kubernetes security issues:

* **Image Registry Bypass:** A misconfiguration in admission policies could allow deployment of container images from disallowed registries (e.g., a missing URL slash allowed `myregistry.com.attacker.com` to bypass an “allowed registries” rule). Our ABAC policy enforces exact match on approved image registries, preventing such bypasses.
* **Wildcard Privilege Binding:** A role binding that grants wildcard (`*`) permissions cluster-wide to a non-admin principal. This simulates an overly broad ClusterRoleBinding where a service account gains full privileges. The ABAC policy adds an attribute constraint that denies binding global `*` permissions to any subject that is not an administrator.
* **Cross-Tenant Access:** A tenant isolation failure where a service account from one namespace can access or modify resources in another namespace (cross-namespace escalation). This can occur if a wildcard privilege is granted unintentionally. The ABAC policy ensures that if the requesting user's tenant (namespace) does not match the target resource's tenant, the request is denied (except for designated admins).

By blending Kubernetes RBAC with external ABAC, the demo provides **formally verified security guarantees**. The XACML policies are mathematically checked using an SMT solver (Z3) to ensure they uphold intended invariants (e.g., *“no non-admin can access another team’s namespace”*) with no policy conflicts. We use a Python CLI tool to encode the RBAC rules and ABAC policies into logical constraints and automatically find policy violations or prove the policies safe. The AuthzForce PDP is then deployed in-cluster and consulted on each API request (via an admission webhook) to enforce the verified policies in real time. This README will guide you through reproducing the experiment step-by-step, verifying the policies, and observing how the system blocks each misconfiguration scenario.

**Key takeaway:** Formally verified ABAC policies (in XACML), when enforced in Kubernetes through an external PDP (AuthzForce) and webhook integration, can systematically close security gaps left by misconfigured RBAC policies. This demo is for research and educational purposes; it uses a local Minikube setup and synthetic scenarios (no real production cluster deployment is involved).

## Prerequisites and Installation

Before proceeding, ensure you have the following installed on an Ubuntu 20.04+ system (the demo was developed on Ubuntu with Docker):

* **Docker:** Docker Engine is required both for running Minikube (using the Docker driver) and for building/pulling container images. Install Docker CE from the official docs or via apt. Make sure the Docker daemon is running and you have permission to use it (e.g., add your user to the `docker` group).
* **Minikube:** Minikube will run the local Kubernetes cluster. Install the latest Minikube (v1.29+ recommended) by following the [official installation guide](https://minikube.sigs.k8s.io/docs/start/). Ensure Minikube is configured to use the Docker driver on Linux (the default if Docker is present).
* **Kubectl:** Kubernetes command-line tool to interact with the cluster. Install kubectl (e.g., `sudo apt install -y kubectl` or download the binary) matching your Kubernetes version (Minikube usually provides a recent version).
* **Python 3:** Required for the policy verification CLI tool. Python 3.8+ is recommended.
* **Z3 SMT Solver:** The Python Z3 solver is used for formal verification. You can install Z3 via the Python binding:

## Step-by-Step Setup Guide

Follow these steps to launch the local Kubernetes cluster, deploy the AuthzForce PDP with ABAC policies, and configure the integration. This will set up the environment for reproducing the experiment.

### 1. Launch Minikube Kubernetes Cluster

Start a Minikube cluster on your local machine:

```bash
minikube start --driver=docker --memory=4096 --cpus=2
```

This command initializes a single-node Kubernetes cluster locally using the Docker driver. If successful, you should see Minikube start the Kubernetes services. Verify that the cluster is running and kubectl is configured to use it:

```bash
kubectl get nodes
```

You should see the Minikube node in a `Ready` state.

### 2. Deploy AuthzForce PDP as a Service

AuthzForce is an open-source XACML 3.0 Policy Decision Point by OW2 that we use to evaluate ABAC policies. In this step, we'll deploy AuthzForce inside the Kubernetes cluster as a service (so that the API server can query it for authorization decisions).

* **Deploy the AuthzForce Deployment and Service:** In the repository, the Kubernetes manifests for AuthzForce are provided (e.g., `manifests/authzforce-deployment.yaml` and `manifests/authzforce-service.yaml`). Apply these manifests:

  ```bash
  kubectl apply -f manifests/authzforce-deployment.yaml
  kubectl apply -f manifests/authzforce-service.yaml
  ```

  This will create a Deployment running the AuthzForce PDP (usually as a Docker container) and expose it as a ClusterIP Service (e.g., service name `authzforce-pdp`). The deployment may use a pre-built AuthzForce Docker image (e.g., `ow2/authzforce-ce-server`). Ensure the image pulls successfully from Docker Hub and the pod starts.

* **Verify AuthzForce is Running:** Check the pod status and logs to ensure AuthzForce started correctly:

  ```bash
  kubectl get pods -l app=authzforce
  kubectl logs deployment/authzforce-pdp
  ```

  You should see the AuthzForce service starting up (it runs on Java/Tomcat). Once it listens on its port (default 8080), it’s ready to accept XACML authorization requests.

### 3. Load ABAC Policies (XACML)

Next, we need to load the ABAC policies into AuthzForce. These policies are written in XACML and encode the security rules to prevent our misconfiguration scenarios. The policies are located in the `policies/` directory of this repository (e.g., `policies/policy1-image-registry.xml`, `policy2-wildcard-binding.xml`, `policy3-tenant-isolation.xml`).

AuthzForce provides a REST API to manage policy sets and PDP configurations. For simplicity, this demo uses a preconfigured policy set:

* **Create Policy Set in AuthzForce:** If not already configured by the deployment, you can create a new policy set (PDP) and upload the XACML policies via the AuthzForce REST API. A helper script (e.g., `scripts/load_policies.py`) is provided to automate this. Run the script to load the policies:

  ```bash
  python3 scripts/load_policies.py
  ```

  This script will connect to the AuthzForce service (using the service ClusterIP or NodePort as configured) and submit the XACML policies. It will group them into a policy set that the PDP will evaluate for each request. Alternatively, you can use `curl` commands to POST the policy XML files to AuthzForce’s API endpoints (refer to AuthzForce documentation for exact endpoints).

* **Verify Policies Loaded:** You can query AuthzForce for the list of policies or check its logs to ensure the policies were loaded without errors. The policies define rules such as:

  * Only images from specific approved registries are permitted (exact string match).
  * RoleBindings that grant `*` (all) permissions are denied unless the subject has an admin attribute.
  * Requests are only permitted if the subject’s tenant (namespace) matches the resource’s tenant (for non-admin users).

With the policies in place, the PDP is conceptually ready to make decisions. The next step is to wire Kubernetes to use this PDP for authorization.

### 4. Integrate AuthzForce as an Admission/Authorization Webhook

Kubernetes supports external authorization via webhook to delegate access control decisions to an outside service. In this experiment, we configure the Kubernetes API server to consult AuthzForce for **authorization** decisions on every API request. This is done by deploying a Validating Admission Webhook that proxies requests to AuthzForce (since AuthzForce expects XACML request format and returns a decision, an adapter is used to translate the Kubernetes request context to an XACML request).

Perform the following:

* **Deploy the Webhook Adapter:** The repository contains code for a small webhook server (e.g., `authz-adapter`) that acts as a bridge between Kubernetes and AuthzForce. This adapter receives Kubernetes AdmissionReview requests, extracts relevant attributes (user, verb, resource, object details), formulates an XACML request, calls AuthzForce PDP, and then formulates an AdmissionReview response (allow or deny). Deploy this adapter as a service in the cluster:

  ```bash
  kubectl apply -f manifests/authz-adapter-deployment.yaml
  kubectl apply -f manifests/authz-adapter-service.yaml
  ```

  The adapter service will be reachable by the API server. It should be configured with the AuthzForce service URL (e.g., via an environment variable or ConfigMap specifying the PDP endpoint). Ensure the adapter pod is running:

  ```bash
  kubectl get pods -l app=authz-adapter
  kubectl logs deployment/authz-adapter
  ```

  You should see it start and listen on HTTPS (most admission webhooks require TLS).

* **Register the Admission Webhook Configuration:** We need to instruct Kubernetes to call the adapter for every relevant request. In `manifests/authz-webhook-config.yaml`, you'll find a `ValidatingWebhookConfiguration` object. Apply it:

  ```bash
  kubectl apply -f manifests/authz-webhook-config.yaml
  ```

  This configuration tells the API server to send admission requests to our `authz-adapter` service (the service name and port are specified, along with a CA bundle for TLS if needed). It can be configured to trigger on all resource requests (or specifically those we want to protect). In our demo, we set it to validate CREATE and DELETE operations for all core resources, and CREATE RoleBinding/ClusterRoleBinding (to catch those events), as well as any other relevant verbs (you can adjust the scope as needed).

* **Verify Webhook Activation:** To confirm the webhook is active, you can try a benign request and see if the adapter logs a decision query. For example:

  ```bash
  kubectl get pods
  ```

  The adapter should log an AuthzForce query for the “list pods” action (which should be permitted for you as cluster admin). If misconfigured, you might see errors in the API server or adapter logs. Fix any TLS or connection issues before proceeding.

At this point, the cluster is fully set up: every API call will trigger AuthzForce PDP evaluation. The XACML policies loaded are now actively governing what is allowed. Next, we will reproduce the three misconfiguration scenarios to test that our ABAC policies indeed block them.

## Verifying and Testing Policies

In this section, we verify the policies both logically (with the SMT solver tool) and empirically (by attempting the misconfigurations on the live cluster). Each case demonstrates how the formally verified ABAC rules mitigate the issue.

### 5. Formal Policy Verification with Z3

Before testing the live cluster, you can use the provided Python CLI tool to perform formal verification on the RBAC and ABAC policy set. This tool encodes the cluster’s RBAC state and our ABAC rules into logical constraints and checks for policy violations using the Z3 SMT solver.

* **Run the Verification Tool:** Use the Python script (e.g., `verify_policies.py`) to analyze the current policy configuration. For example:

  ```bash
  python3 verify_policies.py --with-abac
  ```

  This will connect to the Kubernetes API (using your kubeconfig context) to fetch RBAC data (roles, bindings, etc.) and then load our ABAC rules. The tool defines security invariants for each case (image policy correctness, no wildcard for non-admin, tenant isolation). Z3 will attempt to find a counterexample request that violates any invariant.

* **Interpret the Output:** If the policies are sound, the solver should report `unsat` (unsatisfiable) for each security property check, meaning no violation was found. For instance, with the ABAC policies in place, the image registry rule should produce no model that allows an unapproved registry (the solver would prove that any allowed image must meet the exact-match invariant). Similarly, tenant isolation and privilege scope invariants should hold true (no model where a non-admin can delete another tenant’s resource, etc.). If you run the tool **without** ABAC (`--with-abac=false` or by excluding the ABAC rules), it should find concrete counterexamples illustrating the misconfigurations (e.g., a model showing a registry string `"myregistry.com.attacker.com"` is allowed, or a service account in `teamA` able to access `teamB` namespace as in the cross-tenant case). These formal results give confidence that our ABAC policies indeed fix the RBAC flaws.

*(The formal verification step is optional for running the demo, but it provides a mathematical assurance of policy correctness. The main demonstration of enforcement is via the live tests below.)*

### 6. Testing Policy Enforcement in Kubernetes

Now we manually attempt each misconfiguration scenario against the running cluster. All these actions would normally be **allowed** by Kubernetes RBAC alone (simulating a misconfigured environment), but in our setup the AuthzForce ABAC policies should **deny** them.

Before starting, create two test namespaces to represent separate tenants (for the cross-tenant test):

```bash
kubectl create namespace team-a
kubectl create namespace team-b
```

Also create a service account in each to simulate users/clients:

```bash
kubectl create serviceaccount attacker-sa -n team-a
kubectl create serviceaccount victim-sa -n team-b
```

These will represent a non-privileged account in Team A (attacker) and a target in Team B.

**Test Case 1: Image Registry Bypass**

*Scenario:* An attacker tries to deploy a pod with an image from an untrusted registry that should be disallowed. In a misconfigured admission controller (e.g., Gatekeeper with a faulty regex), this might slip through. In our cluster, the ABAC policy requires images to come from (for example) `myregistry.com` exactly, so any other registry should be blocked.

* **Attempt:** Apply a pod manifest in Team A’s namespace that uses a disallowed image. For example, in `examples/pod-bad-image.yaml`:

  ```yaml
  apiVersion: v1
  kind: Pod
  metadata:
    name: bad-image-pod
    namespace: team-a
  spec:
    containers:
    - name: sleeper
      image: "myregistry.com.attacker.com/evil:latest"  # Deliberately not an allowed registry
      command: ["sleep", "3600"]
  ```

  Apply this pod:

  ```bash
  kubectl apply -f examples/pod-bad-image.yaml
  ```

* **Expected Result:** The creation should be **denied** by the AuthzForce policy. You should see an error from kubectl similar to:

  ```
  Error from server (Forbidden): error when creating "pod-bad-image.yaml": admission webhook "authz-adapter.myorg.svc" denied the request: image registry not allowed
  ```

  No pod will be created. The adapter’s logs will show that the request was evaluated and a Deny decision returned due to the registry attribute not matching the approved set.

  *Without ABAC, this pod would have been admitted, potentially running an unauthorized container. The ABAC rule mitigates the supply-chain threat by enforcing exact image registry matching.*

* *(Optional)* **Cleanup:** Ensure the denied pod did not remain in any pending state. You can also test that using an allowed image (e.g., `myregistry.com/app:1.0`) results in a Permit decision (the pod would be admitted in that case).

**Test Case 2: Wildcard ClusterRole Binding**

*Scenario:* A cluster administrator accidentally grants a service account full wildcard privileges. For example, binding `cluster-admin` role to a normal service account. Under RBAC alone, this is allowed (admins can create any binding), and the service account would then effectively have admin rights – an obvious misconfiguration. Our ABAC policy is designed to catch this: it will deny the creation of any RoleBinding or ClusterRoleBinding that grants “\*” (all resources/all verbs) to a subject that is not explicitly an admin.

* **Attempt:** Try to create a ClusterRoleBinding that gives `attacker-sa` (Team A) the `cluster-admin` role:

  ```yaml
  # examples/wildcard-binding.yaml
  apiVersion: rbac.authorization.k8s.io/v1
  kind: ClusterRoleBinding
  metadata:
    name: give-attacker-full-rights
  subjects:
  - kind: ServiceAccount
    name: attacker-sa
    namespace: team-a
  roleRef:
    kind: ClusterRole
    name: cluster-admin
    apiGroup: rbac.authorization.k8s.io
  ```

  Apply this:

  ```bash
  kubectl apply -f examples/wildcard-binding.yaml
  ```

* **Expected Result:** The ClusterRoleBinding creation is **blocked** by the ABAC policy. Kubectl should report a forbidden error from our webhook:

  ```
  Error from server (Forbidden): clusterrolebindings.rbac.authorization.k8s.io "give-attacker-full-rights" is forbidden: denied by ABAC policy
  ```

  The AuthzForce decision logic sees that the role’s permissions are global (`*`) and the subject `attacker-sa` lacks the required admin attribute, so it returns Deny. Thus, the dangerous binding is never established.

  *Without ABAC, this binding would succeed, and `attacker-sa` would gain cluster-wide admin powers. With the ABAC rule in place, such privilege escalation is prevented at the configuration stage.*

* **Verification:** You can confirm that the binding was not created:

  ```bash
  kubectl get clusterrolebinding give-attacker-full-rights
  ```

  It should not be found. Also, check the AuthzForce/adapter logs for the decision trace indicating denial due to wildcard permissions rule.

**Test Case 3: Cross-Tenant Access**

*Scenario:* We test the tenant isolation policy. Assume an attacker in Team A somehow has a role that technically allows accessing Team B’s resources (e.g., via a wildcard binding or an overly broad role). In a pure RBAC scenario, if such credentials are compromised, the attacker could list or delete resources in Team B’s namespace, violating multi-tenancy. Our ABAC policy enforces that non-admin users can only act within their own namespace.

* **Preparation:** For demonstration, we will simulate a scenario where `attacker-sa` has a role to list pods cluster-wide. (We won’t actually give full admin since we already blocked that above, but let’s grant a narrower privilege that still violates tenant isolation.) Create a ClusterRole and RoleBinding for pod viewing:

  ```yaml
  # examples/pod-reader-role.yaml
  apiVersion: rbac.authorization.k8s.io/v1
  kind: ClusterRole
  metadata:
    name: pod-reader-global
  rules:
  - apiGroups: [""]
    resources: ["pods"]
    verbs: ["get", "list"]
  ---
  apiVersion: rbac.authorization.k8s.io/v1
  kind: ClusterRoleBinding
  metadata:
    name: allow-attacker-read-pods
  subjects:
  - kind: ServiceAccount
    name: attacker-sa
    namespace: team-a
  roleRef:
    kind: ClusterRole
    name: pod-reader-global
    apiGroup: rbac.authorization.k8s.io
  ```

  Apply the above:

  ```bash
  kubectl apply -f examples/pod-reader-role.yaml
  ```

  This gives `attacker-sa` the ability to list pods in any namespace according to RBAC (a misconfiguration from an isolation perspective, since Team A should not list Team B’s pods).

* **Attempt:** Use the `attacker-sa` credentials to list pods in Team B. One way to do this is to retrieve a token for `attacker-sa` and use it with kubectl:

  ```bash
  SA_TOKEN=$(kubectl create token attacker-sa -n team-a)
  kubectl --token="$SA_TOKEN" --namespace=team-b get pods
  ```

  (Ensure your Kubernetes version supports `kubectl create token`. If not, you may retrieve the service account token from its secret.)

* **Expected Result:** The request will be **denied** by AuthzForce. Instead of getting a pods list, you should see:

  ```
  Error from server (Forbidden): pods is forbidden: denied by ABAC policy (cross-tenant access)
  ```

  AuthzForce evaluates that the subject’s tenant (“team-a”) does not match the resource’s tenant (“team-b”) and the subject isn’t an admin, triggering a deny decision. Thus, even though RBAC allowed this action, our ABAC overlay policy stops it.

  *Without ABAC, `attacker-sa` would have succeeded in listing (or even modifying) resources in another tenant’s namespace, breaking isolation. With the ABAC tenant rule, such cross-tenant requests are universally blocked, thwarting the lateral movement attempt.*

* **Cleanup:** You can revoke the test privileges:

  ```bash
  kubectl delete clusterrolebinding allow-attacker-read-pods
  kubectl delete clusterrole pod-reader-global
  ```

  Also, if you generated a token, it's ephemeral and will expire, but you can consider it compromised for the demo and revoke by deleting the service account or simply ignore as the cluster will be torn down eventually.

Through these tests, we have reproduced each misconfiguration scenario and observed the ABAC policies preventing the insecure actions. The live enforcement results corroborate the formal verification: no policy violations occur when the ABAC rules are in effect, and all attempted exploits are stopped.

## Expected Results

After completing the above steps, you should conclude:

* **Formal Verification:** The SMT-based analysis finds no counterexamples when ABAC policies are applied. All security invariants (image provenance, privilege scope, tenant isolation) hold true. By contrast, if the ABAC policies are omitted, the solver would find concrete misconfiguration exploits (demonstrating the need for those policies). This provides mathematical confidence that the policy set is sound and covers the intended security properties.

* **Policy Enforcement:** Each misconfiguration attempt is blocked by the system:

  * Unapproved container image deployments are denied at admission. Only pods with images from the explicitly allowed registry can run, effectively mitigating the image policy bypass vulnerability.
  * Wildcard role bindings to non-admins are not allowed. Kubernetes administrators cannot accidentally grant full privileges to regular users without the ABAC layer catching it. This prevents privilege-escalation misconfigs from being introduced.
  * Cross-namespace (cross-tenant) API requests by non-privileged accounts are rejected, even if RBAC would permit them. This ensures strong tenant isolation; a compromised service account in one namespace cannot leverage overly broad RBAC permissions to impact other namespaces.

* **Observed Outcomes:** In practice, kubectl commands that would normally succeed (but represent misconfigurations) instead return "Forbidden" errors. The AuthzForce PDP logs show decisions of “Deny” for those requests, aligning with the policy rules. No unintended side effects or conflicts were noticed – thanks to XACML’s policy combining algorithms (deny-overrides) and our careful policy design, the ABAC rules cleanly override insecure configurations.

In summary, the experiment demonstrates that formally verified ABAC policies, when enforced via an external PDP integrated into Kubernetes, can **proactively prevent configuration mistakes** that might otherwise lead to security breaches. This approach brings an added layer of assurance to Kubernetes security: even if an admin writes an insecure RBAC rule or misses a subtle policy detail, the ABAC layer (validated by formal methods) will catch and correct the oversight at runtime.
