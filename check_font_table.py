#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import sys
from pathlib import Path
from collections import defaultdict
from font_mapper import FontMapper
from PIL import Image


def main():
    parser = argparse.ArgumentParser(
        description="Check font-table.txt for duplicates and build images")
    parser.add_argument("--ascii-table", default="./font/ascii-table.bin",
                        help="Path to ascii-table.bin")
    parser.add_argument("--font-table", default="./font/font-table.txt",
                        help="Path to font-table.txt")
    parser.add_argument("--font-img-dir", default="./font/png",
                        help="Path to font image tables directory")
    parser.add_argument("--output-dir", default="./duplicates",
                        help="Directory to save duplicate images")
    parser.add_argument("--rows", type=int, default=19,
                        help="Number of rows in the font table")
    parser.add_argument("--cols", type=int, default=18,
                        help="Number of columns in the font table")
    args = parser.parse_args()

    fm = FontMapper(args.ascii_table, args.font_table)

    # Compute table position for a flat index
    def calc_position(index: int, cols: int, rows: int):
        table_idx = index // (cols * rows)
        local_index = index % (cols * rows)
        row = local_index // cols
        col = local_index % cols
        return table_idx, row, col

    # Collect duplicates
    char_to_codes = defaultdict(list)
    for code, char in fm.font_table.items():
        char_to_codes[char].append(code)
    duplicates = {ch: codes for ch, codes in char_to_codes.items() if len(codes) > 1}

    if not duplicates:
        print("No duplicates found in font-table.")
        return

    # Prepare output directory
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Found {len(duplicates)} duplicate character(s). Building images...")
    DEF_FONT_SIZE = 256
    
    for ch, codes in duplicates.items():
        char_imgs = []
        for code in codes:
            # locate index in font table
            idx = list(fm.font_table.keys()).index(code)
            table_idx, row, col = calc_position(idx, args.cols, args.rows)
            table_num = table_idx + 1
            img_path = Path(args.font_img_dir) / f"table-{table_num}.png"
            if not img_path.exists():
                print(f"Warning: image for table {table_num} not found at {img_path}", file=sys.stderr)
                continue

            # load and crop
            table_img = Image.open(img_path)
            img_w, img_h = table_img.size

            # dynamic cell dimensions: floor division handles any image size; table starts at top-left
            cell_w = DEF_FONT_SIZE // args.cols * (img_w // DEF_FONT_SIZE)
            cell_h = DEF_FONT_SIZE // args.rows * (img_h // DEF_FONT_SIZE)

            # top-left corner of the character cell
            x0 = col * cell_w
            y0 = row * cell_h

            # Crop full cell, not just centered char
            crop = table_img.crop((x0, y0, x0 + cell_w, y0 + cell_h))
            char_imgs.append(crop)

            #print(f"Cropped {img_w}, {img_h} {img_path}: table {table_num}, row {row}, col {col}, {cell_w}x{cell_h} box=({x0},{y0},{x0+cell_w},{y0+cell_h})")

        if not char_imgs:
            continue

        # compose row image
        total_w = cell_w * len(char_imgs)
        combined = Image.new('RGBA', (total_w, cell_h), (255, 255, 255, 0))

        x_off = 0
        for im in char_imgs:
            combined.paste(im, (x_off, 0))
            x_off += cell_w

        # safe filename
        fname = f"dup_{ord(ch):04X}_{ch}.png"
        fname = ''.join(c if c.isalnum() or c in ('_', '.') else '_' for c in fname)
        combined.save(out_dir / fname)
        print(f"Saved duplicate image for '{ch}' to {out_dir / fname}")

if __name__ == "__main__":
    main()
