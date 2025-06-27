import os
import sys
import argparse
import struct
import json

from unpack_spirit import align_4, align_sector, get_file_format, TYPE_WITH_FILES

def rebuild_packed_data(entry_info, base_source_dir):
    """
    Rebuilds data for a 'packed' or 'tab_packed' entry.
    base_source_dir is the path to the directory containing this packed container's files.
    """
    rebuilt_parts = []
    
    if entry_info["tabed"]:
        rebuilt_parts.append(b'\x00' * 4)
    
    # Construct the specific directory for this packed container's files
    current_container_dir = os.path.join(base_source_dir, f"packed_{entry_info['id']}")

    for i, file_entry in enumerate(entry_info["files"]):
        if i+1 == len(entry_info["files"]) and entry_info["last_tabed"]:
            rebuilt_parts.append(b'\x00' * 4)

        if file_entry["type"] in TYPE_WITH_FILES and file_entry.get("files"):
            # Recursively rebuild nested containers
            rebuilt_nested_data = rebuild_nested_container(file_entry, current_container_dir)
            rebuilt_parts.append(struct.pack('<I', len(rebuilt_nested_data)))
            rebuilt_parts.append(rebuilt_nested_data)
            rebuilt_parts.append(b'\x00' * (align_4(len(rebuilt_nested_data)) - len(rebuilt_nested_data)))
        else:
            file_path = os.path.join(current_container_dir, f"file_{file_entry['id']}{get_file_format(file_entry)}")
            if not os.path.exists(file_path):
                print(f"ERROR: File not found: {file_path}")
                return b"" # Or raise an exception
            with open(file_path, 'rb') as f:
                sub_file_data = f.read()

            rebuilt_parts.append(struct.pack('<I', len(sub_file_data)))
            rebuilt_parts.append(sub_file_data)
            rebuilt_parts.append(b'\x00' * (align_4(len(sub_file_data)) - len(sub_file_data)))
            
    return b''.join(rebuilt_parts)

def rebuild_archive_data(entry_info, base_source_dir):
    """
    Rebuilds data for an 'archive' entry based on its parsed structure.
    """
    header_parts = []
    files_content_parts = []
    
    # Construct the specific directory for this archive container's files
    current_container_dir = os.path.join(base_source_dir, f"archive_{entry_info['id']}")

    # 1. Write the number of segments (first 4 bytes of archive header)
    header_parts.append(struct.pack('<I', entry_info["segments"]))
    
    # List to store the calculated offsets for each file within this archive
    offsets = {}
    
    initial_file_data_offset = 0
    
    if entry_info["sectored"]:
        initial_file_data_offset = 0x800
    else:
        # For non-sectored, the file data starts immediately after the header.
        initial_file_data_offset = 4 + (entry_info["segments"] * 4)
        if entry_info["archive_length"]:
            initial_file_data_offset += 4
    
    sorted_files = sorted(entry_info["files"], key=lambda x: x["offset"])
    
    # current_accumulated_data_size tracks the total size of file data appended so far
    current_accumulated_data_size = 0 
    
    for i, file_entry in enumerate(sorted_files):

        if i != 0 and file_entry["offset"] == sorted_files[i-1]["offset"]:
            offsets[file_entry["id"]] = sorted_files[i-1]["offset"]
            continue
            
        offsets[file_entry["id"]] = initial_file_data_offset + current_accumulated_data_size
        
        rebuilt_sub_data = b""
        if file_entry["type"] in TYPE_WITH_FILES and file_entry.get("files"):
            # Recursively rebuild nested containers.
            rebuilt_sub_data = rebuild_nested_container(file_entry, current_container_dir)
        else:
            # Read the content of a regular file
            file_path = os.path.join(current_container_dir, f"file_{file_entry['id']}{get_file_format(file_entry)}")
            if not os.path.exists(file_path):
                print(f"ERROR: File not found for archive sub-entry ID {file_entry['id']}: {file_path}")
                return b"" # Or raise an exception for critical error
            with open(file_path, 'rb') as f:
                rebuilt_sub_data = f.read()
            
        files_content_parts.append(rebuilt_sub_data)
        if entry_info["sectored"]:
            sector_padding = align_sector(len(rebuilt_sub_data))-len(rebuilt_sub_data)
            if sector_padding:
                files_content_parts.append(b'\x00' * sector_padding)
                current_accumulated_data_size += sector_padding
        
        # Update the accumulated size, including 4-byte padding for the next file
        current_accumulated_data_size += len(rebuilt_sub_data)
        
        # Add padding if the data length is not aligned to 4 bytes
        padding_needed = align_4(len(rebuilt_sub_data)) - len(rebuilt_sub_data)
        if padding_needed > 0:
            files_content_parts.append(b'\x00' * padding_needed)
            current_accumulated_data_size += padding_needed


    # 2. Add offsets to the header parts
    for file in entry_info["files"]:
        header_parts.append(struct.pack('<I', offsets[file["id"]]))
        
    # 3. Add the final length/zero field to the header
    # This is where the 'archive_length' flag from handle_archive becomes important.
    # If archive_length was true, it meant offsets[0] == (segments+2)*4.
    # For sectored archives, it's typically 0.
    if entry_info["archive_length"]:
        # This implies the original archive had its first offset at (segments+2)*4,
        header_parts.append(struct.pack('<I', current_accumulated_data_size + initial_file_data_offset))
    if entry_info["sectored"]:
        header_parts.append(struct.pack('<I', 0))
    
    rebuilt_header = b''.join(header_parts)
    
    # Pad the header to 0x800 if it's a sectored archive and the header is smaller
    if entry_info["sectored"] and len(rebuilt_header) < 0x800:
        rebuilt_header += b'\x00' * (0x800 - len(rebuilt_header))
    
    # Combine the header and the actual file contents
    return rebuilt_header + b''.join(files_content_parts)


