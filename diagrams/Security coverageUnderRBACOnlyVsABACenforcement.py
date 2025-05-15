import matplotlib.pyplot as plt
import numpy as np

# Synthetic invariant satisfaction data per scenario (RBAC vs RBAC+ABAC)
scenarios = ["Image registry bypass", "Wildcard ClusterRole binding", "Cross-tenant access"]
total_invariants = 5  # assume 5 security invariants checked per scenario
# Invariants satisfied vs violated under RBAC-only
satisfied_RBAC = [4, 4, 3]   # e.g., RBAC satisfies most invariants except a few...
violated_RBAC  = [1, 1, 2]   # ...violating 1–2 invariants per scenario
# Invariants satisfied vs violated under RBAC+ABAC (after fixes)
satisfied_ABAC = [5, 5, 5]   # ABAC+RBAC satisfies all invariants (no violations)
violated_ABAC  = [0, 0, 0]

labels = ["Image registry\nbypass", "Wildcard ClusterRole\nbinding", "Cross-tenant\naccess"]
x = np.arange(len(scenarios))
width = 0.3
offset = width/2 + 0.05  # offset bars for a slight gap between RBAC vs ABAC bars

fig, ax = plt.subplots(figsize=(6,4))
for i in range(len(scenarios)):
    # Positions for RBAC (left) and ABAC (right) bars in each group
    rbac_x = x[i] - offset
    abac_x = x[i] + offset
    # Plot RBAC-only bar (stacked segments)
    ax.bar(rbac_x, satisfied_RBAC[i], width, color='tab:green', label='Satisfied invariants' if i==0 else "")
    ax.bar(rbac_x, violated_RBAC[i], width, bottom=satisfied_RBAC[i], color='tab:red', label='Violated invariants' if i==0 else "")
    # Plot RBAC+ABAC bar (all satisfied, no violated segment needed)
    ax.bar(abac_x, satisfied_ABAC[i], width, color='tab:green')
    # Annotate counts inside each segment
    if satisfied_RBAC[i] > 0:
        ax.text(rbac_x + width/2, satisfied_RBAC[i]/2, str(satisfied_RBAC[i]), ha='center', va='center')
    if violated_RBAC[i] > 0:
        ax.text(rbac_x + width/2, satisfied_RBAC[i] + violated_RBAC[i]/2, str(violated_RBAC[i]), 
                ha='center', va='center', color='white')
    ax.text(abac_x + width/2, satisfied_ABAC[i]/2, str(satisfied_ABAC[i]), ha='center', va='center')
# Axis labels and title
ax.set_xticks(x)
ax.set_xticklabels(labels)
ax.set_ylabel('Number of Security Invariants')
ax.set_title('Security Coverage: RBAC-Only vs RBAC+ABAC')
ax.legend()

# Adjust y-limit and layout, then save as vector graphics
ax.set_ylim(0, total_invariants + 0.2)
fig.tight_layout()
fig.savefig("coverage_chart.pdf")
fig.savefig("coverage_chart.svg")
