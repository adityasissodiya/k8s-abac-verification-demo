from graphviz import Digraph

dot = Digraph(name="RBAC_ABAC_diagram", format="png")
dot.attr('graph', rankdir='LR', nodesep='0.6', ranksep='0.8')
dot.attr('node', fontname='Helvetica')
dot.attr('edge', fontname='Helvetica', fontsize='10')

# User node
dot.node(
    'user',
    label='<<FONT><I>u</I> (User)</FONT>>',
    shape='ellipse',
    style='filled',
    fillcolor='lightgrey'
)

# RBAC cluster: light blue background for RBAC nodes
with dot.subgraph(name='cluster_RBAC') as rb:
    rb.attr(label="RBAC Model", labelloc='t', style='dashed')
    # give the RBAC subgraph a light-blue background
    rb.attr('graph', style='filled', fillcolor='azure1')
    rb.node(
        'role',
        label='<<FONT><I>r</I> (Role)</FONT>>',
        shape='ellipse',
        style='filled',
        fillcolor='lightblue'
    )
    rb.node(
        'perm',
        label='<<FONT><I>p</I> (Permission)</FONT>>',
        shape='ellipse',
        style='filled',
        fillcolor='lightblue'
    )
    rb.node(
        'Perms_RBAC',
        label='<<I>Perms</I><SUB>RBAC</SUB><I>(u) = p | ∃ r: (u,r)∈B ∧ (r,p)∈A</I>>',
        shape='rectangle',
        style='filled',
        fillcolor='lightblue'
    )
    rb.edge('role', 'perm', label='A')

# ABAC cluster: light green background for ABAC nodes
with dot.subgraph(name='cluster_ABAC') as ab:
    ab.attr(label="ABAC Model + Negative Testing", labelloc='t', style='dashed')
    ab.attr('graph', style='filled', fillcolor='honeydew')
    # Verify(π) node for Part VII
    ab.node(
        'Verify',
        label='<<FONT><I>Verify</I>(π)<BR/>(total function)</FONT>>',
        shape='hexagon',
        style='filled',
        fillcolor='palegoldenrod'
    )
    # ABAC decision logic node
    ab.node(
        'ABACAllow',
        label='<<I>π (ABAC decision logic)</I>>',
        shape='rectangle',
        style='filled',
        fillcolor='lightgreen'
    )
    # Security invariant node
    ab.node(
        'phi',
        label='<<FONT><I>φ</I>(u, res, a)</FONT>>',
        shape='ellipse',
        style='filled',
        fillcolor='lightgreen'
    )
    ab.node(
        'Perms_ABAC',
        label='<<I>Perms</I><SUB>ABAC</SUB><I>(u) = (res, a) | ABACAllow(u,res,a)=Permit</I>>',
        shape='rectangle',
        style='filled',
        fillcolor='lightgreen'
    )
    # Edges inside ABAC cluster
    ab.edge('phi', 'ABACAllow',
            style='dashed',
            label='<<FONT>Deny if ¬ </FONT><I>φ</I><FONT> (excluded in </FONT><I>π</I><SUB>bad</SUB><FONT>)</FONT>>')
    ab.edge('Verify', 'ABACAllow', label='only if π well-formed')
    ab.edge('phi', 'Verify', label='invariants ⇒ ')

# Cross-links and delta analysis
dot.edge('user', 'role', label='B')
dot.edge('user', 'Verify', label='User attributes → Verify')
dot.node(
    'Delta',
    label='<<I>Δ(u) = Perms</I><SUB>RBAC</SUB><I>(u) ∖ Perms</I><SUB>ABAC</SUB><I>(u)</I>>',
    shape='rectangle',
    style='filled',
    fillcolor='moccasin'
)
dot.edge('Perms_RBAC', 'Delta', label='RBAC-only privileges',
         color='blue')
dot.edge('Perms_ABAC', 'Delta', label='Revoked by ABAC',
         style='dashed',
         arrowhead='tee',
         color='darkgreen')

# Layout left-to-right
dot.attr(rankdir='LR')

# Render outputs
dot.render('rbac_abac_diagram_updated', format='pdf')
dot.render('rbac_abac_diagram_updated', format='svg')