def rebuild_map_data(entry_info, base_source_dir):
    """
    Rebuilds data for a 'map' entry.
    base_source_dir is the path to the directory containing this map container's files.
    """
    header_parts = []
    files_content_parts = []
    
    # Construct the specific directory for this map container's files
    current_container_dir = os.path.join(base_source_dir, f"map_{entry_info['id']}")

    header_parts.append(struct.pack('<Q', entry_info["map_header"])) # Map header is 8 bytes
    
    offsets = []
    current_offset_in_map = 0x18 # Fixed initial offset for map data
    
    for file_entry in entry_info["files"]:
        offsets.append(current_offset_in_map)
        
        if file_entry["type"] in TYPE_WITH_FILES and file_entry.get("files"):
            nested_data = rebuild_nested_container(file_entry, current_container_dir)
            files_content_parts.append(nested_data)
            current_offset_in_map += len(nested_data)
        else:
            file_path = os.path.join(current_container_dir, f"file_{file_entry['id']}{get_file_format(file_entry)}")
            if not os.path.exists(file_path):
                print(f"ERROR: File not found: {file_path}")
                return b"" # Or raise an exception
            with open(file_path, 'rb') as f:
                sub_file_data = f.read()
            
            files_content_parts.append(sub_file_data)
            current_offset_in_map += len(sub_file_data)
            
    # Add offsets (4 of them) to header parts
    for offset in offsets:
        header_parts.append(struct.pack('<I', offset))
        
    rebuilt_header = b''.join(header_parts)
    
    # Pad up to the first file's offset if necessary (0x18)
    if len(rebuilt_header) < 0x18:
        rebuilt_header += b'\x00' * (0x18 - len(rebuilt_header))
        
    return rebuilt_header + b''.join(files_content_parts)

