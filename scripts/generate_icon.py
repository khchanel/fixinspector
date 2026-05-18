#!/usr/bin/env python
"""Generate PNG icon from SVG using Qt."""
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QIcon
from PySide6.QtWidgets import QApplication


def generate_png_icon():
    """Convert SVG icon to PNG for better Windows compatibility."""
    svg_path = Path(__file__).parent.parent / "fixinspector" / "assets" / "app-icon.svg"
    png_path = svg_path.with_suffix(".png")

    if png_path.exists():
        print(f"PNG icon already exists: {png_path}")
        return

    # Create minimal Qt app to render SVG
    app = QApplication([])

    # Load SVG and render to PNG
    icon = QIcon(str(svg_path))

    # Create image at standard sizes for taskbar
    image = QImage(256, 256, QImage.Format_ARGB32)
    image.fill(Qt.transparent)

    # Paint icon onto image
    from PySide6.QtGui import QPainter
    painter = QPainter(image)
    icon.paint(painter, 0, 0, 256, 256)
    painter.end()

    # Save PNG
    if image.save(str(png_path)):
        print(f"Generated PNG icon: {png_path}")
    else:
        print(f"Failed to generate PNG icon")


if __name__ == "__main__":
    generate_png_icon()

