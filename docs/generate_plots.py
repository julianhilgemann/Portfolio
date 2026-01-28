import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats

# Style Configuration
sns.set_theme(style="whitegrid", context="talk")
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Arial', 'Helvetica', 'DejaVu Sans']

# Color Palette (Professional/Dark Blue-ish)
colors = ["#2E4053", "#1ABC9C", "#E74C3C", "#8E44AD"]

fig, axes = plt.subplots(2, 2, figsize=(16, 12))
plt.subplots_adjust(hspace=0.4, wspace=0.3)

# 1. Customer Arrivals (Poisson)
# Distribution of Daily Arrivals for a high-volume day
# Let's assume Monthly Target = 300 -> Daily Lambda = 10
ax1 = axes[0, 0]
lambda_val = 10
x_p = np.arange(0, 25)
pmf_p = stats.poisson.pmf(x_p, lambda_val)

ax1.bar(x_p, pmf_p, color=colors[0], alpha=0.8, edgecolor='black', width=1.0)
ax1.set_title("Daily Customer Arrivals (Poisson)", fontsize=16, fontweight='bold', pad=15)
ax1.set_xlabel("Number of New Customers", fontsize=12)
ax1.set_ylabel("Probability", fontsize=12)
ax1.text(0.95, 0.95, f"$\\lambda = {lambda_val}$ customers/day", 
         transform=ax1.transAxes, ha='right', va='top', fontsize=12,
         bbox=dict(facecolor='white', alpha=0.8, edgecolor='none'))
ax1.grid(axis='x')

# 2. Market Noise (AR(1))
# Simulate a year
ax2 = axes[0, 1]
np.random.seed(42)
days = 365
rho = 0.6
sigma = 0.1
noise = [0]
for _ in range(days):
    noise.append(rho * noise[-1] + sigma * np.random.normal())
noise = np.array(noise[1:])
# Convert to multiplicative effect: exp(noise)
effect = np.exp(noise)

ax2.plot(effect, color=colors[1], linewidth=2)
ax2.axhline(1.0, color='gray', linestyle='--', linewidth=1)
ax2.set_title("Market Regime Noise (AR(1))", fontsize=16, fontweight='bold', pad=15)
ax2.set_xlabel("Simulation Day", fontsize=12)
ax2.set_ylabel("Demand Multiplier", fontsize=12)
ax2.text(0.95, 0.95, f"$\\rho = {rho}$\n$\\sigma = {sigma}$", 
         transform=ax2.transAxes, ha='right', va='top', fontsize=12,
         bbox=dict(facecolor='white', alpha=0.8, edgecolor='none'))
ax2.set_ylim(0.5, 1.8)

# 3. ARPU Distribution (Lognormal)
ax3 = axes[1, 0]
target_arpu = 1000
arpu_sigma = 0.05
# mu for underlying normal
mu = np.log(target_arpu) - (arpu_sigma**2)/2
x_l = np.linspace(800, 1200, 1000)
pdf_l = stats.lognorm.pdf(x_l, arpu_sigma, scale=np.exp(mu))

ax3.plot(x_l, pdf_l, color=colors[2], linewidth=2.5)
ax3.fill_between(x_l, pdf_l, color=colors[2], alpha=0.1)
ax3.set_title("Subscription Price (Lognormal)", fontsize=16, fontweight='bold', pad=15)
ax3.set_xlabel("Monthly Recurring Revenue (€)", fontsize=12)
ax3.set_ylabel("Density", fontsize=12)
ax3.text(0.95, 0.95, f"Target = €{target_arpu}\n$\\sigma = {arpu_sigma}$", 
         transform=ax3.transAxes, ha='right', va='top', fontsize=12,
         bbox=dict(facecolor='white', alpha=0.8, edgecolor='none'))

# 4. Churn Hazard (Tenure Decay)
ax4 = axes[1, 1]
tenure_months = np.linspace(1, 24, 100)
base_prob = 0.013 # ~15% annual
beta = 0.5 # decay
hazard = base_prob * (tenure_months ** -beta)

ax4.plot(tenure_months, hazard * 100, color=colors[3], linewidth=2.5) # As percentage
ax4.set_title("Churn Hazard Function (Tenure Decay)", fontsize=16, fontweight='bold', pad=15)
ax4.set_xlabel("Customer Tenure (Months)", fontsize=12)
ax4.set_ylabel("Monthly Churn Probability (%)", fontsize=12)
ax4.text(0.95, 0.95, f"Base Rate = {base_prob*100:.1f}%\nDecay $\\beta = {beta}$", 
         transform=ax4.transAxes, ha='right', va='top', fontsize=12,
         bbox=dict(facecolor='white', alpha=0.8, edgecolor='none'))
ax4.set_ylim(0, 2.0)

# Add constraints/info header
fig.suptitle("Stochastic Engine: Generator Distributions", fontsize=24, fontweight='bold', y=0.98)

# Save
output_path = "docs/assets/generator_distributions.png"
plt.savefig(output_path, dpi=300, bbox_inches='tight')
print(f"Plot saved to {output_path}")
