import json
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

with open('output/pipeline/20260109-04.pipeline.json', encoding='utf-8') as f:
    data = json.load(f)

fr = data['file_routing']
clfs = data.get('classifications', [])

fig = plt.figure(figsize=(15, 10))
gs = fig.add_gridspec(2, 2, hspace=0.32, wspace=0.25)

# 1. Pie chart
ax1 = fig.add_subplot(gs[0, 0])
sizes = [fr['n_auto'], fr['n_needs_human']]
labels = [f"Auto-file ({fr['n_auto']})", f"Needs Human ({fr['n_needs_human']})"]
ax1.pie(sizes, labels=labels, autopct='%1.1f%%', colors=['#2ecc71', '#e74c3c'], startangle=140, textprops={'fontsize': 11, 'weight': 'bold'})
ax1.set_title('Ty Le Xu Ly: Auto vs Needs Human', fontsize=13, weight='bold')

# 2. Tiers bar
ax2 = fig.add_subplot(gs[0, 1])
tiers = pd.Series([c['tier'] for c in clfs]).value_counts()
ax2.bar(tiers.index, tiers.values, color=['#3498db', '#2ecc71', '#e74c3c'], width=0.5)
ax2.set_title('Phan Bo Tang Quyet Dinh (Tier)', fontsize=13, weight='bold')
ax2.set_ylabel('So lat cat')
for i, v in enumerate(tiers.values):
    ax2.text(i, v + 0.5, str(v), ha='center', weight='bold')

# 3. Categories horizontal bar
ax3 = fig.add_subplot(gs[1, :])
cats = pd.Series([c.get('predicted_category', 'UNKNOWN') for c in clfs]).value_counts()
colors = ['#e74c3c' if x == 'UNKNOWN' else '#2980b9' for x in cats.index]
bars = ax3.barh(cats.index, cats.values, color=colors)
ax3.set_title('So Luong Lat Cat Theo Tung Loai Tai Lieu', fontsize=13, weight='bold')
ax3.set_xlabel('So lat cat')
ax3.invert_yaxis()
for bar in bars:
    ax3.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height()/2, str(int(bar.get_width())), va='center', weight='bold')

title_text = f"KET QUA PHAN LOAI PIPELINE: {data['file_name']} (69 trang -> 57 lat cat)"
plt.suptitle(title_text, fontsize=15, weight='bold')
plt.savefig('output/pipeline_overview_chart.png', dpi=150, bbox_inches='tight')
print("DA XUAT ANH: output/pipeline_overview_chart.png")
