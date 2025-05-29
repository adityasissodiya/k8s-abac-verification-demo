from graphviz import Digraph

dot = Digraph(name="RBAC_ABAC_diagram", format="png")
dot.attr('graph', rankdir='LR')                        # Left-to-right layout
dot.attr('node', fontname='Helvetica')
dot.attr('edge', fontname='Helvetica', fontsize='10')

# User node
dot.node('user', label='<<FONT><I>u</I> (User)</FONT>>', shape='ellipse')

# RBAC cluster with roles, permissions, and Perms_RBAC
with dot.subgraph(name='cluster_RBAC') as rb:
    rb.attr(label="RBAC Model", labelloc='t', style='dashed')
    rb.node('role', label='<<FONT><I>r</I> (Role)</FONT>>', shape='ellipse')
    rb.node('perm', label='<<FONT><I>p</I> (Permission)</FONT>>', shape='ellipse')
    rb.node('Perms_RBAC', 
            label='<<I>Perms</I><SUB>RBAC</SUB><I>(u) = p | ∃ r: (u,r)∈B ∧ (r,p)∈A</I>>', 
            shape='rectangle')
    rb.edge('role', 'perm', label='A')                 # Role-to-Permission assignment

# ABAC cluster with policy π, invariant φ, and Perms_ABAC
with dot.subgraph(name='cluster_ABAC') as ab:
    ab.attr(label="ABAC Model", labelloc='t', style='dashed')
    ab.node('ABACAllow', label='<<I>π (ABAC decision logic)</I>>', shape='rectangle')
    ab.node('phi', label='<<FONT><I>φ</I>(u, res, a)</FONT>>', shape='ellipse')
    ab.node('Perms_ABAC', 
            label='<<I>Perms</I><SUB>ABAC</SUB><I>(u) = (res, a) | ABACAllow(u,res,a)=Permit</I>>', 
            shape='rectangle')
    # Invariant enforcement: "Deny if not φ" (excluded in π_bad if misconfigured)
    ab.edge('phi', 'ABACAllow', style='dashed',
            label='<<FONT>Deny if ¬ </FONT><I>φ</I>'
                  '<FONT> (excluded in </FONT><I>π</I><SUB>bad</SUB><FONT>)</FONT>>')

# Cross-links and delta analysis
dot.edge('user', 'role', label='B')                     # User-to-Role binding
dot.edge('user', 'ABACAllow', label='User attributes (roles)')  # User attributes into ABAC
dot.node('Delta', 
         label='<<I>Δ(u) = Perms</I><SUB>RBAC</SUB><I>(u) ∖ Perms</I>'
               '<SUB>ABAC</SUB><I>(u)</I>>', shape='rectangle')
dot.edge('Perms_RBAC', 'Delta', label='RBAC-only privileges')
dot.edge('Perms_ABAC', 'Delta', label='Revoked by ABAC', style='dashed', arrowhead='tee')

dot.render('rbac_abac_diagram', format='png')
