import struct, argparse

def parse_ps1_model_data(data):
    """
    Parses PS1 model data based on a specific structure.

    Args:
        data (bytes): Byte data from the model file.

    Returns:
         dict: A dictionary containing the number of vertices, list of vertices,
         number of primitives, and list of primitives.
    """
    offset = 0

    # 1. Reading the number of vertices (16-bit)
    num_vertices = struct.unpack('<I', data[offset:offset + 4])[0]
    offset += 4
    print(f"Vertices detected: {num_vertices}")

    # 2. Read vertex block (each 8 bytes)
    vertices = []
    for i in range(num_vertices):
        # Each vertex: short x, short y, short z, short w_or_padding
        # (all 16-bit signed integers, Little Endian)
        x, y, z, w_or_padding = struct.unpack('<hhhh', data[offset:offset + 8])
        vertices.append({'x': x, 'y': y, 'z': z, 'w_or_padding': w_or_padding})
        offset += 8

    print(f"Parsing of {len(vertices)} vertices is complete.")
    if len(vertices) < num_vertices:
        raise Exception(f"Wrong num parsed vertices: {len(vertices)} < {num_vertices}")
        
    # 3. Reading the number of primitives (16-bit)
    num_primitives = struct.unpack('<I', data[offset:offset + 4])[0]
    offset += 4
    old_offset = offset
    print(f"Primitives have been detected: {num_primitives}")

    # 4. Reading a block of primitives
    primitives = []
    for i in range(num_primitives):
        
        primitive_command = struct.unpack_from('<B', data, offset+3)[0]
        
        if primitive_command in [0x20, 0x22]:
            # GP0(20h) - Monochrome three-point polygon, opaque
            # GP0(22h) - Monochrome three-point polygon, semi-transparent
            #
            #  1st  Color+Command     (CcBbGgRrh)
            #  2nd  Vertex1           (YyyyXxxxh)
            #  3rd  Vertex2           (YyyyXxxxh)
            #  4th  Vertex3           (YyyyXxxxh)
            primitive_data = data[offset:offset + 12]
            header_raw = primitive_data[0:4]
            rgb_color = struct.unpack_from('<BBB', primitive_data, 0)
            
            vertex_indices = struct.unpack_from('<HHH', primitive_data, 4)
            
            primitives.append({
                'header_raw': header_raw,
                'command': hex(primitive_command),
                'rgb_color': rgb_color,
                'vertex_indices': vertex_indices,
            })
            offset += 12
            
        elif primitive_command in [0x28, 0x2A]:
            # GP0(28h) - Monochrome four-point polygon, opaque
            # GP0(2Ah) - Monochrome four-point polygon, semi-transparent
            #
            #  1st  Color+Command     (CcBbGgRrh)
            #  2nd  Vertex1           (YyyyXxxxh)
            #  3rd  Vertex2           (YyyyXxxxh)
            #  4th  Vertex3           (YyyyXxxxh)
            #  5th  Vertex4           (YyyyXxxxh)
            primitive_data = data[offset:offset + 12]
            header_raw = primitive_data[0:4]
            rgb_color = struct.unpack_from('<BBB', primitive_data, 0)
            
            vertex_indices = struct.unpack_from('<HHHH', primitive_data, 4)
            
            primitives.append({
                'header_raw': header_raw,
                'command': hex(primitive_command),
                'rgb_color': rgb_color,
                'vertex_indices': vertex_indices,
            })
            offset += 12
         
        elif primitive_command in [0x24]:
            # GP0(24h) - Textured three-point polygon, opaque, texture-blending
            # GP0(25h) - Textured three-point polygon, opaque, raw-texture
            # GP0(26h) - Textured three-point polygon, semi-transparent, texture-blending
            # GP0(27h) - Textured three-point polygon, semi-transparent, raw-texture
            # 
            #  1st  Color+Command     (CcBbGgRrh) (color is ignored for raw-textures)
            #  2nd  Vertex1           (YyyyXxxxh)
            #  3rd  Texcoord1+Palette (ClutYyXxh)
            #  4th  Vertex2           (YyyyXxxxh)
            #  5th  Texcoord2+Texpage (PageYyXxh)
            #  6th  Vertex3           (YyyyXxxxh)
            #  7th  Texcoord3         (0000YyXxh)
            
            primitive_data = data[offset:offset + 20]
            header_raw = primitive_data[0:4]
            rgb_color = struct.unpack_from('<BBB', primitive_data, 0)
            
            vertex_indices = struct.unpack_from('<HHH', primitive_data, 4)
            texture_raw = primitive_data[10:20]
            
            primitives.append({
                'header_raw': header_raw,
                'command': hex(primitive_command),
                'rgb_color': rgb_color,
                'vertex_indices': vertex_indices,
                'texture_raw': texture_raw
            })
            offset += 20
            
        elif primitive_command in [0x25, 0x2E, 0x2F]:
            # GP0(24h) - Textured three-point polygon, opaque, texture-blending
            # GP0(25h) - Textured three-point polygon, opaque, raw-texture
            # GP0(26h) - Textured three-point polygon, semi-transparent, texture-blending
            # GP0(27h) - Textured three-point polygon, semi-transparent, raw-texture
            # 
            #  1st  Color+Command     (CcBbGgRrh) (color is ignored for raw-textures)
            #  2nd  Vertex1           (YyyyXxxxh)
            #  3rd  Texcoord1+Palette (ClutYyXxh)
            #  4th  Vertex2           (YyyyXxxxh)
            #  5th  Texcoord2+Texpage (PageYyXxh)
            #  6th  Vertex3           (YyyyXxxxh)
            #  7th  Texcoord3         (0000YyXxh)
            
            primitive_data = data[offset:offset + 24]
            header_raw = primitive_data[0:4]
            rgb_color = struct.unpack_from('<BBB', primitive_data, 0)
            
            vertex_indices = struct.unpack_from('<HHH', primitive_data, 4)
            texture_raw = primitive_data[12:24]
            
            primitives.append({
                'header_raw': header_raw,
                'command': hex(primitive_command),
                'rgb_color': rgb_color,
                'vertex_indices': vertex_indices,
                'texture_raw': texture_raw
            })
            offset += 24

        elif primitive_command in [0x2C, 0x2D, 0x2E, 0x2F]:
            # GP0(2Ch) - Textured four-point polygon, opaque, texture-blending
            # GP0(2Dh) - Textured four-point polygon, opaque, raw-texture
            # GP0(2Eh) - Textured four-point polygon, semi-transparent, texture-blending
            # GP0(2Fh) - Textured four-point polygon, semi-transparent, raw-texture
            # 
            #  1st  Color+Command     (CcBbGgRrh) (color is ignored for raw-textures)
            #  2nd  Vertex1           (YyyyXxxxh)
            #  3rd  Texcoord1+Palette (ClutYyXxh)
            #  4th  Vertex2           (YyyyXxxxh)
            #  5th  Texcoord2+Texpage (PageYyXxh)
            #  6th  Vertex3           (YyyyXxxxh)
            #  7th  Texcoord3         (0000YyXxh)
            #  8th  Vertex4           (YyyyXxxxh)
            #  9th  Texcoord4         (0000YyXxh)
            
            primitive_data = data[offset:offset + 24]
            header_raw = primitive_data[0:4]
            rgb_color = struct.unpack_from('<BBB', primitive_data, 0)
            
            vertex_indices = struct.unpack_from('<HHHH', primitive_data, 4)
            texture_raw = primitive_data[12:24]
            
            primitives.append({
                'header_raw': header_raw,
                'command': hex(primitive_command),
                'rgb_color': rgb_color,
                'vertex_indices': vertex_indices,
                'texture_raw': texture_raw
            })
            offset += 24
        elif primitive_command in [0x30, 0x32]:
            #  GP0(30h) - Shaded three-point polygon, opaque
            #  GP0(32h) - Shaded three-point polygon, semi-transparent
            # 
            #  1st  Color1+Command    (CcBbGgRrh)
            #  2nd  Vertex1           (YyyyXxxxh)
            #  3rd  Color2            (00BbGgRrh)
            #  4th  Vertex2           (YyyyXxxxh)
            #  5th  Color3            (00BbGgRrh)
            #  6th  Vertex3           (YyyyXxxxh)

            primitive_data = data[offset:offset + 20]
            header_raw = primitive_data[0:4]
            rgb_color = struct.unpack_from('<BBB', primitive_data, 0)
            
            vertex_indices = struct.unpack_from('<HHH', primitive_data, 4)
            shader_color_raw = primitive_data[12:20]
            
            primitives.append({
                'header_raw': header_raw,
                'command': hex(primitive_command),
                'rgb_color': rgb_color,
                'vertex_indices': vertex_indices,
                'shader_color_raw': shader_color_raw
            })
            
            offset += 20
            
        elif primitive_command in [0x38, 0x3A]:
            # GP0(38h) - Shaded four-point polygon, opaque
            # GP0(3Ah) - Shaded four-point polygon, semi-transparent
            # 
            #  1st  Color1+Command    (CcBbGgRrh)
            #  2nd  Vertex1           (YyyyXxxxh)
            #  3rd  Color2            (00BbGgRrh)
            #  4th  Vertex2           (YyyyXxxxh)
            #  5th  Color3            (00BbGgRrh)
            #  6th  Vertex3           (YyyyXxxxh)
            #  7th  Color4            (00BbGgRrh)
            #  8th  Vertex4           (YyyyXxxxh)

            primitive_data = data[offset:offset + 24]
            header_raw = primitive_data[0:4]
            rgb_color = struct.unpack_from('<BBB', primitive_data, 0)
            
            vertex_indices = struct.unpack_from('<HHHH', primitive_data, 4)
            shader_color_raw = primitive_data[12:24]
            
            primitives.append({
                'header_raw': header_raw,
                'command': hex(primitive_command),
                'rgb_color': rgb_color,
                'vertex_indices': vertex_indices,
                'shader_color_raw': shader_color_raw
            })
            offset += 24
        elif primitive_command in [0x34, 0x36]:
            #  GP0(34h) - Shaded Textured three-point polygon, opaque, texture-blending
            #  GP0(36h) - Shaded Textured three-point polygon, semi-transparent, tex-blend
            # 
            #  1st  Color1+Command    (CcBbGgRrh)
            #  2nd  Vertex1           (YyyyXxxxh)
            #  3rd  Texcoord1+Palette (ClutYyXxh)
            #  4th  Color2            (00BbGgRrh)
            #  5th  Vertex2           (YyyyXxxxh)
            #  6th  Texcoord2+Texpage (PageYyXxh)
            #  7th  Color3            (00BbGgRrh)
            #  8th  Vertex3           (YyyyXxxxh)
            #  9th  Texcoord3         (0000YyXxh)

            primitive_data = data[offset:offset + 28]
            header_raw = primitive_data[0:4]
            rgb_color = struct.unpack_from('<BBB', primitive_data, 0)
            
            vertex_indices = struct.unpack_from('<HHH', primitive_data, 4)
            shader_color_raw = primitive_data[10:20]
            texture_raw = primitive_data[20:28]
            
            primitives.append({
                'header_raw': header_raw,
                'command': hex(primitive_command),
                'rgb_color': rgb_color,
                'vertex_indices': vertex_indices,
                'shader_color_raw': shader_color_raw,
                'texture_raw' : texture_raw
            })
            offset += 28
            
        elif primitive_command in [0x3C, 0x3E]:
            #  GP0(3Ch) - Shaded Textured four-point polygon, opaque, texture-blending
            #  GP0(3Eh) - Shaded Textured four-point polygon, semi-transparent, tex-blend
            # 
            #  1st  Color1+Command    (CcBbGgRrh)
            #  2nd  Vertex1           (YyyyXxxxh)
            #  3rd  Texcoord1+Palette (ClutYyXxh)
            #  4th  Color2            (00BbGgRrh)
            #  5th  Vertex2           (YyyyXxxxh)
            #  6th  Texcoord2+Texpage (PageYyXxh)
            #  7th  Color3            (00BbGgRrh)
            #  8th  Vertex3           (YyyyXxxxh)
            #  9th  Texcoord3         (0000YyXxh)
            #  10th Color4            (00BbGgRrh)
            #  11th Vertex4           (YyyyXxxxh)
            #  12th Texcoord4         (0000YyXxh)

            primitive_data = data[offset:offset + 36]
            header_raw = primitive_data[0:4]
            rgb_color = struct.unpack_from('<BBB', primitive_data, 0)
            
            vertex_indices = struct.unpack_from('<HHHH', primitive_data, 4)
            shader_color_raw = primitive_data[12:24]
            texture_raw = primitive_data[24:36]
            
            primitives.append({
                'header_raw': header_raw,
                'command': hex(primitive_command),
                'rgb_color': rgb_color,
                'vertex_indices': vertex_indices,
                'shader_color_raw': shader_color_raw,
                'texture_raw' : texture_raw
            })
            offset += 36
            
            
        else:
            raise Exception(f"Unknown primitive command: {i} | {hex(primitive_command)} | {data[offset:offset+4]}")
        
        
    print(f"Parsing of {len(primitives)} primitives is complete.")

    return {
        'num_vertices': num_vertices,
        'vertices': vertices,
        'num_primitives': num_primitives,
        'primitives': primitives
    }

