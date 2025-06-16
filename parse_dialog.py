import struct, argparse, json

from unpack_spirit import align_4
from font_mapper import FontMapper

def parse_dialog_text(text_bytes, font_map: FontMapper):
    i = 0
    output = []

    def read_next():
        nonlocal i
        if i < len(text_bytes):
            val = text_bytes[i]
            i += 1
            return val
        return None
    
    def is_next():
        nonlocal i
        if i < len(text_bytes):
            return text_bytes[i]
        return None
    
    while i < len(text_bytes):
        byte = read_next()
        if byte is None:
            break

        # Control characters
        if byte == 0x00:
            output.append("[END]")
            remaining = text_bytes[i:]
            if remaining:
                hex_str = ''.join(f'{b:02X}' for b in remaining)
                output.append(f"[RAW:{hex_str}]")
            break

        elif 0x01 <= byte <= 0x0A and is_next() is not None:
            high = byte
            low = read_next()
            code = (high << 8) | (low if low is not None else 0)
            output.append(font_map.get_char(code))

        elif byte == 0x0B:
            output.append("[WAIT]")

        elif byte == 0x0C and is_next() is not None:
            func_id = read_next()
            output.append(f"[FUNC:{func_id}]")

        elif byte == 0x0D:
            output.append("\n")

        elif byte == 0x0E:
            output.append("[SCROLL]")

        elif byte == 0x0F and is_next() is not None:
            subcmd = read_next()
            if subcmd == 0x00:
                delay = read_next()
                output.append(f"[DELAY:{delay}]")
            elif subcmd == 0x01:
                output.append("[WAIT_PRESS]")
                i -= 2
            elif subcmd == 0x02:
                output.append("[CLEAR]")
            elif subcmd == 0x04:
                arg1 = read_next()
                arg2 = read_next()
                if arg1 is not None and arg2 is not None:
                    addr = (arg2 << 8) | arg1
                    output.append(f"[FUNC_CALL:0x{addr:04X}]")
                else:
                    output.append("[FUNC_CALL:??]")
            else:
                output.append(f"[PAUSE:UNKNOWN:{subcmd}]")

        #elif byte == 0x25:
        #    print(text_bytes, output)
        #    output.append(get_ascii_char(byte, TABLE))
        #    output.append(get_ascii_char(read_next(), TABLE))

        elif 0x20 <= byte:
            char = font_map.get_ascii_char(byte)
            output.append(char if char else f"[UNK1:{byte:02X}]")
        else:
            output.append(f"[UNK2:{byte:02X}]")
            
    return ''.join(output)


def parse_dialog(data, font_map: FontMapper):
    offset = 0
    
    main_size = struct.unpack_from('<I', data, offset)[0]
    offset += 4
    
    entries_count_1 = struct.unpack_from('<I', data, offset)[0]
    entries_count_1 += entries_count_1%2
    offset += 4
    entries_1 = []
    for i in range(entries_count_1):
        entry = struct.unpack_from('<H', data, offset + i*2)[0]
        entries_1.append(entry)
        
    offset += entries_count_1 * 2
    print(f"Block 1 entries: {entries_count_1} | {hex(offset)}")
    
    entries_count_2 = struct.unpack_from('<I', data, offset)[0] 
    entries_count_2 += entries_count_2%2
    offset += 4
    entries_2 = []
    print(entries_count_2)
    for i in range(entries_count_2):
        entry = struct.unpack_from('<H', data, offset + i*2)[0]
        entries_2.append(entry)
        
    offset += entries_count_2 * 2
    print(f"Block 2 entries: {entries_count_2} | {hex(offset)}")
    
    block_3_size = struct.unpack_from('<I', data, offset)[0]
    offset += 4
    
    print(f"Block 3 size: {block_3_size} | {hex(offset)}")
    
    table_size = struct.unpack_from('<I', data, offset)[0]
    
    table_offsets_count = (table_size-4)//4
    table_offsets = []
    for i in range(table_offsets_count):
        table_offset = struct.unpack_from('<I', data, offset + 4 + i*4)[0]
        table_offsets.append(table_offset)
    
    print(f"Block 3 table_size: {table_size} | {hex(offset)}")
    
    table_entries = []
    table_raw_entries = []
    
    for i in range(len(table_offsets)):
        if i+1 < len(table_offsets):
            size = table_offsets[i+1] - table_offsets[i]
        else:
            size = block_3_size - table_offsets[i]
        entry_offset = offset + table_offsets[i]
        table_entry = data[entry_offset:entry_offset+size]
        table_raw_entries.append(table_entry.hex())
        if struct.unpack_from("<H", table_entry, 0)[0] * 2 + 2 == len(table_entry):
            table_entries.append(f"[RAW:{table_entry.hex()}]")
        else:
            table_entries.append(parse_dialog_text(table_entry, font_map))
        
    offset += block_3_size
    
    print(f"Block 3 table_entries: {len(table_entries)} | {hex(offset)}")
    
    return {
        "main_size": main_size,
        "block_1": {
            "count": entries_count_1,
            "entries": entries_1
        },
        "block_2": {
            "count": entries_count_2,
            "entries": entries_2
        },
        "block_3": {
            "size" : block_3_size,
            "table_size" : table_size,
            "table_offsets": table_offsets,
            "table_entries": table_entries,
            "raw_table_entries": table_raw_entries
        },
        "add_block": data[offset:].hex()
    }


def main():
    parser = argparse.ArgumentParser(
        description="Parse dialog file"
    )
    parser.add_argument("file", help="Input dialog file")
   
    parser.add_argument("dialog_data_out", help="Path to write parsed json data")
    parser.add_argument("font_table", help="Path to font-table.txt", default="./font/ascii-table.bin")
    parser.add_argument("ascii_table", help="Path to ascii-table.bin", default="./font/font-table.txt")
    args = parser.parse_args()
    
    with open(args.file, 'rb') as f1:
        data = f1.read()

    dialog_data = parse_dialog(data, FontMapper(args.font_table, args.ascii_table))
    
    with open(args.dialog_data_out, 'w', encoding='utf-8') as out:
        json.dump(dialog_data, out, indent=2, ensure_ascii=False)
    
    print("[+] Json dialog_data extracted to:", args.dialog_data_out)
    
if __name__ == '__main__':
    main()