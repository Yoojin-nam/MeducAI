"""
MeducAI Premium Plot Theme (npj Digital Medicine Journal Quality)

This module sets up Matplotlib and Seaborn configurations specifically tailored for
Nature Portfolio (npj Digital Medicine) submission standards.

Nature Portfolio guidelines:
- Typography: Sans-serif (Arial or Helvetica)
- Font sizes: 5-7 pt (minimum) up to 8 pt (labels). No more than 9 pt.
- Line weights: 0.5 pt minimum, optimally around 0.5-1.0 pt.
- Figure widths: Single column = 89 mm (~3.5 inches), Two column = 183 mm (~7.2 inches)

Usage:
    from tools.meducai_plot_theme import apply_npj_theme, NPJ_PALETTE
    apply_npj_theme(fig_type='single')
"""

import matplotlib.pyplot as plt
import seaborn as sns

# NPJ Digital Medicine Recommended Color Palette (Nature style, colorblind safe)
NPJ_PALETTE = {
    'primary_blue': '#0072B2',    # Colorblind safe blue
    'secondary_teal': '#009E73',  # Colorblind safe bluish green
    'accent_red': '#D55E00',      # Vermillion/Red
    'neutral_gray': '#555555',    # Charcoal gray for text/borders
    'light_amber': '#E69F00',     # Orange
    'grid_color': '#EAEAEA',      # Very soft grid
}

def apply_npj_theme(fig_type='single', base_context='paper'):
    """
    Applies the Nature Portfolio (npj) premium journal-quality style.
    
    Args:
        fig_type (str): 'single' (89mm) or 'double' (183mm) column width.
        base_context (str): seaborn context
    """
    # 1. Base seaborn style
    sns.set_theme(style="ticks", context=base_context)
    
    # 2. Figure sizing (mm to inches conversion: 1 inch = 25.4 mm)
    if fig_type == 'single':
        fig_width = 89 / 25.4   # ~3.5 inches
        fig_height = fig_width * 0.75 # 4:3 default ratio
    else:
        fig_width = 183 / 25.4  # ~7.2 inches
        fig_height = fig_width * 0.5  # Widescreen or 2:1 ratio for double columns
        
    # 3. Nature Portfolio rcParams requirements
    custom_params = {
        'figure.figsize': (fig_width, fig_height),
        'figure.dpi': 300,
        'savefig.dpi': 600,  # 600 DPI recommended for line art in Nature
        'savefig.format': 'pdf',
        'savefig.bbox': 'tight',
        'savefig.pad_inches': 0.05,
        
        # Typography (strict Nature rules)
        'font.family': 'sans-serif',
        'font.sans-serif': ['Arial', 'Helvetica', 'sans-serif'],
        'font.size': 7,
        'axes.labelsize': 8,
        'axes.titlesize': 8,
        'xtick.labelsize': 7,
        'ytick.labelsize': 7,
        'legend.fontsize': 7,
        'legend.title_fontsize': 8,
        
        # Grid lines and Axes
        'axes.linewidth': 0.75,
        'axes.edgecolor': 'black',
        'axes.grid': False, # Nature prefers clean backgrounds without dense grids
        
        # Spine removal (Top and Right)
        'axes.spines.top': False,
        'axes.spines.right': False,
        
        # Ticks
        'xtick.major.width': 0.75,
        'ytick.major.width': 0.75,
        'xtick.color': 'black',
        'ytick.color': 'black',
        'xtick.direction': 'out',
        'ytick.direction': 'out',
        
        # Lines and Markers
        'lines.linewidth': 1.0,
        'lines.markersize': 4,
        'patch.linewidth': 0.75,
        'patch.edgecolor': 'black',
        
        # Colors (Colorblind safe)
        'axes.prop_cycle': plt.cycler(color=[
            NPJ_PALETTE['primary_blue'], 
            NPJ_PALETTE['secondary_teal'], 
            NPJ_PALETTE['light_amber'], 
            NPJ_PALETTE['accent_red'], 
            '#CC79A7'  # Reddish purple
        ]),
    }
    
    plt.rcParams.update(custom_params)
    print(f"✅ npj Digital Medicine Plot Theme ('{fig_type}' column) applied.")
if __name__ == "__main__":
    apply_npj_theme()
    # Demo plot
    sns.barplot(x=['Control', 'Treatment A', 'Treatment B'], y=[10, 20, 15])
    plt.title("npj Digital Medicine Sample Theme")
    plt.xlabel("Groups")
    plt.ylabel("Scores")
    plt.tight_layout()
    # plt.show()

