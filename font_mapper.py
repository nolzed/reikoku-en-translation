#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import sys
import struct
from pathlib import Path
from collections import defaultdict

class FontMapper:
    """
    A class for loading and working with ASCII and font tables.
    Allows you to convert characters to codes and back.
    """
    def __init__(self, ascii_bin_path: str, font_table_path: str):
        self.ascii_table = self._load_ascii_table(ascii_bin_path)
        self.reverse_ascii_table = {v: k for k, v in self.ascii_table.items()}
        self.font_table = self._load_font_table(font_table_path)
        self.reverse_font_table = {v: k for k, v in self.font_table.items()}

    def _load_ascii_table(self, path: str) -> dict:
        data = Path(path).read_bytes()
        table = {}
        base_code = 0x20
        entries = len(data) // 2
        for i in range(entries):
            code = base_code + i
            value = struct.unpack_from('<H', data, i * 2)[0]
            table[code] = value
        return table

    def _load_font_table(self, path: str) -> dict:
        raw = Path(path).read_text(encoding='utf-8', errors='ignore')
        raw = raw.replace('\r', '').replace('\n', '')
        if not raw:
            raise ValueError("font-table.txt Empty or unread.")
        table = {}
        for i, ch in enumerate(raw):
            code = (i + 0x100) & 0xFFF
            table[code] = ch
        return table

    def get_ascii_code(self, char: str) -> int:
        font_code = self.reverse_font_table.get(char)
        return self.reverse_ascii_table.get(font_code) if font_code is not None else None

    def get_ascii_char(self, ascii_code: int) -> str:
        font_code = self.ascii_table.get(ascii_code)
        return self.font_table.get(font_code) if font_code and font_code != 0x00 else None

    def get_code(self, char: str) -> int:
        return self.reverse_font_table.get(char)

    def get_char(self, code: int) -> str:
        return self.font_table.get(code)


def main():
    parser = argparse.ArgumentParser(
        description="Font table mapper and debugger (code <-> font/ascii)")
    parser.add_argument("--ascii-table", default="./font/ascii-table.bin",
                        help="Path to ascii-table.bin")
    parser.add_argument("--font-table", default="./font/font-table.txt",
                        help="Path to font-table.txt")

    subparsers = parser.add_subparsers(dest="command", required=True,
                                       help="Action to perform")

    # info-chars: multiple characters
    p_chars = subparsers.add_parser("info-chars",
                                    help="Inspect multiple characters (font and ASCII)")
    p_chars.add_argument("chars", nargs='+', help="List of characters to inspect")

    # info-code: multiple codes
    p_code = subparsers.add_parser("info-code", help="Inspect font and/or ASCII codes")
    p_code.add_argument("--font", dest="font_codes", nargs='+',
                        help="Font-table codes (hex, e.g. 0x0100)")
    p_code.add_argument("--ascii", dest="ascii_codes", nargs='+',
                        help="ASCII codes (hex, e.g. 0x20)")
    
    p_dup = subparsers.add_parser("find-duplicates", help="Find duplicate characters in font-table")
    
    args = parser.parse_args()
    fm = FontMapper(args.ascii_table, args.font_table)

    def calc_position(index: int, cols: int = 18, rows: int = 19):
        table_idx = index // (cols * rows)
        local_index = index % (cols * rows)
        row = local_index // cols
        col = local_index % cols
        return table_idx, row, col

    def show_info_for_char(ch: str):
        print(f"Character: '{ch}'")
        
        # Font info
        font_code = fm.get_code(ch)
        if font_code is not None:
            idx = list(fm.font_table.keys()).index(font_code)
            table, row, col = calc_position(idx)
            print(f"  Font code: 0x{font_code:03X} (table {table+1}, row {row+1}, col {col+1})")
        else:
            print("  Not found in font-table")
            
        # ASCII info
        ascii_code = fm.get_ascii_code(ch)
        if ascii_code is not None:
            pos = ascii_code - 0x20
            table, row, col = calc_position(pos)
            print(f"  ASCII code: 0x{ascii_code:02X} (table {table}, row {row}, col {col})")
        else:
            print("  Not mapped in ascii-table")
        print()

    if args.command == "info-chars":
        for c in args.chars:
            show_info_for_char(c)

    elif args.command == "info-code":
        # Process font codes
        if args.font_codes:
            for code_str in args.font_codes:
                try:
                    fc = int(code_str, 16)
                except ValueError:
                    print(f"Invalid font code '{code_str}'. Use hex format, e.g. 0x0100", file=sys.stderr)
                    continue
                ch = fm.get_char(fc)
                print(f"Font code 0x{fc:03X} =>")
                if ch is None:
                    print("  No character at this font code")
                    print()
                else:
                    show_info_for_char(ch)
        # Process ASCII codes
        if args.ascii_codes:
            for code_str in args.ascii_codes:
                try:
                    ac = int(code_str, 16)
                except ValueError:
                    print(f"Invalid ASCII code '{code_str}'. Use hex format, e.g. 0x20", file=sys.stderr)
                    continue
                ch = fm.get_ascii_char(ac)
                print(f"ASCII code 0x{ac:02X} =>")
                if ch is None:
                    print("  No character at this ASCII code")
                    print()
                else:
                    show_info_for_char(ch)
        
    elif args.command == "find-duplicates":
        char_to_codes = defaultdict(list)
        for code, char in fm.font_table.items():
            char_to_codes[char].append(code)

        duplicates = {ch: codes for ch, codes in char_to_codes.items() if len(codes) > 1}

        if not duplicates:
            print("No duplicates found in font-table.")
        else:
            print("Duplicate characters in font-table:")
            for ch, codes in duplicates.items():
                print(f"Character '{ch}' appears at:")
                for code in codes:
                    idx = list(fm.font_table.keys()).index(code)
                    table, row, col = calc_position(idx)
                    print(f"  Code 0x{code:03X} (table {table}, row {row}, col {col})")
                print()
            print("Duplicates:", len(duplicates))
                
if __name__ == "__main__":
    main()
