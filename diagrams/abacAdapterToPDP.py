from graphviz import Digraph

dot = Digraph('adapter_pdp', filename='adapter_to_pdp')
dot.attr('node', fontname='Helvetica'); dot.attr('edge', fontname='Helvetica')

# Kubernetes AdmissionReview (simplified fields)
dot.node('AR', shape='record', label="{{AdmissionReview}|{<user> user: Alice | groups: [dev, ops] | <verb> verb: create | <res> resource: Deployment | <ns> namespace: prod}}")

# XACML Request (subject, resource, action attributes)
dot.node('XACML', shape='record', label="{{XACML Request}|{<subj> Subject: user=Alice, groups=[dev,ops] | <resAttr> Resource: type=Deployment, ns=prod | <act> Action: verb=create}}")

# PDP and response
dot.node('PDP',  "AuthzForce PDP\n(XACML Evaluation)")
dot.node('Resp', "AdmissionReview Response\n(Allowed or Denied)")

# Field mapping (dotted lines)
dot.edge('AR:user', 'XACML:subj',    style='dotted')  # user -> subject.user
# Map resource kind and namespace to resource attributes:
dot.edge('AR:res',  'XACML:resAttr', style='dotted')  # kind -> resource.type
dot.edge('AR:ns',   'XACML:resAttr', style='dotted')  # namespace -> resource.ns
dot.edge('AR:verb', 'XACML:act',     style='dotted')  # verb -> action

# PDP query/response (solid arrows)
dot.edge('XACML', 'PDP', label="XACML request")
dot.edge('PDP', 'Resp', label="Permit/Deny decision")

dot.attr(rankdir='LR')

# Render to PDF and SVG
dot.render('adapter_to_pdp.pdf', format='pdf')
dot.render('adapter_to_pdp.svg', format='svg')
