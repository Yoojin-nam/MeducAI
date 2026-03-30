"""
Example NPJ Digital Medicine Plotting Script

This script demonstrates how to generate publication-quality figures 
from QA Survey data (Paper 1 / Paper 3) using the custom MeducAI NPJ Theme.

To run:
    python -m src.tools.qa.example_npj_plot_survey_results
"""

import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
import os

from src.tools.meducai_plot_theme import apply_npj_theme, NPJ_PALETTE

def plot_mock_survey_results():
    # 1. Apply the strict NPJ Digital Medicine Theme (Single column = 89mm width)
    apply_npj_theme(fig_type='single')
    
    # 2. Mock Data generation (Simulating S5 Multi-agent Validation scores)
    groups = ['Control (Resident)', 'S5 (AI Agent)', 'Specialist']
    scores_mean = [3.2, 4.3, 4.6]
    scores_std = [0.4, 0.3, 0.2]
    
    df = pd.DataFrame({
        'Group': groups,
        'Mean Score (1-5)': scores_mean,
        'Error': scores_std
    })

    # 3. Create the figure explicitly
    fig, ax = plt.subplots()

    # 4. Plot using the defined Nature Palette (Colorblind friendly)
    bars = sns.barplot(
        data=df, 
        x='Group', y='Mean Score (1-5)', 
        ax=ax,
        palette=[NPJ_PALETTE['neutral_gray'], NPJ_PALETTE['primary_blue'], NPJ_PALETTE['secondary_teal']],
        capsize=0.1, err_kws={'linewidth': 0.75}
    )
    
    # Add error bars manually if using older seaborn or specifically formatting Nature style
    ax.errorbar(
        x=np.arange(len(df)),
        y=df['Mean Score (1-5)'],
        yerr=df['Error'],
        fmt='none',
        c='black',
        capsize=3,
        linewidth=0.75
    )

    # 5. npj Typography constraints (Titles clean, limits explicitly set)
    ax.set_ylim(1, 5)
    ax.set_ylabel("Mean Confidence Score (1-5)")
    ax.set_xlabel("") # Often implicit in group labels
    
    # 6. Save specifically as PDF with 600 DPI (Nature standard for line art/charts)
    out_dir = "7_Manuscript/figures"
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "Figure1_Mock_Survey_Results.pdf")
    
    plt.tight_layout()
    plt.savefig(out_path, format='pdf', dpi=600)
    print(f"✅ Generated NPJ compliant plot: {out_path}")

if __name__ == "__main__":
    plot_mock_survey_results()
