import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import pandas as pd

# Style Configuration
sns.set_theme(style="whitegrid", context="talk")
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Arial', 'Helvetica', 'DejaVu Sans']

# Color Palette (consistent with generate_plots.py)
colors = ["#2E4053", "#1ABC9C", "#E74C3C", "#8E44AD"]
# Navy, Teal, Red, Purple

# 1 Row, 2 Columns
fig, axes = plt.subplots(1, 2, figsize=(16, 7))
plt.subplots_adjust(wspace=0.3)

# ---------------------------------------------------------
# 1. Trend Change (Regime Detection)
# ---------------------------------------------------------
ax1 = axes[0]

# Simulate time
t = np.linspace(0, 48, 200) # 4 years (months)
# Piecewise trend
trend = np.piecewise(t, [t < 24, t >= 24], [lambda x: 100 + 5*x, lambda x: 220 + 15*(x-24)])
# Add some noise
np.random.seed(42)
y_noisy = trend + np.random.normal(0, 10, size=len(t))

# Plot 'Earlier' data (Low Growth)
ax1.plot(t[:100], y_noisy[:100], color='gray', alpha=0.5, label='Legacy Regime', linestyle='--')
# Plot 'Recent' data (High Growth)
ax1.plot(t[100:], y_noisy[100:], color=colors[0], linewidth=3, label='Active Regime')
# Plot Trend Line
ax1.plot(t, trend, color=colors[2], linewidth=2, linestyle=':')

ax1.axvline(24, color='black', linestyle='--', alpha=0.3)

ax1.set_title("1. Trend Changepoints (Regime Detection)", fontsize=16, fontweight='bold', pad=15)
ax1.set_xlabel("Time (Months)", fontsize=12)
ax1.set_ylabel("Metric (e.g., MRR)", fontsize=12)
ax1.text(0.05, 0.85, "Phase 1:\nSlow Growth", transform=ax1.transAxes, fontsize=11, color='gray')
ax1.text(0.55, 0.40, "Phase 2:\nAccelerated Growth", transform=ax1.transAxes, fontsize=11, color=colors[0], fontweight='bold')
ax1.legend(loc='lower right', fontsize=10)


# ---------------------------------------------------------
# 2. Final Forecast Composition (Posterior)
# ---------------------------------------------------------
ax2 = axes[1]

# History
t_hist = np.linspace(0, 50, 50)
y_hist = 50 + 2*t_hist + np.random.normal(0, 5, 50)
# Forecast
t_fut = np.linspace(50, 80, 30)
y_fut = 50 + 2*t_fut # Linear extension
# Uncertainty (widening funnel)
uncertainty = np.linspace(5, 20, 30)

# Plot History
ax2.scatter(t_hist, y_hist, color='black', s=20, label='Actuals (ACT)')
# Plot Forecast
ax2.plot(t_fut, y_fut, color=colors[0], linewidth=3, label='Forecast (FCT)')
# Plot Uncertainty
ax2.fill_between(t_fut, y_fut - uncertainty, y_fut + uncertainty, color=colors[0], alpha=0.2, label='80% Confidence Interval')

ax2.axvline(50, color=colors[2], linestyle='--', label='Cutoff Date')

ax2.set_title("2. Final Forecast Composition", fontsize=16, fontweight='bold', pad=15)
ax2.set_xlabel("Timeline", fontsize=12)
ax2.set_ylabel("Projected Value", fontsize=12)
ax2.legend(loc='upper left', fontsize=10)


# Main Title
fig.suptitle("Forecasting Engine: Prophet Mechanism & Results", fontsize=24, fontweight='bold', y=0.98)

# Save
output_path = "docs/assets/forecast_mechanism.png"
plt.savefig(output_path, dpi=300, bbox_inches='tight')
print(f"Plot saved to {output_path}")