def convert_to_obj(model_data, output_filepath):
    """
    Converts parsed PS1 model data to OBJ format.

    Args:
        model_data (dict): The dictionary returned by parse_ps1_model_data.
        output_filepath (str): The path to the OBJ file to save.
    """
    with open(output_filepath, 'w') as f:
        f.write(f"# Vertices: {model_data['num_vertices']}\n")
        f.write(f"# Primitives: {model_data['num_primitives']}\n\n")

        # Write vertices
        for i, vert in enumerate(model_data['vertices']):
            # OBJ format expects float, but PS1 uses short.
            # It may be necessary to scale x, y, z values for a better display
            # in standard 3D editors, as they may be very small or large.
            f.write(f"v {vert['x']} {vert['y']} {vert['z']}\n")
        f.write("\n")

        # Recording facets
        for i, prim in enumerate(model_data['primitives']):

            # Vertex indices in OBJ must be from 1
            v_indices = [idx + 1 for idx in prim['vertex_indices']]
            
            if len(v_indices) == 4:
                f.write(f"f {v_indices[0]} {v_indices[1]} {v_indices[3]} {v_indices[2]}\n")
            elif len(v_indices) == 3:
                f.write(f"f {v_indices[0]} {v_indices[1]} {v_indices[2]}\n")
            else:
                raise Exception(f"Unkonwn num vertex indices: {len(v_indices)} | {v_indices}")

        print(f"The model has been successfully saved in {output_filepath}")
    
def main():
    parser = argparse.ArgumentParser(
        description="Parse .model file"
    )
    parser.add_argument("file", help="Input .model file")
    parser.add_argument("out", help="Path to write parsed .obj model")
    args = parser.parse_args()
    
    with open(args.file, 'rb') as f1:
        data = f1.read()

    parsed_model = parse_ps1_model_data(data)
    
    convert_to_obj(parsed_model, args.out)
    
if __name__ == '__main__':
    main()