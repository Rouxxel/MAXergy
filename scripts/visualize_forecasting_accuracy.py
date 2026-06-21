import matplotlib.pyplot as plt
import numpy as np

# Data: overall RMSPE (%) by energy series
series = ["Electricity", "Gas", "Heating oil", "Petrol"]
models = ["Persistence forecast", "Deterministic trend", "ETS", "SARIMA"]

values = {
    "Electricity": [1.25, 2.68, 2.37, 6.17],
    "Gas": [1.35, 3.16, 1.34, 8.55],
    "Heating oil": [4.75, 6.66, 4.77, 11.40],
    "Petrol": [3.58, 4.48, 3.58, 5.62],
}

# Styling
BG = "#FFFFFF"
TEXT = "#000000"
GRID = "#E5E7EB"
BEST = "#B8FF5A"
OTHER = "#D1D5DB"
SERIES_LINE = "#E5E7EB"

# Figure
fig = plt.figure(figsize=(15, 9), facecolor=BG)

# Consistent margins for title/subtitle/chart/footer
left_margin = 0.07
right_margin = 0.95
bottom_margin = 0.12
top_axes = 0.80

ax = fig.add_axes([
    left_margin,
    bottom_margin,
    right_margin - left_margin,
    top_axes - bottom_margin
])
ax.set_facecolor(BG)

# Layout parameters
bar_height = 0.16
row_step = 0.28
group_gap = 1.30
x_start = 2.25  # bars start here so labels do not overlap

# Compute evenly spaced y positions
series_tops = []
all_bar_y = []
all_bar_vals = []
all_bar_colors = []
all_model_labels = []
all_value_labels = []

current_top = (len(series) - 1) * (4 * row_step + group_gap)

for s in series:
    vals = values[s]
    best_val = min(vals)
    series_tops.append(current_top)

    for model, val in zip(models, vals):
        y = current_top - len([yy for _, yy, ss in all_model_labels if ss == s]) * row_step
        all_bar_y.append(y)
        all_bar_vals.append(val)
        all_model_labels.append((model, y, s))
        all_value_labels.append((val, y, s))
        all_bar_colors.append(BEST if np.isclose(val, best_val) else OTHER)

    current_top -= (4 * row_step + group_gap)

# Draw bars
for y, val, color in zip(all_bar_y, all_bar_vals, all_bar_colors):
    ax.barh(
        y=y,
        width=val,
        left=x_start,
        height=bar_height,
        color=color,
        edgecolor="none"
    )

# Add model labels and value labels
for (model, y, s), (val, _, _) in zip(all_model_labels, all_value_labels):
    best_val = min(values[s])
    is_best = np.isclose(val, best_val)
    weight = "bold" if is_best else "normal"

    ax.text(
        0.05, y,
        model,
        ha="left", va="center",
        fontsize=11,
        color=TEXT,
        fontweight=weight
    )

    ax.text(
        x_start + val + 0.12, y,
        f"{val:.2f}%",
        ha="left", va="center",
        fontsize=12,
        color=TEXT,
        fontweight=weight
    )

# Series titles and separators
for i, s in enumerate(series):
    top = series_tops[i]

    ax.text(
        0.0, top + 0.38,
        s,
        ha="left", va="bottom",
        fontsize=18,
        fontweight="bold",
        color=TEXT
    )

    if i < len(series) - 1:
        sep_y = top - (3 * row_step) - 0.42
        ax.axhline(sep_y, color=SERIES_LINE, linewidth=1.2)

# Title
fig.text(
    left_margin, 0.94,
    "Why we chose the Persistence forecast",
    fontsize=28,
    fontweight="bold",
    color=TEXT,
    ha="left"
)

# Subtitle with italic Destatis
subtitle = (
    r"RMSPE Forecast error across four German energy price series, "
    r"evaluated on 2020 to 2025 monthly CPI data from $\it{Destatis}$ "
    r"(lower is better)"
)

fig.text(
    left_margin, 0.885,
    subtitle,
    fontsize=13.5,
    color=TEXT,
    ha="left"
)

# Clean axis
ax.set_xlim(0, x_start + 12.6)
ax.set_ylim(min(all_bar_y) - 0.6, max(all_bar_y) + 0.8)
ax.set_xticks([])
ax.set_yticks([])

for spine in ax.spines.values():
    spine.set_visible(False)

# Footer
fig.text(
    left_margin, 0.06,
    "The Persistence forecast is best overall for 3 of 4 series and ties for best on petrol.",
    fontsize=13.5,
    color=TEXT,
    fontweight="bold",
    ha="left"
)

# Save
plt.savefig("documentation/images/pitch_overall_rmspe_final_subtitle.png", dpi=300, bbox_inches="tight", facecolor=BG)
# plt.savefig("documentation/images/pitch_overall_rmspe_final_subtitle.svg", bbox_inches="tight", facecolor=BG)

# plt.show()