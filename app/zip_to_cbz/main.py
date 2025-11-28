#!/usr/bin/env python3
"""
Convert ZIP files to CBZ format with sequential numbering.

This script:
1. Extracts ZIP files from convert_cbz/data/src/ to convert_cbz/data/temp/
2. Renames image files to 3-digit sequential numbers (001.jpg, 002.jpg, etc.)
3. Creates CBZ files (ZIP with .cbz extension) in convert_cbz/data/dest/
4. Uses the extracted directory name as the CBZ filename
"""

import os
import shutil
import zipfile
from pathlib import Path
from typing import List


def get_image_files(directory: Path) -> tuple[List[Path], Path]:
    """
    Get all image files from directory, sorted alphabetically.

    Args:
        directory: Directory to search for image files

    Returns:
        Tuple of (list of image file paths sorted alphabetically, directory containing images)
    """
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
    image_files = []

    for file_path in directory.rglob('*'):
        if file_path.is_file() and file_path.suffix.lower() in image_extensions:
            image_files.append(file_path)

    sorted_files = sorted(image_files)

    if sorted_files:
        image_dir = sorted_files[0].parent
    else:
        image_dir = directory

    return sorted_files, image_dir


def extract_zip(zip_path: Path, temp_dir: Path) -> Path:
    """
    Extract ZIP file to temporary directory.

    Args:
        zip_path: Path to ZIP file
        temp_dir: Temporary directory for extraction

    Returns:
        Path to the extracted directory
    """
    extract_path = temp_dir / zip_path.stem

    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_path)

    return extract_path


def rename_images_sequentially(image_files: List[Path], target_dir: Path) -> List[Path]:
    """
    Rename image files to 3-digit sequential numbers.

    Args:
        image_files: List of image file paths to rename
        target_dir: Directory where renamed files will be placed

    Returns:
        List of renamed file paths
    """
    renamed_files = []

    for index, image_file in enumerate(image_files, start=1):
        extension = image_file.suffix
        new_name = f"{index:03d}{extension}"
        new_path = target_dir / new_name

        shutil.copy2(image_file, new_path)
        renamed_files.append(new_path)

    return renamed_files


def create_cbz(source_dir: Path, cbz_name: str, dest_dir: Path) -> Path:
    """
    Create CBZ file from directory.

    Args:
        source_dir: Directory containing numbered image files
        cbz_name: Name for the CBZ file (without extension)
        dest_dir: Destination directory for CBZ file

    Returns:
        Path to created CBZ file
    """
    cbz_path = dest_dir / f"{cbz_name}.cbz"

    with zipfile.ZipFile(cbz_path, 'w', zipfile.ZIP_DEFLATED) as cbz_file:
        for file_path in sorted(source_dir.iterdir()):
            if file_path.is_file():
                cbz_file.write(file_path, file_path.name)

    return cbz_path


def process_zip_file(zip_path: Path, temp_dir: Path, dest_dir: Path) -> None:
    """
    Process a single ZIP file: extract, rename, and create CBZ.

    Args:
        zip_path: Path to ZIP file
        temp_dir: Temporary directory for extraction
        dest_dir: Destination directory for CBZ file
    """
    print(f"Processing: {zip_path.name}")

    extracted_dir = extract_zip(zip_path, temp_dir)
    print(f"  Extracted to: {extracted_dir}")

    image_files, image_dir = get_image_files(extracted_dir)
    print(f"  Found {len(image_files)} image files")

    if not image_files:
        print(f"  Warning: No image files found in {zip_path.name}")
        return

    numbered_dir = temp_dir / f"{zip_path.stem}_numbered"
    numbered_dir.mkdir(exist_ok=True)

    renamed_files = rename_images_sequentially(image_files, numbered_dir)
    print(f"  Renamed {len(renamed_files)} files to sequential numbers")

    cbz_name = image_dir.name
    cbz_path = create_cbz(numbered_dir, cbz_name, dest_dir)
    print(f"  Created: {cbz_path.name}")

    shutil.rmtree(extracted_dir)
    shutil.rmtree(numbered_dir)
    print(f"  Cleaned up temporary files")


def main():
    """Main function to process all ZIP files."""
    script_dir = Path(__file__).parent
    src_dir = script_dir / "data" / "src"
    temp_dir = script_dir / "data" / "temp"
    dest_dir = script_dir / "data" / "dest"

    src_dir.mkdir(parents=True, exist_ok=True)
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Clean up temp directory completely before processing
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir(parents=True, exist_ok=True)

    zip_files = list(src_dir.glob("*.zip"))

    if not zip_files:
        print(f"No ZIP files found in {src_dir}")
        return

    print(f"Found {len(zip_files)} ZIP file(s) to process\n")

    for zip_file in zip_files:
        try:
            process_zip_file(zip_file, temp_dir, dest_dir)
            print()
        except Exception as e:
            print(f"Error processing {zip_file.name}: {e}\n")

    # Clean up temp directory after all processing is complete
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
        print("Cleaned up temp directory")

    print("Processing complete!")


if __name__ == "__main__":
    main()
