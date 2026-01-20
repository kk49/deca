# ((DE)C)onstructor for (A)pps (DECA)

["Everything should be built top-down, except the first time." - Alan Perlis](http://www.cs.yale.edu/homes/perlis-alan/quotes.html)

**Code contributions are more than welcome!!!**

A hacked up tool for exploring/extracting/modding files from Avalanche Studios APEX engine files, 
mainly Generation Zero.

Written in Python, tested only on Linux, code is a mess, because this is an experiment...

## (Pre-)Releases for Windows
https://github.com/kk49/deca/releases

*Development Releases are on the Discord*

## Discord
For **deca** specific and general GenZero, theHunter:COTW, and other APEX engine games modding.
Also has a channel for development releases of **deca**

https://discord.gg/x5AuPj7

## Maps and data mining created with DECA
### Generation Zero
* Main page - http://www.mathartbang.com/deca/gz/
* Map - http://www.mathartbang.com/deca/gz/map.html

### theHunter:COTW
* Main page - http://www.mathartbang.com/deca/hp/
* Map - http://www.mathartbang.com/deca/hp/map.html

## Key Features
* Export (modelc, meshc, hrmeshc) to GLTF 2.0 (material models not complete/missing, no bones)
* Export ADF encoded spreadsheets
* Export textures to PNG
* Parsing most ADF files (Gen Zero)
* GUI to explore archive files
* Basic rebuilding of archive files to update textures, Characters/Machines work. Set pieces do not.

## "Supported" Games
Support varies among the games, people are activily using **deca** for GenZero and theHunter:COTW

|Studio|GAME|
|---|---|
|Avalanche Studios / Systemic Reaction|Generation Zero®|
|Avalanche Studios / Expansive Worlds|theHunter™: Call of the Wild|
|Avalanche Studios / Expansive Worlds|theHunter™: Classic|
|Avalanche Studios / Expansive Worlds|theHunter™: Primal|
|Avalanche Studios / Expansive Worlds|Call of the Wild: The Angler™|
|Avalanche Studios|Just Cause 3|
|Avalanche Studios|Just Cause 4|
|Avalanche Studios / Warner Bros. Interactive Entertainment.|Mad Max (2015)|
|Avalanche Studios|RAGE 2|
|Avalanche Studios / Systemic Reaction|Second Extinction|


## Quick Start
No installer, just unzip the [release file](https://github.com/kk49/deca/releases) in some directory and start deca_gui.exe. (not signed so windows will complain)
Go to the menu and under File select New Project ..., find theHunter EXE, and wait 40 minutes the first time.
It does a bunch of work to figure out possible file names, and python multiprocessing on Windows is a pain.

It will uncompress all the compressed sections of the archives and place them into "__ CACHE __" in the project 
directory.

It currently creates a work/hp directory one directory above where deca_gui.exe is. So you can used File/Open Project 
and find the project.json file to open it again. Ignore the log tab on the left and take a look at the DIR tab, which 
shows the entry VFS layout. Double click on nodes and the contents (if **deca** can parse them) appears in the tables on 
the right.

Individual files can be extracted with the EXTRACT button after they are selected with one click. They are placed in 
the project directory under "extracted". Folders can be extracted recursively so be careful unless you want to expand 
gigabytes of data.

Modding is a work in progress, files are extracted with the PREP MOD button and placed in the "mod" sub-directory.
BUILD MOD will then package up all the files in the mod directory (which you can/must edit by hand right now) and 
places the results into the "build" sub-directory. The build directory contents can then be copied to the normal 
"dropzone" folder like in JC3 (I have not tested it with theHunter, only GZB, and even then all I know is that the 
game does not crash before it gets to BETA over screen)

## Game Support

## File Type Status (Numbers are arbitrary)
|FILES|Status|Notes|
|-----|-----------|-----|
|TAB/ARC|Done| |
|AAF| Done|  |
|SARC| Done|  |
|AVTX, ATX, DDSC, HMDDSC| Done |  |
|ADF| Extractable, Parsed | Partial Handling of GameDataCollection (0x178842fe)|
| |  | Export of modelc, meshc, hrmeshc, mdic to GLTF 2.0 (material models not correct?, missing bones) |
| |  | Missing code for types that have hardcoded parsers in EXE(?) |
| |  | stringlookup not fully grokked |
|RTPC|  Extractable, Parsed |  |
|OGG| Extractable | Ogg file, can be extracted |
|CFX|  Extractable | Autodesk Scaleform https://github.com/jindrapetrik/jpexs-decompiler |
|.obc|  Extractable | found a correlation in file size, guess at record size/count |
|RIFF|  Extractable |  |
|lFSB5|  Extractable |  |
|RBMDL| Extractable |  |
|TAG0|  Extractable |  |
|btc|  Extractable |  |

## External Dependencies
* A modified version of [HavokLib](https://github.com/PredatorCZ/HavokLib) (Modified version here https://github.com/kk49/HavokLib)
 
## References

#### Gibbed's Just Cause 3 archive exporter
Learned about ALL the files here and used as a basis to understand changes made in GZ.

Big thanks to Gibbed for creating and sharing his work!!!

https://github.com/gibbed/Gibbed.JustCause3

#### Timothée Feuillet's fork of Rick Gibbed's tools
This filled in some holes for the ADF parsing
"A Fork of the Just Cause 3 tools by Rick Gibbed" 
https://github.com/tim42/gibbed-justcause3-tools-fork

#### Lukas Cone (PredatorCZ) Apex Tools
This has information about how stranger AmfBuffer formats are "compressed"
https://github.com/PredatorCZ/ApexLib

#### Various Microsoft(tm) websites
Got most of the info for parsing the custom image formats came from the source documentation for DirectX

#### CFX Decompiler
I don't have to worry about the CFX files because of this!
https://github.com/jindrapetrik/jpexs-decompiler

### For map generator and viewing files locally with pouchdb
add this to chrome command line 
```
--allow-file-access-from-files --allow-file-access --allow-cross-origin-auth-prompt
```

### Blender
#### Script to turn off normal smoothing
```
for object in bpy.context.scene.objects:
    if object.type == 'MESH': 
        object.data.use_auto_smooth = False
```

### [Kaitai](https://kaitai.io/) Format
Format files for `.gfx` for string extraction and older (for GZ and COTW) non RTPC `world.bin` files are provide with 
[Kaitai](https://kaitai.io/) description files. Kaitai links [Main](https://kaitai.io/), [IDE](https://ide.kaitai.io/), [docs](http://doc.kaitai.io/user_guide.html)  

## Disclaimer (IANAL)
All product names, logos, and brands are property of their respective owners. All company, product and service names used in this website are for identification purposes only. Use of these names, logos, and brands does not imply endorsement.
