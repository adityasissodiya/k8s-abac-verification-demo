import matplotlib.pyplot as plt
import numpy as np

# Data: violations detected in each scenario (before vs. after ABAC mitigation)
scenarios = ["Image registry bypass", "Wildcard ClusterRole binding", "Cross-tenant access"]
violations_before = [1, 1, 2]  # e.g., 1–2 violations per case under RBAC-only
violations_after  = [0, 0, 0]  # violations after ABAC policy fix (all resolved)

# Use multi-line labels for better readability on x-axis
labels = ["Image registry\nbypass", "Wildcard ClusterRole\nbinding", "Cross-tenant\naccess"]

# Plot grouped bar chart
x = np.arange(len(scenarios))
width = 0.35
fig, ax = plt.subplots(figsize=(6,4))
bars1 = ax.bar(x - width/2, violations_before, width, color='tab:red', label='Before ABAC')
bars2 = ax.bar(x + width/2, violations_after,  width, color='tab:green', label='After ABAC')

# Label axes and title
ax.set_xticks(x)
ax.set_xticklabels(labels)
ax.set_ylabel('Number of Policy Violations')
ax.set_title('Policy Violations Detected: Before vs After ABAC Mitigation')
ax.legend()

# Annotate bar values on top of each bar
for bar in bars1:
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05, str(int(bar.get_height())),
            ha='center', va='bottom')
for bar in bars2:
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05, str(int(bar.get_height())),
            ha='center', va='bottom')

# Save figures in vector formats for publication
fig.tight_layout()
fig.savefig("violations_chart.pdf")
fig.savefig("violations_chart.svg")
