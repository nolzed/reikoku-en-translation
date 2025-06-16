import os
import argparse
from pathlib import Path
import struct

from parse_model import parse_ps1_model_data, convert_to_obj

def convert_all_models(input_dir, output_dir):
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    model_files = list(input_dir.glob("*.model"))

    if not model_files:
        print("No .model files found.")
        return

    for model_path in model_files:
        print(f"Processing: {model_path.name}")

        with open(model_path, "rb") as f:
            data = f.read()

        model_data = parse_ps1_model_data(data)

        output_path = output_dir / (model_path.stem + ".obj")
        convert_to_obj(model_data, output_path)

    print(f"\nConversion completed. Files saved: {len(model_files)}")


def main():
    parser = argparse.ArgumentParser(description="Converter for PS1 .model files to OBJ format")
    parser.add_argument("input_dir", type=str, help="Path to folder with .model files")
    parser.add_argument("output_dir", type=str, help="Path to folder where .obj files will be saved")

    args = parser.parse_args()
    convert_all_models(args.input_dir, args.output_dir)


if __name__ == "__main__":
    main()

