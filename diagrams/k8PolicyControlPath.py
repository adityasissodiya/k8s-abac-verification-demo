from graphviz import Digraph

dot = Digraph('control_path', filename='k8s_policy_control_path')
dot.attr('node', fontname='Helvetica'); dot.attr('edge', fontname='Helvetica')

# Nodes for start, decisions, and outcomes
dot.node('start',   "User Request", shape='oval')
dot.node('rbac',    "RBAC Authorizer\npermits request?", shape='diamond')
dot.node('abac',    "ABAC Webhook (PDP)\npermits request?", shape='diamond')
dot.node('allowed', "Request Allowed", shape='oval')
dot.node('denied',  "Request Denied", shape='oval')

# Decision flow with labeled branches
dot.edge('start', 'rbac')
dot.edge('rbac', 'abac',  label="Permit")  # if RBAC allows, go to ABAC
dot.edge('rbac', 'denied', label="Deny")   # if RBAC denies, request denied
dot.edge('abac', 'allowed', label="Permit")  # if ABAC allows, request allowed
dot.edge('abac', 'denied',  label="Deny")    # if ABAC denies, request denied

dot.attr(rankdir='TB')

# Render to PDF and SVG
dot.render('k8s_control_path.pdf', format='pdf')
dot.render('k8s_control_path.svg', format='svg')
