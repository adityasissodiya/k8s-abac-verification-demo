from graphviz import Digraph

# Initialize a new directed graph for the SMT‐Solver expansion
dot = Digraph('smt_negative_testing', filename='smt_negative_testing_diagram')
dot.attr('graph', rankdir='LR')
dot.attr('node', fontname='Helvetica')
dot.attr('edge', fontname='Helvetica')

# Main SMT‐Solver node (collapsed view)
dot.node(
    'SMT_main',
    label="SMT Solver\n(Verification Engine)",
    shape='ellipse',
    style='filled',
    fillcolor='lightgoldenrod1'
)

# Zoom‐in: place the detailed cluster to the right of the main node
with dot.subgraph(name='cluster_smt_detail') as c:
    c.attr(label="SMT Solver Internals", labelloc='t', style='dashed')
    c.attr(rankdir='TB')  # top‐to‐bottom layout inside the cluster
    
    # Parsing stage
    c.node('Parse', label="Parse(π) → SyntaxTree", shape='box')
    # Model‐construction stage
    c.node('Model', label="Model(SyntaxTree) → Formula", shape='box')
    # SAT check stage
    c.node('SATCheck', label="SATCheck(Formula)", shape='box')
    
    # Outcome nodes, color‐code for clarity
    c.node(
        'Valid', 
        label="Valid", 
        shape='oval', 
        style='filled', 
        fillcolor='palegreen'
    )
    c.node(
        'Invalid', 
        label="Invalid", 
        shape='oval', 
        style='filled', 
        fillcolor='lightcoral'
    )
    c.node(
        'Rejected', 
        label="Rejected", 
        shape='oval', 
        style='filled', 
        fillcolor='lightgrey'
    )
    c.node(
        'Error', 
        label="Error", 
        shape='oval', 
        style='filled', 
        fillcolor='khaki'
    )
    
    # Edges inside the cluster
    c.edge('Parse', 'Model', label="if Parse ↓")
    c.edge('Model', 'SATCheck', label="if Model ↓")
    
    # From SATCheck to Valid/Invalid
    c.edge('SATCheck', 'Valid', label="if formula ⊨ unsat")
    c.edge('SATCheck', 'Invalid', label="if formula ⊨ sat")
    # Malformed → Rejected
    c.edge('Parse', 'Rejected', style='dotted', label="if Parse ↑")
    c.edge('Model', 'Rejected', style='dotted', label="if Model ↑")
    # Unexpected solver failure → Error
    c.edge('SATCheck', 'Error', style='dotted', label="if check ↑ or unknown")

# Connect the main node to its expanded cluster
dot.edge('SMT_main', 'Parse', style='bold', label="detail")

# Render the diagram
dot.render('smt_negative_testing_diagram', format='pdf')
dot.render('smt_negative_testing_diagram', format='svg')
