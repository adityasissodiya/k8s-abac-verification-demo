from graphviz import Digraph

def build_k8s_framework_diagram(output_filename='k8s_framework_deployment'):
    # Create the top-level Digraph
    dot = Digraph(comment='Kubernetes + Formal Verification Framework', format='png')
    dot.attr(rankdir='LR', size='8,5')
    dot.attr('node', shape='box', style='rounded', fontname='Helvetica', fontsize='10')
    dot.attr('graph', splines='ortho')

    # External actors
    dot.node('User', 'End User', shape='oval')
    dot.node('Admin', 'Cluster Admin', shape='oval')
    dot.edge('User', 'API', label='kubectl / API call', minlen='2')
    dot.edge('Admin', 'API', label='kubectl / admin change', style='dashed')

    # Kubernetes Cluster box
    with dot.subgraph(name='cluster_k8s') as k8s:
        k8s.attr(label='Kubernetes Cluster', color='blue', style='dashed')
        # Control Plane
        with k8s.subgraph(name='cluster_control') as cp:
            cp.attr(label='Control Plane', color='black', style='solid', rank='same')
            cp.node('API', 'API Server')
            cp.node('Controller', 'Controller Manager', shape='ellipse')
            cp.node('Scheduler', 'Scheduler', shape='ellipse')
        # Admission Phase
        with k8s.subgraph(name='cluster_webhook') as wh:
            wh.attr(label='Admission Extensions', color='black', style='solid')
            wh.node('Webhook', 'Validating Webhook\n(Policy Enforcement Point)')
        # Worker Nodes placeholder
        with k8s.subgraph(name='cluster_nodes') as wn:
            wn.attr(label='Worker Nodes', color='black', style='solid')
            wn.node('Workload', 'Sample Application Pod', shape='rect')

    # External framework components
    dot.node('Verifier', 'Policy Verification Tool\n(SMT + CLI)', shape='note')
    dot.node('PDP', 'External Policy Engine\n(ABAC PDP)', shape='cylinder')

    # Edges: how components interact
    dot.edge('API', 'Webhook', label='AdmissionReview')
    dot.edge('Webhook', 'PDP', label='authz query')
    dot.edge('PDP', 'Webhook', label='Permit / Deny')
    dot.edge('Verifier', 'PDP', label='deploy verified policies', style='dotted')
    dot.edge('Admin', 'Verifier', label='author & verify policies', style='dotted')

    # Layout hints
    dot.attr('node', width='1.8')
    dot.attr('edge', fontsize='8')

    # Render
    output_path = dot.render(output_filename, cleanup=True)
    return output_path

# Generate and display the diagram
file_path = build_k8s_framework_diagram()
file_path
