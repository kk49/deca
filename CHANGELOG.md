#### v0.2.16-wip ???
* Updated to support COTW the Angler (WIP)
* Added COTW reserve 14 NH support
* New packaging

#### v0.2.15 free abortions on demand
* Updated to support COTW 2022-06-28
* Added COTW reserve 13 Finland support

#### v0.2.14 5 by 5
* added Mississippi (delta) update for COTW
* added more strings from the community
* added vpath file names for COTW

#### v0.2.13 meh
* REBUILD DB: added sha1sum hash for every node, this is written to vpaths to let people see what files changed between releases
* Added placeholder to BC6H DXGI loader, for now it fills in a 0,0,0,0 color for all pixels
* Fixed Eye model extraction for COTW  
* Added support for reserve 10 and 11 in COTW
* Fixed some issues with JC4 model extraction
* Added option to not build archives when building mods
* (REMOVED) Added option to "Save Changed Files As Symlinks" at mod build time, this will mark changed files as symlink instead of copying the changed file in SARC files
* For ADF files that exist inside GDC/GDCC files (currently only GenZero) extract a gdcc.txt version to seperate it from the normal ADF files
* For ADF files that exist inside GDC/GDCC files (currently only GenZero) allow the display of the version inside the GDC and one example of the one outside of the GDC
* LINUX ONLY: Added dumping of translation file during startup to `<working dir>/text_debug.txt`
* TEST HACK: allow same file to be added twice to SARC file
* Added cross game field strings, and a second cross game database in work/
* Added messages to indicate which file is being exported and in what format (at least for raw and text)
* Made parsing more forgiving of missing 0xDEFE88ED types, 0xDEFE88ED may contain length in second field? But length does not matter anyway for skiping data
* Improved error when reporting which type in an ADF object is missing, this gives details for 0xDEFE88ED types
* Fixed crash when doing text export of entire editor directory in GenZero
* Added elapsed time log message for when ARCHIVE is being processed
* Added various possible field names, updated rtpc to always show property hash id, and optionally the matching string if it exits
* Fixed bug in extracting item from Raw list tab

