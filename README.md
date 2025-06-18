# Reikoku: Ikeda Kizoku Shinrei Kenkyuujo Tools
Also known as **"Reikoku - Kizoku Ikeda's Psychics Laboratory"**

This project contains tools and scripts used for unpacking, modifying, and translating the game files.

## TODO
- [-] Understand how text is encoded and displayed on screen  
- [ ] Fix all inaccuracies in `font-table.txt`  
- [x] Unpack and repack the `SPIRIT.DAT` file  
- Parse and pack text from files:  
  - [x] `.dialog` (level texts)  
  - [ ] `.scenario` (Haunted Locations texts)  
  - [ ] `.database` (database texts)  
- Translate all texts:  
  - [ ] Level dialogue text  
  - [ ] Haunted Locations  
  - [ ] Interface/items and others  
  - [ ] Database  
- Translate all graphics:  
  - [ ] Images/interface of the database  
  - [ ] Settings/loading/other menus  
  - [ ] Sprites/textures  
- [ ] Extract and dump in-game text embedded in SLPM file tables  
- [ ] Patch for correct display of Latin characters  
- [ ] Subtitles for video cutscenes?  
- [ ] Manual localization  
- [ ] Decompress `.lz` files  

## Image Unpacking/Building

The following tools are used to unpack and rebuild the game disc image:

- [**psximager**](https://github.com/cebix/psximager/tree/master):
  - `psxrip` — Unpacks the PS1 image
  - `psxbuild` — Rebuilds the PS1 image

## SPIRIT.DAT Repack Tools

- `unpack_spirit.py`  
  Extracts `SPIRIT.DAT` into a separate directory using the file `SLPM_862.74` to locate the correct sectors.

- `pack_spirit.py`  
  Packs the contents of the `SPIRIT` directory (must contain `.structure.json`) back into `SPIRIT.DAT` and updates sectors in `SLPM_862.74`.

## Tools for Extracted Files from SPIRIT.DAT

- `parse_model.py`  
  Parses `.model` files and converts them into `.obj` format.

- `convert_models.py`  
  Same as above, but processes all files in a directory.

- `parse_tilemap.py`  
  Parses tilemap files into `.json` format. *(Work in progress)*

- `parse_dialog.py`  
  Parses `.dialog` files into `.json` and exports text to an Excel table.

- `pack_dialog.py`  
  Packs Excel table and `.json` file back into `.dialog` format.

## Font Tools

- `font_mapper.py`  
  Loads and works with font mapping tables from the `./font/` directory.

- `check_font_table.py`  
  Checks `font-table.txt` for duplicate entries and outputs results as images.
