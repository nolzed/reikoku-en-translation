#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import struct
from pathlib import Path

def load_ascii_table(path):
    data = Path(path).read_bytes()
    entries = len(data) // 2
    return [struct.unpack_from('<H', data, i * 2)[0] for i in range(entries)]

def load_font_table(path):
    raw = Path(path).read_text(encoding='utf-8', errors='ignore')
    raw = raw.replace('\r', '').replace('\n', '')
    table = {}
    for i, ch in enumerate(raw):
        code = (i + 0x100) & 0xFFF
        table[code] = ch
    return table

def convert_ascii_table(ascii_table, font_table, width=16):
    result_lines = []
    for i in range(0, len(ascii_table), width):
        line = ''
        for code in ascii_table[i:i+width]:
            if code == 0x0000:
                line += ' '
            else:
                line += font_table.get(code, '?')  # '?' for unknown mappings
        result_lines.append(line)
    return result_lines

def main():
    ascii_bin_path = "./font/ascii-table.bin"
    font_table_path = "./font/font-table.txt"
    output_path = "ascii-table.txt"

    ascii_table = load_ascii_table(ascii_bin_path)
    font_table = load_font_table(font_table_path)
    
    lines = convert_ascii_table(ascii_table, font_table, width=16)

    with open(output_path, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")

    print(f"[+] ASCII table dumped to {output_path}")

if __name__ == "__main__":
    main()
