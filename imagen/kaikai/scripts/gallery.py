#!/usr/bin/env python3
"""
Gallery Viewer and Selector for Generated Characters
Displays contact sheet and allows selection of best images.
"""

import glob
import os
import shutil
from pathlib import Path

try:
    from PIL import Image
    import matplotlib.pyplot as plt
    import matplotlib
    matplotlib.rcParams['font.family'] = 'DejaVu Sans'
except ImportError as e:
    print(f"❌ Missing dependency: {e}")
    print("Install with: pip install Pillow matplotlib")
    exit(1)


DEFAULT_OUTPUT_DIR = "/content/generated_characters"
DEFAULT_SELECTED_DIR = "/content/selected_characters"


def create_contact_sheet(
    images: list[str],
    output_path: str,
    cols: int = 5
) -> str:
    """Create a contact sheet grid of all generated images."""
    
    rows = (len(images) + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols, figsize=(20, 4 * rows))
    
    if rows == 1:
        axes = [axes]
    
    for idx, img_path in enumerate(images):
        row = idx // cols
        col = idx % cols
        
        img = Image.open(img_path)
        ax = axes[row][col] if rows > 1 else axes[col]
        ax.imshow(img)
        
        # Extract filename for label
        fname = os.path.basename(img_path)
        ax.set_title(f"#{idx+1}\n{fname}", fontsize=8)
        ax.axis('off')
    
    # Hide empty cells
    for idx in range(len(images), rows * cols):
        row = idx // cols
        col = idx % cols
        ax = axes[row][col] if rows > 1 else axes[col]
        ax.axis('off')
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.show()
    
    return output_path


def view_gallery(
    output_dir: str = None,
    cols: int = 5
) -> list[str]:
    """Display all generated images in a grid."""
    
    if output_dir is None:
        output_dir = DEFAULT_OUTPUT_DIR
    
    images = sorted(glob.glob(f"{output_dir}/*.png"))
    
    if not images:
        print("❌ No images found")
        return []
    
    # Create contact sheet
    contact_path = os.path.join(output_dir, "contact_sheet.png")
    create_contact_sheet(images, contact_path, cols)
    
    print(f"\n📊 Total: {len(images)} images")
    print("="*50)
    
    return images


def select_images(
    selected_numbers: str,
    output_dir: str = None,
    selected_dir: str = None
) -> list[str]:
    """Copy selected images to a separate folder."""
    
    if output_dir is None:
        output_dir = DEFAULT_OUTPUT_DIR
    
    if selected_dir is None:
        selected_dir = DEFAULT_SELECTED_DIR
    
    os.makedirs(selected_dir, exist_ok=True)
    
    images = sorted(glob.glob(f"{output_dir}/*.png"))
    
    if not images:
        print("❌ No images found")
        return []
    
    # Parse selected numbers (1-indexed)
    selected = [int(n.strip()) - 1 for n in selected_numbers.split(",")]
    
    copied_files = []
    print("\n🏆 Selected images:")
    
    for idx in selected:
        if 0 <= idx < len(images):
            src = images[idx]
            dst = os.path.join(selected_dir, os.path.basename(src))
            shutil.copy2(src, dst)
            copied_files.append(dst)
            print(f"   ✅ #{idx+1}: {os.path.basename(src)} → selected/")
    
    print(f"\n📁 Saved to: {selected_dir}")
    print(f"📊 Total selected: {len(copied_files)}")
    
    return copied_files


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='View and select generated characters')
    parser.add_argument('--dir', type=str, default=None, help='Output directory')
    parser.add_argument('--selected-dir', type=str, default=None, help='Selected images directory')
    parser.add_argument('--select', type=str, default=None, 
                       help='Comma-separated image numbers to select (e.g., "1,5,8")')
    parser.add_argument('--cols', type=int, default=5, help='Grid columns')
    
    args = parser.parse_args()
    
    # View gallery
    images = view_gallery(output_dir=args.dir, cols=args.cols)
    
    # Select images if specified
    if args.select and images:
        select_images(
            selected_numbers=args.select,
            output_dir=args.dir,
            selected_dir=args.selected_dir
        )


if __name__ == '__main__':
    main()
