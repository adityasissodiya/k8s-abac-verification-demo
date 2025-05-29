from graphviz import Digraph

# ─────────────────────────────
# Logical view diagram
# ─────────────────────────────
logical = Digraph("LogicalView", node_attr={'shape': 'box'})

# Nodes
logical.node('Admin', "Policy Admin (writes policies)", shape='oval')
logical.node('CLI',   "Policy CLI & Encoder Tool")
logical.node('SMT',   "SMT Solver (Verifier)")
logical.node('Repo',  "Verified Policy Repository", shape='cylinder')
logical.node('PDP',   "Policy Decision Point (PDP)")
logical.node('API',   "Kubernetes API Server")
logical.node('PEP',   "Admission Webhook (PEP)")
logical.node('User',  "End User / K8s Client",        shape='oval')

# Design-time subgraph
with logical.subgraph(name='cluster_design') as c:
    c.attr(label="Design-Time (Verification)", color="blue", style="dashed")
    for n in ['Admin', 'CLI', 'SMT', 'Repo']:
        c.node(n)

# Runtime subgraph
with logical.subgraph(name='cluster_runtime') as c:
    c.attr(label="Runtime (Enforcement)", color="green", style="dashed")
    for n in ['API', 'PEP', 'PDP', 'User']:
        c.node(n)

# Edges
logical.edge('Admin',  'CLI',   label="writes policies")
logical.edge('CLI',    'SMT',   label="checks invariants")
logical.edge('CLI',    'Repo',  label="stores verified policies")
logical.edge('Repo',   'PDP',   label="deploys to PDP")
logical.edge('User',   'API',   label="API request")
logical.edge('API',    'PEP',   label="AdmissionReview")
logical.edge('PEP',    'PDP',   label="authz query")
logical.edge('PDP',    'PEP',   label="decision")
logical.edge('PEP',    'API',   label="allow / reject")

logical.format = 'png'
logical.render('logical_view', cleanup=True)

# ─────────────────────────────
# Physical view diagram
# ─────────────────────────────
physical = Digraph("PhysicalView", node_attr={'shape': 'box'})
physical.attr(label="Kubernetes Cluster (Production)", color="blue", style="dashed")

# Control-plane subgraph
with physical.subgraph(name='cluster_master') as cm:
    cm.attr(label="Master Node (Control Plane)", color="gray", style="dotted")
    cm.node('APIServer', "API Server")
    cm.node('Webhook',   "AuthZ Webhook (PEP)", shape='ellipse')

# Worker subgraph
with physical.subgraph(name='cluster_worker') as cw:
    cw.attr(label="Worker Node", color="gray", style="dotted")
    cw.node('Pod', "Example Workload Pod")

# External actors
physical.node('PDPService', "External PDP Service")
physical.node('AdminPC',    "Policy Dev Machine", shape='oval')
physical.node('Client',     "User Client",        shape='oval')

# Edges
physical.edge('Client',     'APIServer',   label="K8s API call")
physical.edge('APIServer',  'Webhook',     label="validate via webhook")
physical.edge('Webhook',    'PDPService',  label="authz query")
physical.edge('PDPService', 'Webhook',     label="decision reply")
physical.edge('Webhook',    'APIServer',   label="admission response")
physical.edge('APIServer',  'Pod',         label="deploy workload", style="dashed")
physical.edge('AdminPC',    'PDPService',  label="push verified policies")

physical.format = 'png'
physical.render('physical_view', cleanup=True)
