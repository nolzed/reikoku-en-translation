import struct
import argparse
import json

from font_mapper import FontMapper
from unpack_spirit import align_4
from pack_dialog import pack_dialog_text, build_dialog, normalize_text, import_from_excel_unescape

def fix_dialog_window(data):
    script_data = data["block_2"]
    
    for i in range(len(script_data["entries"])):

        if script_data["entries"][i:i+4] == [0x00AA, 0x0029, 0x0005, 0x0018]:
            #script_data["entries"][i-1] = param_1  # 0x05
            #script_data["entries"][i-3] = param_2  # 0x00
            #script_data["entries"][i-5] = param_3  # Frame height (rows)
            #script_data["entries"][i-7] = param_4  # Frame width (cols)
            #script_data["entries"][i-9] = param_5  # Frame Y pos
            #script_data["entries"][i-11] = param_6 # Frame X pos
            
            columns = script_data["entries"][i-7]
            if columns == 0x0013:
                fix_columns = 0x0021
            elif columns == 0x000f:
                fix_columns = 0x001a
            else:
                raise Exception(f"Unknown column count: {columns} | {script_data["entries"][i-11:i+4]}")
            data["block_2"]["entries"][i-7] = fix_columns
            
    return data
    
def main():
    parser = argparse.ArgumentParser(description="Pack JSON dialog into binary format")
    parser.add_argument("infile", help="Input JSON file with dialog structure")
    parser.add_argument("outfile", help="Output binary dialog file")
    parser.add_argument("--excel", help="Path to excel text entries", required=False)
    parser.add_argument(
        "--font_table",
        default="./font/font-table.txt",
        help="Path to font-table.txt"
    )
    parser.add_argument(
        "--ascii_table",
        default="./font/ascii-table.bin",
        help="Path to ascii-table.bin"
    )
    args = parser.parse_args()

    # Load JSON
    with open(args.infile, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Load and insert excel entries
    if args.excel:
        data['block_3']['table_entries'] = import_from_excel_unescape(args.excel)
    
    # Fix dialog window scripts
    data = fix_dialog_window(data)
    
    # Build binary
    bin_data = build_dialog(data, FontMapper(args.ascii_table, args.font_table))

    # Write
    with open(args.outfile, 'wb') as f:
        f.write(bin_data)

    print(f"[+] Binary dialog written to: {args.outfile}")


if __name__ == '__main__':
    main()
