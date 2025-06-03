# Securing Kubernetes with Formalized ABAC – End-to-End Prototype
This repository contains the code and configuration for the prototype described in the research paper **"Securing Kubernetes with Formalized Attribute-Based Access Control"**. It demonstrates how to formally verify Kubernetes access control policies using an SMT solver and enforce them at runtime using an external Attribute-Based Access Control (ABAC) engine.

## Overview
This repository demonstrates a Kubernetes security experiment using **formally verified Attribute-Based Access Control (ABAC)** policies to mitigate synthetic Role-Based Access Control (RBAC) misconfigurations. The goal is to show that by integrating an external ABAC Policy Decision Point (PDP) (AuthzForce) with formally verified XACML policies, we can prevent specific classes of configuration flaws that are otherwise possible under Kubernetes RBAC. The demo sets up a local Kubernetes cluster (via Minikube on Docker) and enforces custom XACML policies through an AuthzForce PDP service and an admission webhook. We illustrate three misconfiguration case studies inspired by known Kubernetes security issues:

* **Image Registry Bypass:** A misconfiguration in admission policies could allow deployment of container images from disallowed registries (e.g., a missing URL slash allowed `myregistry.com.attacker.com` to bypass an “allowed registries” rule). Our ABAC policy enforces an exact match on approved image registries, preventing such bypasses.
* **Wildcard Privilege Binding:** A role binding that grants wildcard (`*`) permissions cluster-wide to a non-admin principal. This simulates an overly broad ClusterRoleBinding where a service account gains full privileges. The ABAC policy adds an attribute constraint that denies binding global `*` permissions to any subject that is not an administrator.
* **Cross-Tenant Access:** A tenant isolation failure where a service account from one namespace can access or modify resources in another namespace (cross-namespace escalation). This can occur if a wildcard privilege is granted unintentionally. The ABAC policy ensures that if the requesting user's tenant (namespace) does not match the target resource's tenant, the request is denied (except for designated admins).

By blending Kubernetes RBAC with external ABAC, the demo provides **formally verified security guarantees**. The XACML policies are mathematically checked using an SMT solver (Z3) to ensure they uphold intended invariants (e.g., *“no non-admin can access another team’s namespace”*) with no policy conflicts. We use a Python CLI tool to encode the RBAC rules and ABAC policies into logical constraints and automatically find policy violations or prove the policies safe. The AuthzForce PDP is then deployed in-cluster and consulted on each API request (via an admission webhook) to enforce the verified policies in real time. This README will guide you through reproducing the experiment step-by-step, verifying the policies, and observing how the system blocks each misconfiguration scenario.

**Key takeaway:** Formally verified ABAC policies (in XACML), when enforced in Kubernetes through an external PDP (AuthzForce) and webhook integration, can systematically close security gaps left by misconfigured RBAC policies. This demo is for research and educational purposes; it uses a local Minikube setup and synthetic scenarios (no real production cluster deployment is involved).

## Architecture & Components

The prototype consists of two main parts: an **offline formal verification tool** and a **runtime enforcement mechanism**. Below is a brief architecture overview and description of key components in the repository:

* **Policy Verification CLI (Python + Z3)** – Located in the `cli/` directory. This is a Python command-line tool (see `cli/verify_policies.py`) that uses the Z3 SMT solver to analyze Kubernetes RBAC policies and additional ABAC rules. It models the cluster’s roles, role bindings, and ABAC conditions as logical formulas and checks for any policy violations (counterexamples) to the desired security properties. The CLI uses example policy files in `cli/fixtures/` (described below) to simulate misconfigurations and their fixes.

* **Robust error handling** – The CLI rejects any malformed or incomplete policy file with a clear error message. If a policy is well-formed but fails verification, it is flagged as invalid, with a counterexample provided to illustrate the violation.

