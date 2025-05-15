from graphviz import Digraph

dot = Digraph('smt_flow', filename='smt_verification_flow')
dot.attr('node', shape='rectangle', style='rounded', fontname='Helvetica')
dot.attr('edge', fontname='Helvetica')

# Define nodes for each step in the verification flow
dot.node('parse',    "Parse policy YAML files\n(+ invariants)")
dot.node('encode',   "Compile policies to SMT formulas")
dot.node('solve',    "Query SMT solver (e.g., Z3)")
dot.node('result',   "Solver result: SAT/UNSAT\n(+ model if SAT)")
dot.node('explain',  "Interpret counterexample\n(if model found)")

# Connect the steps in order
dot.edge('parse', 'encode')
dot.edge('encode', 'solve')
dot.edge('solve', 'result')
dot.edge('result', 'explain')

# Top-to-bottom layout
dot.attr(rankdir='TB')

# Render to PDF and SVG
dot.render('smt_verification_flow.pdf', format='pdf')
dot.render('smt_verification_flow.svg', format='svg')
