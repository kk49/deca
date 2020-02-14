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