* **Misconfiguration Case Studies (RBAC/ABAC Examples)** – Under `cli/fixtures/`, three pairs of YAML files encode the case studies:

  * *Image Registry Bypass:* `bad-registry-policy.yaml` defines an insecure admission policy (e.g., a regex that could be bypassed) and RBAC context; `fixed-registry-policy.yaml` provides the corrected policy. This case simulates a supply-chain security rule that is too lax.
  * *Wildcard ClusterRole Binding (Shadow Admin):* `bad-rolebinding-policy.yaml` represents a scenario where a service account is accidentally granted wildcard admin privileges (privilege escalation); `fixed-rolebinding-policy.yaml` adds constraints or changes to fix this.
  * *Cross-Tenant Access Breach:* `bad-tenant-policy.yaml` models a situation where a service account in one namespace can access another namespace’s resources (due to overly broad permissions); `fixed-tenant-policy.yaml` includes an ABAC condition to enforce strict tenant isolation.

  These YAML files define RBAC roles/bindings and (in the fixed versions) incorporate ABAC rules as annotations. The CLI tool loads these files to verify that the **bad** policies indeed allow a violation (Z3 finds a counterexample), and that the **fixed** policies satisfy the security invariants (no counterexample exists).

* **XACML ABAC Policies** – Located in the `runtime/policies/` directory as XML files (e.g., `image-registry-policy.xml`, `wildcard-rolebinding-policy.xml`, `tenant-isolation-policy.xml`). These are ABAC policies written in the standard XACML 3.0 format. They encode the same rules as the fixed policy scenarios above, but in a form that the AuthzForce PDP can evaluate at runtime. Each policy corresponds to one case study and is designed to **deny** requests that violate the intended security condition (e.g., deny pods from unapproved registries, deny wildcard role bindings for non-admins, deny cross-namespace resource access). The CLI’s formal verification covers these as well (to prove that with these rules in place, no insecure scenario is possible).

* **AuthzForce PDP (Policy Decision Point)** – An open-source XACML engine by OW2, used as an external authorization service. In this prototype, AuthzForce is deployed in the Kubernetes cluster (see `runtime/manifests/authzforce-pdp-deployment.yaml` and `authzforce-pdp-service.yaml`). The PDP is loaded with the XACML policies mentioned above. At runtime, when a request comes to the Kubernetes API server, the server delegates the authorization decision to this PDP (via the adapter below). AuthzForce evaluates the request’s attributes against the policies and returns `Permit` or `Deny`. By running the PDP inside Minikube, we avoid any external dependencies — all decisions are made locally within the cluster.

* **Admission Webhook (AuthzForce Adapter)** – A **Validating Admission Webhook** service that integrates Kubernetes with the AuthzForce PDP. This component (deployed via `runtime/manifests/authz-adapter-deployment.yaml` and a corresponding Service and Webhook Configuration) acts as a bridge: it receives API access requests from the Kubernetes API server (as AdmissionReview objects), translates them into XACML authorization requests (extracting attributes like the user, action, resource, etc.), calls the AuthzForce PDP’s API, and then returns an allow/deny response back to Kubernetes. The webhook is configured to intercept create and delete operations (and others as needed) cluster-wide, so it effectively applies our ABAC policies on top of Kubernetes’s own RBAC. The repository includes the necessary Kubernetes manifests to set up this adapter and a self-signed certificate for secure communication (the files `runtime/server.crt`, `server.key`, etc., are used to configure TLS for the webhook).

All these components work together as follows: **Before deployment**, you use the CLI tool to formally verify that the RBAC+ABAC policy combination has no weaknesses. **At runtime**, the Kubernetes API server calls the external webhook (adapter) for every request; the adapter consults AuthzForce PDP which enforces the verified XACML policies; and only safe requests are permitted. Next, we provide instructions to set up each part on a local Minikube cluster and reproduce the experiment.

## Prerequisites and Installation

Before proceeding, ensure you have the following installed on your machine (the demo was developed on Ubuntu Linux, but it should work similarly on other systems):

