"""
Summary chart of validation results -> saved to assets/validation_summary.png
"""
import duckdb
import matplotlib
matplotlib.use("Agg")  
import matplotlib.pyplot as plt
import os

DB = "provider_validation.duckdb"
os.makedirs("assets", exist_ok=True)

con = duckdb.connect(DB)

# --- data for chart 1: issues by rule ---
rules = ["invalid_npi","excluded_provider","ghost_no_claims","state_mismatch","missing_phone"]
counts = []
for r in rules:
    c = con.execute(f"SELECT SUM(flag_{r}) FROM validation_flags").fetchone()[0] or 0
    counts.append(c)

# --- data for chart 2: recommended actions ---
actions = con.execute("""
    SELECT recommended_action, COUNT(*) n
    FROM gold_provider_scores GROUP BY recommended_action
""").fetchdf()
order = {"REMOVE":0,"REVIEW":1,"KEEP":2}
actions["o"] = actions.recommended_action.map(order)
actions = actions.sort_values("o")

con.close()

# --- building a 2-panel figure ---
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12,5))
fig.suptitle("Provider Directory Validation — Results Summary", fontsize=15, fontweight="bold")

# panel 1: flags by rule
bars = ax1.barh(rules[::-1], counts[::-1], color="#2c6e9c")
ax1.set_title("Listings failing each validation rule")
ax1.set_xlabel("Number of listings")
for bar, val in zip(bars, counts[::-1]):
    ax1.text(bar.get_width()+1, bar.get_y()+bar.get_height()/2, str(val), va="center")

# panel 2: recommended actions
colors = {"REMOVE":"#c0392b","REVIEW":"#e67e22","KEEP":"#27ae60"}
ax2.bar(actions.recommended_action, actions.n,
        color=[colors[a] for a in actions.recommended_action])
ax2.set_title("Recommended action per listing")
ax2.set_ylabel("Number of listings")
for i, (a, n) in enumerate(zip(actions.recommended_action, actions.n)):
    ax2.text(i, n+2, str(n), ha="center")

plt.tight_layout(rect=[0,0,1,0.95])
plt.savefig("assets/validation_summary.png", dpi=150, bbox_inches="tight")
print("Saved assets/validation_summary.png")