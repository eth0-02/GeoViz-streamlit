"""
Icon and Symbol Library for GeoViz Studio
Provides functions to add custom icons, symbols, and infographic elements to maps
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, Circle, Rectangle, Polygon
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import io

def create_icon(icon_type, color="#333333", size=50):
    """
    Create a simple icon as PIL Image
    icon_type: 'oil', 'gold', 'fish', 'tree', 'factory', 'hospital', 'school', etc.
    """
    img = Image.new('RGBA', (size, size), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    
    # Convert hex color to RGB
    color_rgb = tuple(int(color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
    
    if icon_type == 'oil':
        # Oil barrel icon
        draw.ellipse([10, 10, 40, 20], fill=color_rgb)
        draw.rectangle([10, 15, 40, 40], fill=color_rgb)
        draw.ellipse([10, 35, 40, 45], fill=color_rgb)
        
    elif icon_type == 'gold':
        # Gold/diamond icon
        points = [(25, 10), (40, 25), (25, 40), (10, 25)]
        draw.polygon(points, fill=color_rgb)
        
    elif icon_type == 'fish':
        # Fish icon
        draw.ellipse([15, 20, 35, 30], fill=color_rgb)
        draw.polygon([(35, 25), (45, 20), (45, 30)], fill=color_rgb)  # tail
        draw.ellipse([28, 23, 32, 27], fill=(255, 255, 255))  # eye
        
    elif icon_type == 'tree':
        # Tree icon
        draw.rectangle([22, 30, 28, 45], fill=(139, 69, 19))  # trunk
        draw.ellipse([10, 10, 40, 35], fill=color_rgb)  # foliage
        
    elif icon_type == 'factory':
        # Factory icon
        draw.rectangle([10, 25, 40, 45], fill=color_rgb)
        draw.rectangle([15, 10, 20, 25], fill=color_rgb)  # chimney
        draw.rectangle([30, 15, 35, 25], fill=color_rgb)  # chimney
        
    elif icon_type == 'hospital':
        # Hospital cross
        draw.rectangle([20, 10, 30, 40], fill=color_rgb)
        draw.rectangle([10, 20, 40, 30], fill=color_rgb)
        
    elif icon_type == 'school':
        # School building
        draw.rectangle([10, 20, 40, 45], fill=color_rgb)
        draw.polygon([(25, 10), (5, 20), (45, 20)], fill=color_rgb)  # roof
        
    else:
        # Default circle
        draw.ellipse([10, 10, 40, 40], fill=color_rgb)
    
    return img

def add_icon_to_map(ax, lon, lat, icon_type, color="#333333", size=0.02, transform=None):
    """
    Add an icon to a matplotlib map
    """
    icon_img = create_icon(icon_type, color, size=50)
    imagebox = OffsetImage(icon_img, zoom=size)
    
    if transform is None:
        ab = AnnotationBbox(imagebox, (lon, lat), frameon=False, xycoords='data')
    else:
        ab = AnnotationBbox(imagebox, (lon, lat), frameon=False, xycoords='data')
    
    ax.add_artist(ab)
    return ab

def add_text_label(ax, lon, lat, text, fontsize=10, color='black', bbox_style=None):
    """
    Add a text label to the map
    """
    if bbox_style:
        ax.text(lon, lat, text, fontsize=fontsize, color=color,
                bbox=dict(boxstyle=bbox_style, facecolor='white', alpha=0.8, edgecolor='none'),
                ha='center', va='center')
    else:
        ax.text(lon, lat, text, fontsize=fontsize, color=color,
                ha='center', va='center')

def create_infographic_legend(categories, colors, icons=None):
    """
    Create a professional infographic-style legend
    Returns a list of matplotlib patches
    """
    legend_elements = []
    
    for i, (category, color) in enumerate(zip(categories, colors)):
        if icons and i < len(icons):
            # Icon-based legend (would need custom handler)
            patch = mpatches.Patch(facecolor=color, edgecolor='black', linewidth=0.5, label=category)
        else:
            patch = mpatches.Patch(facecolor=color, edgecolor='black', linewidth=0.5, label=category)
        legend_elements.append(patch)
    
    return legend_elements

def add_pattern_fill(ax, geometry, pattern='/', color='blue', alpha=0.5):
    """
    Add pattern fills (hatching) to polygons
    """
    from matplotlib.patches import PathPatch
    from matplotlib.path import Path
    
    # This would require converting shapely geometry to matplotlib path
    # Simplified version - just add hatching to existing plot
    pass

def create_donut_chart_icon(values, colors, size=100):
    """
    Create a donut chart as an icon (for infographic maps)
    """
    fig, ax = plt.subplots(figsize=(size/100, size/100))
    ax.pie(values, colors=colors, startangle=90, counterclock=False,
           wedgeprops=dict(width=0.3, edgecolor='white'))
    ax.axis('equal')
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', transparent=True, bbox_inches='tight', pad_inches=0)
    buf.seek(0)
    img = Image.open(buf)
    plt.close(fig)
    
    return img
