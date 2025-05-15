from graphviz import Digraph

dot = Digraph('counterexample', filename='counterexample_flow')
dot.attr('node', fontname='Helvetica'); dot.attr('edge', fontname='Helvetica')

# Invariant and policy nodes
dot.node('inv',  "Security invariant φ:\nimage registry must equal 'myregistry.com'")
dot.node('pol',  "Misconfigured policy π:\nallows registry prefix 'myregistry.com*'")

# Solver process node
dot.node('solver', "SMT Solver (Z3)\nchecks φ vs. π")

# Counterexample and outcome nodes
dot.node('cex',   "Counterexample model:\nregistry = 'myregistry.com.attacker.com'\n(violates φ, allowed by π)")
dot.node('misconf', "Identified misconfiguration:\nprefix-match logic in policy is too broad")

# Relationships
dot.edge('inv', 'solver')
dot.edge('pol', 'solver')
dot.edge('solver', 'cex', label="finds violation")
dot.edge('cex', 'misconf', label="highlights flaw in policy")

dot.attr(rankdir='TB')

# Render to PDF and SVG
dot.render('counterexample_flow.pdf', format='pdf')
dot.render('counterexample_flow.svg', format='svg')
