#### v0.2.6 "Copy and Paste, a dangerous tool"
* Fix for dds file generation caused by cut and paste shenanigans
* Fixed bug where filter stopped working
* Fixed bug where add external stopped working
* Combine DDSC and DDS processing, now using same code and headers
* Fixed processing of DXGI format 10 which has 16 bit floating point channels (display scales based on single min and max of all channels)

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
