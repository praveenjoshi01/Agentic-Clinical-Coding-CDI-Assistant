"""
PIL-based clinical note image generator.

Generates synthetic clinical note images for testing image ingestion.
Uses PIL to render text as images simulating scanned documents.
"""

from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import textwrap


# Import image note text from generate_test_data
from generate_test_data import IMAGE_NOTES


def generate_clinical_note_image(
    note_text: str,
    output_path: str,
    width: int = 800,
    dpi: int = 150
) -> None:
    """
    Generate a PIL-rendered clinical note image.

    Args:
        note_text: Clinical text to render
        output_path: Path to save PNG image
        width: Image width in pixels (default 800)
        dpi: DPI for image (default 150)
    """
    # Use default font (no external dependencies)
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None  # Fall back to PIL default

    # Wrap text at 80 characters per line
    lines = []
    for line in note_text.split('\n'):
        if line.strip():
            wrapped = textwrap.wrap(line, width=80)
            if wrapped:
                lines.extend(wrapped)
            else:
                lines.append('')  # Preserve empty lines
        else:
            lines.append('')  # Preserve paragraph breaks

    # Calculate image height
    line_height = 20  # pixels per line
    padding = 40  # top and bottom padding
    height = len(lines) * line_height + padding * 2

    # Create off-white background (simulate scan)
    bg_color = (248, 248, 240)
    text_color = (20, 20, 20)  # Near-black

    img = Image.new('RGB', (width, height), color=bg_color)
    draw = ImageDraw.Draw(img)

    # Draw text
    y_position = padding
    for line in lines:
        draw.text((30, y_position), line, fill=text_color, font=font)
        y_position += line_height

    # Save with specified DPI
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, dpi=(dpi, dpi))

    print(f"+ Generated image: {output_path} ({width}x{height} px)")


def generate_all_test_images():
    """Generate all 5 test images for cases 015-019."""
    output_dir = Path("cliniq/data/gold_standard/images")
    output_dir.mkdir(parents=True, exist_ok=True)

    print("Generating clinical note images...")

    for case_id, note_text in IMAGE_NOTES.items():
        output_path = output_dir / f"{case_id}.png"
        generate_clinical_note_image(note_text, str(output_path))

    print(f"\n+ Generated {len(IMAGE_NOTES)} clinical note images in {output_dir}")


if __name__ == "__main__":
    generate_all_test_images()