#### v0.2.12 "THis implies the existence of a one themed game"
* Support for Second Extinction 
* Added [kaitai](https://kaitai.io/) format files for non-RTPC (GZ and COTW) locations/world.bin files
* Fixed GLTF2 skeletons for model types without MeshProperties, now assumes if BoneIndex or BoneWeight exits, it is skinned, also always use boneIndexMapping if it exists
* Made location extraction more flexible and tolerant of missing models
* Fixed decompression of compression type 3 (it's zstandard records), added bypass for non compressed blocks
* Made XLSX extractor more flexible to handle mystery entry
* Added extrapolation for file names from model_xml to modelc for COTW
* Added COTW mesh type 0x6f841426 to gltf2 export
* Fixed bug in preparing for modding and creating mod/ directory
* dump cache directory to log on first use

#### v0.2.11 Damn it's hot (applicable only in the norther hemisphere)
* Added option to extract maps both full resolution png and tiles for webmaps
* Added hack to handle bone weights being all zero when vertex is not connected to any bones, APEX is fine with this GLTF2/Blender is not
* Added guessing of textures/hp_ai_textures/{\*,\*_user}.ddsc from settings/hp_settings/hp_ai_textures/\*.bmp_datac    
* GLTF2 export of BC1_UNORM, BC2_UNORM, BC3_UNORM, downgrades to pre DX10 format, to work around blender bug(?)
* First pass at RAGE2 model export. (BUG IN APEX ENGINE? index buffer offsets in archive, offsets not in bytes, but indexes)
* All game {gz, gzb, jc3, jc4, rg2}.json configurations are loaded from `resources/gameinfo`
* Additional user provided game configurations can be loaded from `work/gameinfo`
* Added cleanup of textures that have missing mip levels when exporting to GLTF2.
* Added speculative decoding of u32s in RTPC to hashed strings, also Cleanup of RTPC processing/handling
* Added pre dxt10 dwFourCC encodings DXT2, DXT4, ATI1, BC5U ala https://walbourn.github.io/the-dds-file-format-lives/
* Added option to export GLTF2 models with: dds format, ddsc (dds format, ddsc extension), or png formats
* Added loading of strings from `work/property_list.hsh` if it exists. property_list.hsh is included in the Ashen Tools 
* Fixed typo in RTPC 48 bit hash lookup, was using cache incorrectly
* Added more aggressive splitting of strings into possible substrings, now splits on `,`, `|`
* Changed call to skeleton generator to use subprocess.run instead of os.system, should capture stderr and stdout 
* Better handling of GLTF2 export of adf files that are not models and/or are missing type info
* Handle games without settings/hp_settings/equipment.bin
* Upgraded Pillow to 7.1.0 (security alert fix)
* Regular expression mask:
    * Accepted when **Enter** is key'ed or **SET** is pressed
    * Reset to previously accepted value if **Esc** is key'ed or **CLEAR** is pressed
    * Has a yellow text background when valid but not yet accepted expression is entered
    * Has a red text background when not valid
 
#### v0.2.10 Half Way There
* GLTF2: Added option to export skeletons with models (Using [HavokLib!](https://github.com/PredatorCZ/HavokLib))
* GUI: will now create a new tab with the contents of a SARC (nl/fl/...) when the open button in the SARC tab is pressed
* Build: Option added to build a subset of files/archives. Check build subset checkbox, and press build
* Build: Added building ddsc, atx?, hmddsc? directly into archive files, this can be used to package dds files renamed as ddsc!!!
* GUI: Added "G, H, S" column, which displays how many versions of a file are
  * G : in a GDCC file
  * H : "Hard" meaning the file contents are present
  * S : "Symbolic" meaning the container of the file only references the file by name, and does not contain the contents
* GUI: Removed Used Depth column, was only used during early development, not super useful currently
* Load large files 1MB at a time during file determination this was a problem for some people on windows
* Added script and support to process CAnimSpline objects
* Textures: dxgi type 41 support, JC4 s failed to load because this was missing
* Added Loading of multiple external files at once to Load External File
* Textures: Added more mapping of texture types to their base type
* Textures: Added text name for texture types
* Textures: Fixed processing of non square textures
* Textures: Reinstated requirement that DDS to DDSC conversion requires matching DXGI type and size
* Added info about DirectXTex, not currently used
* Fixed issue with uint32* parameter in some ADF files, causing a crash because it attempts to do a hash string lookup
* GUI: Added folder button next to each extract button and build button to open folder in OS 
* Added file node trace for exception causes nodes/files
* GUI: Fixed hash to string search function in gui
* Fixed issue with newer file formats, block info was not reloaded from the database
* Fixed missing skeleton from weapons

#### v0.2.9 The May Day edition
* Added ability to do basic dump of APEX engine files (like a save file) without processing entire game
* Fixed issue with not tracking missing ADF types
* Fixed processing of JC3 (missing image type info, and ADF type bug, related to missing ADF type tracking bug)
* Fix for text export issue of GZ savefile on at least on windows machine
* Will now attempt to annotate all integer and integer array fields in an ADF file to an equipment or text
* Fixed issue with building ddsc files
* Added user readable name of equipment that uses clothing models
* Added notes column to file tree to add information that deca finds while processing files
* Added Translated Name of equipment to comment in ADF files when EquipmentHash is found

#### v0.2.8 "I really need to clean my room" 
* Added lookup of EquipmentName when EquipmentHash is encountered in string dump of ADF files
* Added hacky version of exporting VegetationBark and VegetationFoliage material types for GLTF2 export
* Moved(ing) GLTF2 processing of APEX models to duck typing, removing asserts, as avalanche has changed types
* Added schematics and loot items to GZ map generation
* Added script to extract schematic and loot item locations
* Fixed issue with process_adf and process_rtpc needing the data base because they want to lookup hash strings. With no data base it doesnt translate hash strings
* Added webhook to put latest successful build into discord
* Updated to Pillow 6.2.2 to fix CVE-2019-19911 and CVE-2020-5313

#### v0.2.7 Stay Safe
* Added tracking of RTPC objects, object ids, and event ids to DB
* Stopped dumping of image file details
* Fixed Gen Zero map build code
* Added mapping of check_apex_social_event to GZ Map generation
* Added embedded ADF files in EXE to VFS tree, process instances in them, fixed array processing

#### v0.2.6 "Copy and Paste, a dangerous tool"
* Fix for dds file generation caused by cut and paste shenanigans
* Fixed bug where filter stopped working
* Fixed bug where add external stopped working
* Combine DDSC and DDS processing, now using same code and headers
* Fixed processing of DXGI format 10 which has 16 bit floating point channels (display scales based on single min and max of all channels)
* Added support for CubeMaps DDSC and DDS
* Support for more image formats, should be all in JC3, JC4, GZ, RAGE2, and theHunter:COTW

#### v0.2.5 "Gotta go faster, without graphic artifacts"
* BC7 decompression works with JIT compilation using Numba

#### v0.2.4 "Gotta go faster"
* Refactored way file type determination is done to separate with and without path processing, and tag nodes as being done to prevent duplication of work.
* garcs are tagged during the raw processing with path phase
* Another String update from Ciprianno

#### v0.2.3 "Gotta go fast"
* Sped up RTPC string dumping speed by caching string hash results and not hitting the DB for every field
* Sped up RTPC string dumping and initial search by switching to the visitor pattern (Issue #84)
* Removed Archive version TODO from title window (Issue #87)
* Updated collection info generator (GZ specific) to use the codex spreadsheet. (Issue #67)
* Fixed issue with extract contents functionality

#### v0.2.2 - I forgot to give the last release a name
* Added custom string file option ../work/custom.txt
* Added extracted fields from Rage2 for all games, ./resources/field_strings/rg2.txt
* Added strings from Ciprianno
* Common string lookup files are now 
  * 'deca/resources/strings.txt' (old), 
  * 'deca/resources/common/fields.txt' (new), 
  * 'deca/resources/common/filenames.txt' (new)
  * 'deca/resources/common/strings.txt' (new)
* User string lookup files are now
  * '../work/fields.txt' (new), 
  * '../work/filenames.txt' (new)
  * '../work/strings.txt' (new)
* Preparing for separation of filename strings from field name strings from miscellaneous strings
* Incomplete support for new DXGI 97 / BC7 image format
* DDSC/AVTX files now put their pixel format into the DB and the sub_type field shared with ADF files that expose their
    ADF type


#### v0.2.1 - * INSERT SOMETHING CLEVER *
* Added automatic splitting of strings along commas with removal of spaces to find more possible strings, this helps
with at least Generation Zero entities
* Made database fields/column names clearer


#### v0.2.0 - "I don't want to do my taxes"
* Decent support for JC4 and RAGE2, no build support for RAGE2 at the moment
* RAGE2 New Files: 
  * ADFs with a single instance and only a hash id of the type
  * "garcs" there are a set of master gt0c files that store info about ee/nl/fl files (which are sarc's in other games)
* New tab based separation of workflow for "extract", "modding", and "3d/GLTF extraction"


#### v0.1.0
* New back-end Sqlite3, simplified access to deca's gathered data, plus...
* Faster archive processing, with DB backend multiple processes can process files in parrallel
* Improved GUI performance, with DB back-end the GUI loads in node info as needed
* \_\_CACHE\_\_ directory layout has changed, cached files now live in directory based on where they physically are
* RTPC and ADF generated text files now look in DB for strings that match hashes without in file strings
* Found 48 bit hash used by GenZero, it is 6 bytes from MurmurHash3-128bit-x64 (which 6 bytes seems to depend on the implementation of the hash)
