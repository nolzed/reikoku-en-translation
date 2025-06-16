import os
import sys
import argparse
import struct
import json

from pprint import pprint

SECTOR_SIZE = 2048
FILE_ID_COUNTER = 1

SIGNATURES_4 = {
    0x00000041  : "tmd",
    0x00000042  : "pmd",
    0x00000050  : "hmd",
    0x56414270  : "vhb",   # b'pBAV'
    0x53455170  : "seq",   # b'pQES'
    b'VAGp'     : "vag",
    
    0x0C114353  : "pocket" #b'SC' PocketStation
    
    #0x08002100  : "lz"
    #0x000003FC  : "0x3FC",
    #0x00000040  : "0x40"
}

SIGNATURES_2 = {
    0x000A : "pcx",
    0x0010 : "tim",
    0x0011 : "clt",
    0x0012 : "pxl",
    0x0021 : "anm",
    0x0022 : "cel",
    0x0023 : "bgd",
    0x0024 : "tsq",
    0x0050 : "tod",
}

def check_tim(data: bytes) -> bool:
    """
    Checks whether the data is a valid TIM image.
    """
    try:
        if len(data) < 20:
            return False  # not enough data even for a header

        # TIM Title: magic (4), img_type (4), offset (4), pox, poy, palette_colors, nb_palettes
        magic, img_type, offset = struct.unpack_from('<III', data, 0)

        if magic != 0x10:
            return False

        # Check for valid image types
        if img_type not in (0x02, 0x08, 0x09):
            return False

        # Check that the offset is within the limits of the data
        if offset + 16 + 4 > len(data):  # need at least 4 bytes after offset + 16
            return False

        # Attempting to read dimensions
        width_word, height = struct.unpack_from('<HH', data, offset + 16)

        # Basic size check
        if width_word == 0 or height == 0 or height > 4096:
            return False

        return True
    except:
        return False
        
def check_archive(data):
    
    if len(data) < 8:
        return False
        
    segments = struct.unpack_from('<I', data, 0)[0]
    
    # Must have at least one segment
    if segments < 1 or len(data) < (segments + 1) * 4 or segments > 10000 or len(data) < (segments + 3) * 4:
        return False
    
    length = len(data)
    sorted_archive = True
    
    offsets = []
    for i in range(1, segments+1):
        try:
            next_offset = struct.unpack_from('<I', data, i * 4)[0]
        except struct.error:
            return False
        if sorted_archive and offsets and offsets[-1] > next_offset:
            sorted_archive = False
        if next_offset < (segments+1)*4:
            return False
        if next_offset > length:
            return False
        offsets.append(next_offset)
        
    sectored = offsets[0] == SECTOR_SIZE
    
    if sectored:
        if struct.unpack_from('<I', data, (segments+2)*4)[0] != 0:
            return False
    else:
        min_offset = offsets[0] if sorted_archive else min(offsets)
        if min_offset != (segments+2)*4 and min_offset+4 != (segments+2)*4:
            return False
    
    return True
    

def align_4(n):
    """Rounding to the nearest higher multiple of 4"""
    return (n + 3) & ~3
    
 
def align_sector(n):
    """Round up to the nearest sector"""
    return (n + SECTOR_SIZE - 1) // SECTOR_SIZE * SECTOR_SIZE

def check_tab_packed(data):
    return check_packed(data[4:]) and struct.unpack_from('<I', data, 0)[0] == 0
    
def check_packed(data):
    if len(data) < 8:
        return False

    def is_reasonable_length(length, remaining):
        return 0 < length <= remaining and length < 10_000_000

    offset = 0
    data = data[offset:]
    original_offset = len(data)

    local_offset = 0
    block_count = 0

    while len(data) >= 4:
        length = struct.unpack_from('<I', data, 0)[0]

        if length == 0:
            if original_offset - offset > 0:
                # Allow one “null” block at the end if enough data is available
                break
            else:
                return False

        if not is_reasonable_length(length, len(data) - 4):
            return False

        aligned = align_4(length)
        block_size = aligned + 4  # +4 bytes per header

        if block_size > len(data):
            return False

        data = data[block_size:]
        local_offset += block_size
        block_count += 1

    # Completion condition: at least one block and the balance does not exceed a sector
    return block_count > 0 and local_offset + len(data) == original_offset
 
    