* **Docker:** Docker Engine is required for running Minikube (using the Docker driver) and for pulling container images. Install Docker CE from the official docs or via your package manager. Make sure the Docker daemon is running and you have permission to use it (e.g., add your user to the `docker` group on Linux).
* **Minikube:** Minikube will run the local Kubernetes cluster. Install the latest Minikube (v1.29+ recommended) by following the [official Minikube installation guide](https://minikube.sigs.k8s.io/docs/start/). Ensure Minikube is configured to use the Docker driver on your platform (on Linux, it defaults to Docker if available).
* **kubectl:** Kubernetes command-line tool to interact with the cluster. Install kubectl (e.g., `sudo apt install -y kubectl` on Ubuntu, or download the binary) with a version compatible with your Minikube Kubernetes version (Minikube typically uses a recent stable release).
* **Python 3:** Required for the policy verification CLI tool. Python 3.8+ is recommended. Make sure you can install Python packages with pip.
* **Z3 SMT Solver:** The verification tool depends on the Z3 solver. Install the Z3 Python bindings via pip: `pip install z3-solver`. (If using the provided virtual environment or requirements file, this will be handled there.)

## Step-by-Step Setup Guide

Follow these steps to launch the local Kubernetes cluster, deploy the AuthzForce PDP with ABAC policies, and configure the Kubernetes admission webhook. After setup, you will run the verification CLI and test the enforcement of policies. **All steps are done locally on Minikube**.

### 1. Launch Minikube Kubernetes Cluster

First, start a Minikube cluster on your local machine:

```bash
minikube start --driver=docker --memory=4096 --cpus=2
```

This command initializes a single-node Kubernetes cluster locally using the Docker driver, allocating 4 GB of RAM and 2 CPU cores. If successful, Minikube will start the Kubernetes control plane and node. Verify that the cluster is running and that `kubectl` is configured to talk to it:

```bash
kubectl get nodes
```

You should see the Minikube node in a `Ready` state. At this point, you have a functional Kubernetes cluster to work with.

### 2. Deploy AuthzForce PDP as a Service

AuthzForce is an open-source XACML 3.0 Policy Decision Point that we use to evaluate ABAC policies. In this step, we deploy AuthzForce inside the Kubernetes cluster as a service so that the API server (via our adapter) can query it for authorization decisions.

**Deploy the AuthzForce Deployment and Service:** Kubernetes manifests for AuthzForce are provided in the `runtime/manifests` directory (e.g., `authzforce-pdp-deployment.yaml` and `authzforce-pdp-service.yaml`). Apply these manifests to create the AuthzForce deployment and service:

```bash
kubectl apply -f runtime/manifests/authzforce-pdp-deployment.yaml
kubectl apply -f runtime/manifests/authzforce-pdp-service.yaml
```

This will launch a Deployment running the AuthzForce PDP (using a Docker image, such as `ow2/authzforce-ce-server` from Docker Hub) and expose it as a Service within the cluster (service name might be `authzforce-pdp`). The Deployment will create a pod running AuthzForce (which is a Java/Tomcat-based server).

**Verify AuthzForce is Running:** Check the pod status and logs to ensure AuthzForce started correctly:

```bash
kubectl get pods -l app=authzforce
kubectl logs deployment/authzforce-pdp
```

You should see the AuthzForce pod and that it’s in `Running` state. Inspecting the logs, you should notice AuthzForce initializing (it may take a bit as it starts the web server). Once it listens on its port (default 8080 inside the container), it’s ready to accept XACML authorization requests.

### 3. Load ABAC Policies into AuthzForce

Next, we need to load our ABAC security policies into the AuthzForce PDP. These policies (XACML files in `runtime/policies/`) encode the rules to prevent our misconfiguration scenarios. For example, they specify that images must come from allowed registries, that wildcard role bindings are not allowed for non-admins, and that cross-namespace access is forbidden for regular users.

AuthzForce provides a REST API to manage policies and PDP configurations. For simplicity, this demo uses a default single PDP configuration and we load our policies into it.

**Upload the XACML Policies:** If the AuthzForce deployment is configured with an empty policy set, we will add our policies via the REST API. You can do this using a provided script `scripts/load_policies.py`:

```bash
python3 scripts/load_policies.py
```

```bash
# Make sure this file is executable:
chmod +x scripts/load_policies.py

# From the repo root, run:
./scripts/load_policies.py

# Or specify custom paths/names:
./scripts/load_policies.py \
  --namespace authzforce \
  --configmap authzforce-policies \
  --deployment authzforce-pdp \
  --policies-dir runtime/policies
```

This will:

1. Delete any existing `authzforce-policies` ConfigMap (to avoid stale entries).
2. Create a new ConfigMap containing **all** `.xml` files under `runtime/policies/`.
3. Trigger a rolling restart of the `authzforce-pdp` Deployment so that the PDP pod re-mounts the updated ConfigMap at `/policies`.

After running, give the PDP a minute to restart:

```bash
kubectl -n authzforce rollout status deployment/authzforce-pdp
```

Then you can re-test your webhook or direct PDP queries to confirm that the new policies are active.

**Verify Policies Loaded:** After loading, you can query AuthzForce for the list of policies or check its logs to confirm the policies were accepted. AuthzForce will now enforce rules such as:

* Only images from a specific approved registry (e.g., exactly `"myregistry.com"`) are permitted.
* Any RoleBinding/ClusterRoleBinding that grants all (`*`) permissions is denied unless the subject is an admin.
* Requests are permitted only if the requesting user’s namespace (tenant) matches the resource’s namespace, except for cluster-admins.

With the XACML policies in place, the PDP is ready to make authorization decisions according to our rules. Now we will configure Kubernetes to use this PDP for every API request.

### 4. Integrate AuthzForce via an Admission Webhook

Kubernetes can delegate authorization decisions to an external service using admission webhooks. In our setup, we deploy a **Validating Admission Webhook** that intercepts every relevant API call and forwards it to AuthzForce for a decision. This webhook is essentially our *authz-adapter*.

**Deploy the Webhook Adapter:** Apply the manifest for the adapter deployment and service (e.g., `runtime/manifests/authz-adapter-deployment.yaml` and `authz-adapter-service.yaml`):

```bash
kubectl apply -f runtime/manifests/authz-adapter-deployment.yaml
kubectl apply -f runtime/manifests/authz-adapter-service.yaml
```

This will create a deployment (pod) for the adapter and a service to expose it internally. The adapter service should be accessible at a URL (within the cluster) that the Kubernetes API server can call. The adapter is configured (via environment variables or ConfigMap) with AuthzForce’s endpoint (the service from step 2) and uses the certificate keys provided in `runtime/` to serve HTTPS (required for webhooks).

After deploying, verify the adapter is running:

```bash
kubectl get pods -l app=authz-adapter
kubectl logs deployment/authz-adapter
```

In the logs, you should see the adapter initializing and listening (likely on port 443 within the container). If it starts successfully, it is ready to receive admission review requests.

**Register the Webhook Configuration:** Now we tell Kubernetes to actually use the adapter for admissions. Apply the `ValidatingWebhookConfiguration` manifest (e.g., `runtime/manifests/authz-webhook-config.yaml`):

```bash
kubectl apply -f runtime/manifests/authz-webhook-config.yaml
```

This configuration object instructs the Kubernetes API server to send admission requests to our adapter’s endpoint. It includes the service name, port, and the CA bundle for the adapter’s TLS certificate so the API server can verify it. The configuration can target specific resource types and API operations. In our demo, it’s set to validate (at least) all create and delete operations for core resources, as well as RoleBinding/ClusterRoleBinding creations. This ensures our critical scenarios (image deployments, binding creations, cross-namespace access via resource creation) will all trigger the external check.

**Verify Webhook is Active:** To confirm everything is wired up, try a harmless API call and see if the adapter logs a query. For example:

```bash
kubectl get pods
```

This is a read operation (which our webhook might also intercept depending on configuration). If intercepted, the adapter logs should show an AuthzForce query for listing pods. Even if reads are not hooked, try creating a dummy resource that should obviously be allowed (like a new namespace or a configmap in your current namespace). If the webhook is working, either the creation will succeed (and the adapter will log a Permit decision), or if misconfigured, the API call might hang or error (in which case check the API server logs and adapter logs for any TLS or connection issues). Resolve any issues before proceeding.

At this point, **the cluster is fully set up**: every relevant API call will trigger an AuthzForce PDP authorization decision via the admission webhook. Our formally verified XACML policies are now actively governing cluster behavior. Now it’s time to see the system in action by reproducing the misconfiguration scenarios and verifying that they are blocked as expected.

## Verifying and Testing the Policies

We will use two approaches to validate that the security policies work as intended: (1) **Formal verification using the SMT solver (Z3)** on the model of our policies, and (2) **Empirical testing on the live cluster** by attempting the misconfigurations.

### 5. Formal Policy Verification with Z3 (CLI Tool)

Before making any changes to the live cluster, it’s useful to run the formal verification to ensure our policies are theoretically sound. The Python CLI tool in `cli/verify_policies.py` can be run to analyze the RBAC+ABAC policy set and check for potential violations of the security invariants.

**Run the Verification Tool:** Make sure you have Python and Z3 installed (or activate the provided virtual environment if one is included in the repo). Then run:

```bash
cd cli/
python3 verify_policies.py --with-abac
```

This will load the **fixed** policy files (or optionally fetch the live cluster’s RBAC if the script is designed to do so) and the ABAC rules, then encode the security invariants for each case study. For example, it will encode conditions like *"no pod image registry other than `myregistry.com` is allowed"*, *"no non-admin can have `*` privileges"*, *"no service account can access another namespace's resources"* and so on. The Z3 solver will then attempt to find a model (a set of variable assignments representing a request and roles) that violates any of these invariants.

**Interpret the Output:** If all policies are correct, Z3 should report each check as **unsatisfiable (`unsat`)**, meaning no counterexample was found for that property. This indicates our policies successfully block that misconfiguration. For instance, with the ABAC rules in place, the solver should not find any image name that bypasses the registry rule, nor any scenario where a non-admin gains admin rights or cross-tenant access. If the tool is run on the **bad** policies (for example, running `verify_policies.py` on the `bad-*.yaml` files or with a flag to disable the ABAC rules), Z3 **will find** counterexamples. It might output models showing, for example, a disallowed image name that would be accepted, or a specific service account and action that breaks tenant isolation. Those are essentially the attacks that our ABAC policies prevent. The CLI will typically print either the model (for violations) or a message that no issues were found.

*(Running the formal verification is optional but recommended to understand the guarantees. You may skip it if you trust the setup and proceed to live tests.)*

### 6. Testing Policy Enforcement in Kubernetes

Now for the real test: we try to perform the misconfigurations on the live cluster and see if the system denies them. We will go through each of the three scenarios step by step. Remember, without our ABAC layer, these actions would normally succeed on a misconfigured cluster. With our ABAC policies enforced by AuthzForce, they should be blocked.

**Setup for Testing:** First, let’s create two namespaces to represent two different tenants (for the cross-tenant scenario):

```bash
kubectl create namespace team-a
kubectl create namespace team-b
```

Also create a service account in each namespace, to use as identities in the tests:

```bash
kubectl create serviceaccount attacker-sa -n team-a
kubectl create serviceaccount victim-sa -n team-b
```

These will represent a normal user in Team A (potential attacker) and a target in Team B. We will use `attacker-sa`'s credentials to simulate malicious actions.

**Test Case 1: Image Registry Bypass**

* **Scenario:** An attacker tries to deploy a Pod with a container image from an untrusted registry which is supposed to be disallowed by policy. In real incidents, subtle misconfigurations (like a flawed regex in an admission controller) have allowed such images. Our ABAC policy should catch this by requiring an exact match on the allowed image registry.

* **Attempt the Attack:** We have a pod spec (see `examples/pod-bad-image.yaml`) that uses a disallowed image name. For example:

  ```yaml
  apiVersion: v1
  kind: Pod
  metadata:
    name: bad-image-pod
    namespace: team-a
  spec:
    containers:
      - name: sleeper
        image: "myregistry.com.attacker.com/evil:latest"  # Not an allowed registry (looks similar to allowed one)
        command: ["sleep", "3600"]
  ```

  Try to create this pod:

  ```bash
  kubectl apply -f examples/pod-bad-image.yaml
  ```

* **Expected Result:** The pod creation should be **denied** by our admission webhook. You should see an error from `kubectl` like:

  ```
  Error from server (Forbidden): error when creating "pod-bad-image.yaml": admission webhook "authz-adapter.default.svc" denied the request: image registry not allowed
  ```

  (The exact message might vary, but it will indicate the request was forbidden by the webhook/ABAC policy.) No pod will be created in `team-a`.

  Check the adapter’s logs – it should show that it received the create request for `bad-image-pod`, translated it to an XACML request (with an attribute for image name), and that AuthzForce returned a Deny decision due to the image registry rule.

  *Without our ABAC layer*, this pod would have been admitted by Kubernetes (assuming `attacker-sa` had rights to create pods in that namespace), potentially running an unauthorized image. With the ABAC policy, the attempt is blocked, mitigating the supply-chain risk.

* *(Optional)* If you want, you can also test a pod with an **allowed** image (e.g., `myregistry.com/legit-app:1.0`) in the same namespace. That should be permitted (to verify that it's not blocking everything, just the disallowed cases). Remember to clean up any test pod if created.

**Test Case 2: Wildcard ClusterRole Binding**

* **Scenario:** A cluster admin (by mistake or maliciously) grants a service account full cluster-admin privileges via a ClusterRoleBinding. Under pure RBAC, this is allowed and would instantly escalate `attacker-sa` to have **cluster-admin** rights. Our ABAC policy is intended to prevent such wildcard privilege grants to non-admins.

* **Attempt the Attack:** We have a manifest (e.g., `examples/wildcard-binding.yaml`) that binds `cluster-admin` role to `attacker-sa`:

  ```yaml
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

  Apply this manifest:

  ```bash
  kubectl apply -f examples/wildcard-binding.yaml
  ```

* **Expected Result:** The creation of this ClusterRoleBinding should be **blocked** by the webhook. Kubectl should report something like:

  ```
  Error from server (Forbidden): clusterrolebindings.rbac.authorization.k8s.io "give-attacker-full-rights" is forbidden: request denied by ABAC policy
  ```

  The AuthzForce policy sees that a role with wildcard/all permissions (`cluster-admin` essentially allows `*` on everything) is being granted to a normal service account. Since `attacker-sa` does not have the special admin attribute in our ABAC model, the policy denies the request. Thus, the binding is not created.

  You can verify it was never created:

  ```bash
  kubectl get clusterrolebinding give-attacker-full-rights
  ```

  It should say not found.

  *Without ABAC*, this dangerous binding would have succeeded, and `attacker-sa` would now effectively own the cluster. Our ABAC rule averts this misconfiguration by adding an extra check beyond RBAC.

* **Note:** In a real cluster, only a cluster admin can create such a binding in the first place. Our scenario assumes an admin made a mistake. The ABAC layer acts as a safety net even for cluster admins' actions.

**Test Case 3: Cross-Tenant Access**

* **Scenario:** This tests the tenant isolation policy. Suppose an admin unintentionally gave a role too broad of a scope (e.g., allowed reading resources cluster-wide). If `attacker-sa` gets hold of such credentials, it could access another tenant's resources (here, Team B's namespace). Our ABAC policy says a service account can only access its own namespace (unless it's an admin overriding that).

* **Setup the Misconfiguration:** To simulate, let's deliberately give `attacker-sa` a cluster-wide read access on pods (which is something you might do if mis-scoping a role). Create a role and binding for this:

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

  Apply this:

  ```bash
  kubectl apply -f examples/pod-reader-role.yaml
  ```

  Now `attacker-sa` has RBAC permission to list pods in any namespace (which is a misconfiguration in a multi-tenant cluster context).

* **Attempt the Attack:** Try to list pods in Team B’s namespace using `attacker-sa`’s credentials. One easy way is to obtain a token for `attacker-sa` and use it with kubectl:

  ```bash
  SA_TOKEN=$(kubectl create token attacker-sa -n team-a) 
  kubectl --token="$SA_TOKEN" -n team-b get pods
  ```

  This runs `kubectl get pods` in namespace team-b, authenticating as `attacker-sa`.

* **Expected Result:** The request should be **denied** by our webhook. Instead of a list of pods (or an empty list if none), you should see:

  ```
  Error from server (Forbidden): pods is forbidden: denied by ABAC policy (cross-tenant access)
  ```

  This means AuthzForce recognized that `attacker-sa` (tenant "team-a") was trying to access a resource in "team-b", and since `attacker-sa` is not an admin, the XACML policy denied the request. The Kubernetes API server therefore refuses to return the pods.

  This demonstrates that even though RBAC allowed the action (we intentionally gave that right), our ABAC overlay intercepted and blocked it, preserving tenant isolation.

* **Cleanup:** Remove the test role and binding to avoid lingering broad permissions:

  ```bash
  kubectl delete clusterrolebinding allow-attacker-read-pods
  kubectl delete clusterrole pod-reader-global
  ```

  Also, note that the token created for `attacker-sa` will eventually expire. No further action is needed for it, but you could delete `attacker-sa` if you’re done.

Across all these test cases, you should observe that **insecure configurations/requests are denied** by the system. This is exactly what we intended by adding the formally verified ABAC layer.

## Expected Results

By the end of the experiment, you should have seen the following outcomes:

* **Formal Verification (CLI)**: The SMT solver (Z3) found no counterexamples when the ABAC policies were included, indicating our security invariants hold. For comparison, without the ABAC rules, the solver was able to pinpoint specific policy violations in each of the three scenarios, underscoring the necessity of those rules. This gives confidence that the policy set is logically sound.

* **Runtime Enforcement (AuthzForce + Webhook)**: Each attempted misconfiguration was blocked:

  * Pods with unapproved image registries were not admitted (the webhook denied them). Only pods from the allowed registry succeed, effectively enforcing a strict image provenance policy.
  * Wildcard privilege escalation (ClusterRoleBinding to cluster-admin for a non-admin) was prevented. The ABAC policy acted as a safety net to stop an admin’s mistake from escalating privileges.
  * Cross-namespace operations by an account were denied, maintaining strong tenant isolation. Even though RBAC mistakenly permitted broad access, the ABAC check overrode it to protect other namespaces.

* **Observed Behavior:** In practice, `kubectl` commands that would normally succeed (if the cluster were misconfigured) instead returned **"Forbidden"** errors. The error messages and logs explicitly mention our admission webhook or ABAC policy, making it clear that the external PDP enforcement kicked in. AuthzForce’s logs (if accessed) would show decision evaluations, and the adapter’s logs show the translation of Kubernetes requests to XACML requests. There were no false positives in our tests — legitimate actions (like using correct images or accessing one’s own namespace) were allowed, demonstrating that the ABAC policies were specific and did not disrupt normal operations.

In summary, this repository’s prototype shows that **combining formal verification with runtime enforcement can significantly harden Kubernetes security**. By catching policy misconfigurations through mathematical analysis and then enforcing robust ABAC rules via an external PDP, we can prevent a range of potential attacks caused by human error in RBAC policies. Feel free to modify the scenarios or policies to further experiment, and refer to the research paper for a deeper discussion of the approach and its implications. Happy experimenting with secure Kubernetes policies!