def rebuild_nested_container(container_entry, base_source_dir):
    """
    Handles the rebuilding of nested 'packed' or 'archive' containers.
    base_source_dir is the parent directory where this container's specific folder (e.g., 'packed_ID') resides.
    """
    if container_entry["type"] == "packed":
        return rebuild_packed_data(container_entry, base_source_dir)
    elif container_entry["type"] == "archive":
        return rebuild_archive_data(container_entry, base_source_dir)
    elif container_entry["type"] == "map":
        return rebuild_map_data(container_entry, base_source_dir)
    else:
        # If it's not a known container type, assume it's a regular file
        # The file itself should be directly in the base_source_dir
        file_path = os.path.join(base_source_dir, f"file_{container_entry['id']}{get_file_format(container_entry)}")
        if not os.path.exists(file_path):
            print(f"ERROR: Nested regular data file not found: {file_path}")
            return b""
        with open(file_path, 'rb') as f:
            return f.read()

from unpack_spirit import SECTORS_OFFSET, SECTORS_NUM

def repack_spirit(spirit_dir, output_spirit, slpm_file, output_slpm):
    """
    Repacks the spirit.dat file from extracted files and a structure.json.
    """
    with open(os.path.join(spirit_dir, ".structure.json"), 'r', encoding='utf-8') as f:
        structure = json.load(f)

    sector_id_map = {entry["id"]: i for i, entry in enumerate(structure)}
    structure.sort(key=lambda x: x["spirit_sector"])

    repacked_data_parts = []
    repacked_sectors = []

    current_physical_offset = 0

    for entry in structure:
        entry_data = b""
        
        if entry["type"] == "Empty":
            repacked_data_parts.append(entry_data)

            repacked_sectors.append({
                "id": sector_id_map[entry["id"]],
                "sector": 0,
                "size": 0
            })
            continue
            
        if entry["type"] in TYPE_WITH_FILES and entry.get("files"):
            entry_data = rebuild_nested_container(entry, spirit_dir)
            if entry["type"] == "packed":
                entry_data += b'\x00' * 4
        else:
            file_path = os.path.join(spirit_dir, f"file_{entry['id']}{get_file_format(entry)}")
            if not os.path.exists(file_path):
                print(f"ERROR: File not found for entry ID {entry['id']}: {file_path}")
                continue
            with open(file_path, 'rb') as f:
                entry_data = f.read()

        rebuilt_entry_length = len(entry_data)
        actual_sector_size = align_sector(rebuilt_entry_length, 2048)

        # Padding
        entry_data += b'\x00' * (actual_sector_size - rebuilt_entry_length)

        repacked_data_parts.append(entry_data)

        repacked_sectors.append({
            "id": sector_id_map[entry["id"]],
            "sector": current_physical_offset // 2048,
            "size": rebuilt_entry_length #actual_sector_size
        })

        current_physical_offset += actual_sector_size

    # Join all parts at the end for efficiency
    final_repacked_data = b''.join(repacked_data_parts)

    with open(output_spirit, 'wb') as f:
        f.write(final_repacked_data)
    print(f"[+] Repacked spirit.dat to '{output_spirit}'")
    
    
    # Update offsets and size in sector table in slpm file
    with open(slpm_file, 'rb') as f:
        slpm = bytearray(f.read())

    repacked_sectors.sort(key=lambda x: x["id"])
    for i, sector in enumerate(repacked_sectors):
        offset = SECTORS_OFFSET + i * 8
        struct.pack_into('<II', slpm, offset, sector["sector"], sector["size"])
            
    with open(output_slpm, 'wb') as f:
        f.write(slpm)
        
    print(f"[+] Patched SLPM and wrote to '{output_slpm}'")


# ----- Main Repack Script -----
def main():
    parser = argparse.ArgumentParser(
        description="Repack spirit.dat archive from extracted folder and patch sectors in SLPM file"
    )
    parser.add_argument("spirit_dir", help="Extracted SPIRIT directory")
    parser.add_argument("output_spirit", help="Output path for the repacked spirit.dat file")
    parser.add_argument("slpm_file", help="Path to the orig SLPM_862.74 file")
    parser.add_argument("output_slpm", help="Output path for the patched SLPM_862.74 file")
    args = parser.parse_args()

    repack_spirit(args.spirit_dir, args.output_spirit, args.slpm_file, args.output_slpm)

if __name__ == '__main__':
    main()