def handle_packed(entry, data):
    global FILE_ID_COUNTER
    files=[]
    
    tabed = check_tab_packed(data)
    if tabed:
        offset = 4
    else:
        offset = 0
    
    last_tabed = False
    data = data[offset:]
    original_offset = len(data)
        
    while len(data) >= 4:
        length = struct.unpack_from('<I', data, 0)[0]

        if length == 0:
            if original_offset - offset > 4 and any(b != 0 for b in data[4:4+original_offset - offset - (len(files) * 4)]):
                offset += 4
                data = data[4:]
                length = struct.unpack_from('<I', data, 0)[0]
                last_tabed = True
            else:
                break
                
        if len(data) < length:
            print(f"WARNING: Not enough data for declared length ({length})")
            break
        
        aligned_length = align_4(length)
        signature = find_signature(data[4:4+aligned_length], True)
        
        if files and signature == "file" and files[-1]["type"] == "vhb":
            signature = "vhb_part"
            
        file = {
            "id": FILE_ID_COUNTER,
            "type": signature,
            "offset" : offset + 4,
            "length": length,
        }
        
        FILE_ID_COUNTER += 1

        if SIGN_HANDLERS.get(signature, False):
            file = SIGN_HANDLERS[signature](file, data[4:4+aligned_length])
        
        files.append(file)
        data = data[aligned_length + 4:]  # cut the processed part
        offset += aligned_length + 4
    
    entry["tabed"] = tabed
    entry["last_tabed"] = last_tabed
    entry["packed_ok"] = len(data) - offset < SECTOR_SIZE
    entry["files"] = files
    return entry


import bisect

def handle_archive(entry, data):
    global FILE_ID_COUNTER
    files=[]
    out_offset = 0
    
    sectored = struct.unpack_from('<I', data, 4)[0] == SECTOR_SIZE

    segments = struct.unpack_from('<I', data, 0)[0]
    sorted_archiev = True
    offsets = []
    
    for i in range(1, segments+1):
        next_offset = struct.unpack_from('<I', data, i * 4)[0]
        if sorted_archiev and offsets and next_offset < offsets[-1]:
            sorted_archiev = False
        offsets.append(next_offset)
    
    sorted_offsets = offsets if sorted_archiev else sorted(set(offsets + [len(data)]))
    
    if sectored:
        archive_length = True
    else:
        archive_length = offsets[0] == (segments+2)*4
    
    for i, offset in enumerate(offsets):
        
        idx = bisect.bisect_right(sorted_offsets, offset)
        if idx < len(sorted_offsets):
            length = sorted_offsets[idx] - offset
        elif archive_length:
            length = struct.unpack_from('<I', data, (segments+1)*4)[0] - offset
        else:
            length = len(data) - offset
            
        file_data = data[offset:offset+length]
        
        signature = find_signature(file_data, True)
        
        if files and signature == "file" and files[-1]["type"] == "vhb":
            signature = "vhb_part"
            
        file = {
            "id": FILE_ID_COUNTER,
            "type": signature,
            "offset" : offset,
            "length": length,
        }
        
        out_offset += offset
        FILE_ID_COUNTER += 1
        
        if SIGN_HANDLERS.get(signature, False):
            file = SIGN_HANDLERS[signature](file, file_data)
        
        files.append(file)
        
    entry["segments"] = segments
    entry["sectored"] = sectored
    entry["sorted"] = sorted_archiev
    entry["archive_ok"] = len(data) - out_offset < SECTOR_SIZE
    entry["archive_length"] = archive_length
    entry["files"] = files
    return entry
 
def check_map(data):
    if len(data) < 24:
        return
        
    if struct.unpack_from('<I', data, 0)[0] == 0:
        return False
        
    x1, x2 = struct.unpack_from('<HH', data, 4)
    if x1 == 0 or x2 == 0 or x1 != x2:
        return False
        
    offset_1, offset_2, offset_3, offset_4  = struct.unpack_from('<IIII', data, 8)
    if offset_1 != 0x18:
        return False
        
    if not (offset_1 < offset_2 < offset_3 < offset_4 < len(data)):
        return False
    
    return True

def handle_map(entry, data):
    global FILE_ID_COUNTER
    header = struct.unpack_from('<Q', data, 0)[0]
    offsets = struct.unpack_from('<IIII', data, 8)
    
    files = []
    for i, offset in enumerate(offsets):
        if i+1 < len(offsets):
            length = offsets[i+1] - offset
        else:
            length = len(data) - offset
        file_data = data[offset:offset+length]
        
        signature = find_signature(file_data)
        file = {
            "id": FILE_ID_COUNTER,
            "type": signature,
            "offset" : offset,
            "length": length,
        }
        
        FILE_ID_COUNTER += 1
        
        if SIGN_HANDLERS.get(signature, False):
            file = SIGN_HANDLERS[signature](file, file_data)
            
        files.append(file)
    
    entry["map_header"] = header
    entry["files"] = files
    return entry

