import os
import sys
import argparse
import struct
import json

# Dialog Window
FONT_WIDTH_OFFSETS = [0x2349c, 0x2424c, 0xe1c8, 0xeb30, 0x238b0, 0xdd64, 0xed90, 0xe1f0]
FONT_WIDTH = 0x08

WINDOW_COLUMNS_OFFSETS = [0x1e918, 0xFBC8, 0x4E60, 0x1de80, 0x18fb4, 0xa9cc, 0x276d0, 0x18b80] # 0x279D8 (0x11)
WINDOW_COLUMNS = 0x21

WINDOW_FRAME_WIDTH_OFFSET = 0x23014
FRAME_WIDTH_SCRIPT = [0x00521021, 0x00000000]

# Choice Window
CHOICE_X_POS_OFFSET = 0x14128
CHOICE_X_POS_SCRIPT = [0x000310c0, 0x00000000, 0x00000000]

CHOICE_LINE_WIDTH_OFFSET = 0x21c40
CHOICE_LINE_WIDTH_SCRIPT = [0x00141080, 0x001440c0, 0x00000000]

CHOICE_SELECTED_LINE_WIDTH_OFFSET = 0x23924
CHOICE_SELECTED_LINE_WIDTH_SCRIPT = [0x000938c0, 0x00000000, 0x00073c00]


def fix_dialog_font(slpm_file, output_slpm):

    with open(slpm_file, 'rb') as f:
        slpm = bytearray(f.read())
        
    # Fix font width from 0x0e to 0x08
    for offset in FONT_WIDTH_OFFSETS:
        font_width = struct.unpack_from('<B', slpm, offset)[0]
        if font_width != 0x0e:
            raise Exception(f"Wrong font offset: {offset} | {font_width}")
        struct.pack_into('<B', slpm, offset, FONT_WIDTH)
    
    # Fix window columns count from 0x13 to 0x21
    for offset in WINDOW_COLUMNS_OFFSETS:
        columns = struct.unpack_from('<B', slpm, offset)[0]
        if columns != 0x13:
            raise Exception(f"Wrong columns offset: {offset} | {columns}")
        struct.pack_into('<B', slpm, offset, WINDOW_COLUMNS)
    
    # Fix frame width script
    struct.pack_into('<II', slpm, WINDOW_FRAME_WIDTH_OFFSET, *FRAME_WIDTH_SCRIPT)
    
    # Fix choice x offset script
    struct.pack_into('<III', slpm, CHOICE_X_POS_OFFSET, *CHOICE_X_POS_SCRIPT)
    
    # Fix choice line width
    struct.pack_into('<III', slpm, CHOICE_LINE_WIDTH_OFFSET, *CHOICE_LINE_WIDTH_SCRIPT)
    
    # Fix choice selected line width
    struct.pack_into('<III', slpm, CHOICE_SELECTED_LINE_WIDTH_OFFSET, *CHOICE_SELECTED_LINE_WIDTH_SCRIPT)
    
    with open(output_slpm, 'wb') as f:
        f.write(slpm)
        
    print(f"[+] Patched SLPM and wrote to '{output_slpm}'")


def main():
    parser = argparse.ArgumentParser(
        description="Fix for dialog window font in SLPM file"
    )
    parser.add_argument("slpm_file", help="Path to the SLPM_862.74 file")
    parser.add_argument("output_slpm", help="Output path for the patched SLPM_862.74 file")
    args = parser.parse_args()

    fix_dialog_font(args.slpm_file, args.output_slpm)

if __name__ == '__main__':
    main()