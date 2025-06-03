from graphviz import Digraph

# Initialize directed graph for architecture
dot = Digraph('framework_arch', filename='framework_architecture')
dot.attr('node', fontname="Helvetica"); dot.attr('edge', fontname="Helvetica")

# Cluster: Kubernetes components inside the cluster
with dot.subgraph(name='cluster_k8s') as c:
    c.attr(label="Kubernetes Cluster", style='dashed')
    c.node('API', label="API Server\n(RBAC Authorizer)")
    c.node('Adapter', label="ABAC Adapter\n(Webhook)")
    c.attr(rank='same')  # place API and Adapter at same rank (side by side)

# External components
dot.node('PDP', label="AuthzForce PDP\n(XACML Policy Decision Point)")
# Highlighted SMT Solver node
dot.node(
    'SMT',
    label="SMT Solver\n(Verification Engine)",
    shape='ellipse',
    style='filled',
    fillcolor='lightgoldenrod1'  # light yellow highlight
)


# Represent user/admin initiating requests
dot.node('User', label="User/Admin\n(kubectl client)", shape='none')

# Policy sources (as notes for illustration)
dot.node('RBACpol', label="RBAC Policy (YAML)", shape='note')
dot.node('ABACpol', label="ABAC Policy (XACML/ALFA)", shape='note')
dot.node('Invariant', label="Security invariants", shape='note')

# Runtime request flow (solid arrows)
dot.edge('User', 'API', label="API request")
dot.edge('API', 'Adapter', label="AuthZ webhook call")
dot.edge('Adapter', 'PDP', label="XACML query")
dot.edge('PDP', 'Adapter', label="Permit/Deny decision")
dot.edge('Adapter', 'API', label="AuthZ response")
dot.edge('API', 'User', label="Response allowed/denied")

# Policy distribution (dashed arrows)
dot.edge('RBACpol', 'API', style='dashed')    # RBAC config loaded into API server
dot.edge('ABACpol', 'PDP', style='dashed')    # ABAC policies loaded into PDP
dot.edge('RBACpol', 'SMT', style='dashed')    # RBAC rules fed into verifier
dot.edge('ABACpol', 'SMT', style='dashed')    # ABAC rules fed into verifier
dot.edge('Invariant', 'SMT', style='dashed')  # invariants provided to verifier

# Lay out left-to-right for clarity
dot.attr(rankdir='LR')

# Render to PDF and SVG
dot.render('framework_architecture.pdf', format='pdf')
dot.render('framework_architecture.svg', format='svg')
