import struct, argparse, json

def parse_tilemap(data):
    offset = 0
    
    size = struct.unpack_from('<I', data, offset)[0]
    offset += 4
    print("Tilemap size:", size)
    
    headers = struct.unpack_from('<IIIII', data, offset)
    offset += 20
    print("Headers:", hex(headers[0]), hex(headers[1]), hex(headers[2]), hex(headers[3]), hex(headers[4]))
    
    if headers[2] != headers[3]:
        raise Exception("Last 2 Headers not equal!", hex(headers[2]), hex(headers[3]))
    
    #frames_count = struct.unpack_from('<I', data, offset)[0]
    frames_count = headers[1]
    offset += 4
    print("Animation frames:", frames_count)
    
    frames = []
    for i in range(frames_count):
        frame = struct.unpack_from('<H', data, offset + i*2)[0]
        frames.append(frame)
    offset += frames_count * 2
    
    if frames_count != len(frames):
        raise Exception("Different frames num!", frames_count, len(frames))
    
    sprites_count = headers[2]
    print("Sprites count:", sprites_count)
    sprites_meta = []
    
    for i in range(sprites_count):
        sprite_meta = struct.unpack_from('<HHHH', data, offset + i*8)
        # Sprites are numbered based on clut, frames use order not sprite id
        # 3 sprites * 6 clut = 18 sprites, 0-2 (0 clut), 3-5 (1 clut) ....
        # 1. sprite id
        # 2. flag? 8, 5, FF
        # 3. 0000
        # 4. 0000
        sprites_meta.append(sprite_meta)
    offset += sprites_count * 8
    
    if sprites_count != len(sprites_meta):
        raise Exception("Different sprites meta num!", sprites_count, len(sprites_meta))
        
    print("Sprites meta:", sprites_meta[0])
    
    sprite_offsets = []
    for i in range(sprites_count):
        sprite_offset = struct.unpack_from('<I', data, offset + 4*i)[0]
        sprite_offsets.append(sprite_offset)
    offset += sprites_count * 4
    
    print("Sprite offsets:", hex(sprite_offsets[0]), hex(sprite_offsets[1]), hex(sprite_offsets[2]), "...")
    
    sprites = []
    for i in range(sprites_count):
        flag1, y_offset, x_offset, data1, elapsed_memory, data2, w, h, free, flag2, flag3, flag4 = struct.unpack_from(
            '<hhhhhhhhhhhh', data, offset + sprite_offsets[i]
        )
        sprites.append({
            "flag1" : hex(flag1), 
            "y_offset" : y_offset,
            "x_offset" : x_offset,
            "data1" : hex(data1),
            "elapsed_memory" : elapsed_memory, 
            "data2" : hex(data2), 
            "w" : w, 
            "h" : h, 
            "free" : hex(free), 
            "flag2" : hex(flag2), 
            "flag3" : hex(flag3), 
            "flag4" : hex(flag4)
        })
    
    if offset + sprite_offsets[-1] + 24 != len(data):
        print("[!] Wrong parsing data!", offset, f"{offset + sprite_offsets[-1] + 24}/{len(data)}")
       
    return {
        "size" : size,
        "headers" : headers,
        "frames" : {
            "count" : frames_count,
            "data" : frames
        },
        "sprites" : {
            "count" : sprites_count,
            "meta" : sprites_meta,
            "offsets" : sprite_offsets,
            "data" : sprites
        }
    }

def main():
    parser = argparse.ArgumentParser(
        description="Parse .tilemap file"
    )
    parser.add_argument("file", help="Input .tilemap file")
    parser.add_argument("out", help="Path to write parsed json data")
    args = parser.parse_args()
    
    with open(args.file, 'rb') as f1:
        data = f1.read()

    tilemap = parse_tilemap(data)
    
    with open(args.out, 'w', encoding='utf-8') as out:
        json.dump(tilemap, out, indent=2, ensure_ascii=False)
    
    print("[+] Json tilemap extracted to:", args.out)
    
if __name__ == '__main__':
    main()