def check_tilemap(data):
    length = len(data)
    tilemap_size = struct.unpack_from('<I', data, 0)[0]
    if tilemap_size <= 0 or tilemap_size + 4 != length:
        return False
    
    tilemap_header = struct.unpack_from('<IIIII', data, 4)
    zero_num = 0
    for header in tilemap_header:
        if header == 0:
            zero_num += 1
        if header >= tilemap_size:
            return False
    
    if zero_num != len(tilemap_header) and zero_num != 0:
        return False
    
    return True

def check_text_table(data):
    if len(data) < 12:
        return False
        
    file_size = struct.unpack_from('<I', data, 0)[0]
    if file_size <= 0 or file_size > len(data):
        return False
    
    table_size = struct.unpack_from('<I', data, 4)[0]
    
    if table_size % 4 != 0:
        return False
 
    offsets = []
    for i in range(table_size//4):
        offset = struct.unpack_from('<I', data, 8 + 4*i)[0]
        if offset == 0 or offset < table_size:
            return False
        if offsets and offset < offsets[-1]:
            return False
        offsets.append(offset)
    
    if not offsets or offsets[0] != table_size:
        return False
    
    return True

def check_dialog(data):
    offset = 0
    
    first_part_size = struct.unpack_from('<I', data, offset)[0]
    offset += 4
    
    if first_part_size <= 0 or first_part_size > len(data):
        return False
    
    offset_1 = align_4(struct.unpack_from('<I', data, offset)[0] * 2)
    offset += 4
    
    if offset_1 <= 0 or offset_1 > first_part_size:
        return False
        
    for i in range(offset_1//4):
        if struct.unpack_from('<I', data, offset+(4*i) )[0] == 0:
            return False
    
    offset_2 = align_4(struct.unpack_from('<I', data, offset + offset_1)[0] * 2)
    offset += 4
    
    if offset_2 <= 0 or offset_2 + offset_1 > first_part_size:
        return False
    
    if not check_text_table(data[offset + offset_1 + offset_2:]):
        return False
        
    offset_3 = struct.unpack_from('<I', data, offset + offset_1 + offset_2)[0]
    offset += 4
        
    if offset_3 <= 0 or offset_3 + offset_2 + offset_1 > first_part_size:
        return False
    
    return (offset + offset_3 + offset_2 + offset_1) - first_part_size <= 4

def handle_dialog(entry, data):
    return

def check_scenario(data):
    sign = struct.unpack_from('<I', data, 0)[0]
    if sign <= 0:
        return False
    
    offset_1 = struct.unpack_from('<I', data, 4)[0]
    if offset_1 <= 0 or offset_1 > len(data):
        return False
        
    offset_2 = align_4(struct.unpack_from('<I', data, 8)[0] * 2)
    if offset_2 <= 0 or offset_2 + offset_1 > len(data):
        return False
    
    if not check_text_table(data[4 + 8 + offset_2:]):
        return False
        
    offset_3 = struct.unpack_from('<I', data, 4 + 8 + offset_2)[0]
    if offset_3 <= 0 or offset_3 + offset_2 > len(data):
        return False
    
    return 8 + offset_3 + 4 + offset_2 + 4 == len(data)
    

def check_database(data):
    offsets = []
    for i in range(5):
        offset = struct.unpack_from('<I', data, 4*i)[0]
        if offset == 0 or offset > len(data):
            return False
        if offsets and offset < offsets[-1]:
            return False
        offsets.append(offset)
    
    if offsets[0] != 0x14:
        return False
    
    if sum(offsets) < len(data):
        return False
        
    return True
 
def check_model(data):
    vertex_num = struct.unpack_from('<I', data, 0)[0]
    if vertex_num == 0 or vertex_num * 8 >= len(data):
        return False
        
    primitive_num = struct.unpack_from('<I', data, 4 + vertex_num*8)[0]
    if primitive_num == 0 or vertex_num * 8 >= len(data):
        return False
    
    return True
 
def find_signature(data, skip_packed=False):
    """
    Search for signatures or file types by file structure
    """
    
    if len(data) < 8:
        return "file"
    
    if struct.unpack_from('<I', data, 4)[0] == 0x08002100:
        return "lz"
    
    if check_database(data):
        return "database" 
        
    if check_scenario(data):
        return "scenario"
    
    if check_dialog(data):
        return "dialog"
        
    if check_tilemap(data):
        return "tilemap"
    
    if check_tim(data):
        return "tim"
    
    if check_map(data):
        return "map"
    
    if check_archive(data):
        return "archive"
        
    if not skip_packed and (check_packed(data) or check_tab_packed(data)):
        return "packed"
    
    if check_model(data):
        return "model"
        
    signature_0 = struct.unpack_from('<I', data, 0)[0]
    if SIGNATURES_4.get(signature_0, False):
        return SIGNATURES_4[signature_0]

    return "file"
    
SIGN_HANDLERS = {
    "packed" : handle_packed,
    "archive" : handle_archive,
    "map" : handle_map,
    #"dialog" : handle_dialog,
}

TYPE_WITH_FILES = {"archive", "packed", "map", "dialog"}
    
def generate_spirit_struct(data, sectors):
    global FILE_ID_COUNTER
    files = []
    
    for sector in sectors:

        print("\nSector_count:", sector["sector"], f" | Sector_size: {sector["size"]}")
        offset = sector["sector"] * SECTOR_SIZE
        entry_data = data[offset:offset+sector["size"]]
        
        if sector["size"] > 0:
            signature = find_signature(entry_data)
        else:
            signature = "Empty"
       
        entry = {
            "section": sector["section"],
            "id": FILE_ID_COUNTER,
            "type": signature,
            "offset": offset,
            "length": sector["size"],
            "spirit_sector": sector["sector"],
            "cd_sector": offset // SECTOR_SIZE + 245
        }
       
        FILE_ID_COUNTER += 1
        
        if SIGN_HANDLERS.get(signature, False):
            entry = SIGN_HANDLERS[signature](entry, entry_data)
            
        files.append(entry)
        
        #if FILE_ID_COUNTER > 1355:
        #    break
        
    return files
    
def get_file_format(entry):
    file_format = entry["type"]
    #if file_format == "lz":
    #    file_format = entry["lz_type"]
    if file_format == "file":
        return ".bin"
    if file_format == "archive":
        return ".archive"
    if file_format == "packed":
        return ".packed"
    if file_format == "map":
        return ".map"
    return "." + file_format

def save_file(output_dir, file, data):
    """
    Saves a single file to the specified path.
    """
    file_name = f"file_{file['id']}" + get_file_format(file)
    file_path = os.path.join(output_dir, file_name)
    with open(file_path, 'wb') as out_file:
        out_file.write(data)

def unpack_files(entry, data, output_dir):
    """
    Extracts entry and attached files (archives/packages) recursively.
    """
    entry_dir = os.path.join(output_dir, f"{entry['type']}_{entry['id']}")
    os.makedirs(entry_dir, exist_ok=True)

    for file in entry.get("files", []):
        file_data = data[file["offset"]:file["offset"] + file["length"]]
        if file["type"] in TYPE_WITH_FILES and file.get("files"):
            unpack_files(file, file_data, entry_dir)
        else:
            save_file(entry_dir, file, file_data)

def unpack_spirit(data, output_dir, sectors, structure=None):
    if structure is None:
        structure = generate_spirit_struct(data, sectors)
        with open(os.path.join(output_dir, ".structure.json"), 'w', encoding='utf-8') as out:
            json.dump(structure, out, indent=2, ensure_ascii=False)
    #return
    for entry in structure:
        chunk = data[entry["offset"]:entry["offset"] + entry["length"]]

        if entry["type"] in TYPE_WITH_FILES and entry.get("files"):
            unpack_files(entry, chunk, output_dir)
        else:
            save_file(output_dir, entry, chunk)

    print(f"[+] Unpacked {len(structure)} sectors to '{output_dir}'")

SECTORS_OFFSET = 0x50D80
SECTORS_NUM = 1864//8

def load_sectors(file):
    sectors = []
    empty = 0
    section = 0
    with open(file, 'rb') as f:
        f.seek(SECTORS_OFFSET)
        
        for i in range(SECTORS_NUM):
            chunk = f.read(8)
            if len(chunk) < 8:
                break  # end of file

            sector, size = struct.unpack('<II', chunk)  # little-endian

            if sector == 0 and size == 0:
                sectors.append({
                    'sector': 0,
                    'size': 0,
                    'section': section
                })
                empty += 1
            else:
                if empty >= 2:
                    section += 1
                    
                sectors.append({
                    'sector': sector,
                    'size': size,
                    'section': section
                })
                empty = 0

    return sectors


# ----- Main -----
def main():
    parser = argparse.ArgumentParser(
        description="Unpack spirit.dat archive"
    )
    parser.add_argument("file", help="Input spirit file")
    parser.add_argument("outdir", help="Directory to write files")
    parser.add_argument("slpm", help="SLPM file to read spirit sectors")
    args = parser.parse_args()

    with open(args.file, 'rb') as f1:
        data = f1.read()

    os.makedirs(args.outdir, exist_ok=True)
    
    sectors = load_sectors(args.slpm)
    unpack_spirit(data, args.outdir, sectors)
    
if __name__ == '__main__':
    main()