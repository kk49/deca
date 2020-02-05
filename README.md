# ((DE)C)onstructor for (A)pps (DECA)

["Everything should be built top-down, except the first time." - Alan Perlis](http://www.cs.yale.edu/homes/perlis-alan/quotes.html)

**Code contributions are more than welcome!!!**

A hacked up tool for exploring/extracting/modding files from Avalanche Studios APEX engine files, 
mainly Generation Zero.

Written in Python, tested only on Linux, code is a mess, because this is an experiment...

## Key Features
* Export (modelc, meshc, hrmeshc) to GLTF 2.0 (material models not complete/missing, no bones)
* Export ADF encoded spreadsheets
* Export textures to PNG
* Parsing most ADF files (Gen Zero)
* GUI to explore archive files
* Basic rebuilding of archive files to update textures, Characters/Machines work. Set pieces do not.

## Supported Games
|GAME|STATUS|Nodes Total|Nodes Named|Hashes Total|Hashes Found|ADF Types Found / Missing|Last Update|
|---|---|---|---|---|---|---|---|
|Avalanche Studios' Generation Zero®|Loading most/all files|860879|857305|63375|59897|888 / 7|2019/02/04|
|Avalanche Studios' theHunter™: Call of the Wild|Loading most/all files|278223|273556|72268|67717|920 / 0|2019/02/04|
|Avalanche Studios' Just Cause 3|Loading most/all files|---|---|---|---|---|---|
|Avalanche Studios' Just Cause 4|Loading most/all files|1911397|1757124|223864|190329|1055 / 0|2019/02/04|
|Avalanche Studios' RAGE 2|Partial/In-Development|406834|19126|406682|19126|2081 / 0|2019/02/04|

## Discord
For deca specific and general GenZero (and theHunter?) modding.

https://discord.gg/x5AuPj7

## Quick Start
No installer, just unzip the release file in some directory and start deca_gui.exe. (not signed so windows will complain)
Go to the menu and under File select New Project ..., find theHunter EXE, and wait 40 minutes the first time.
It does a bunch of work to figure out possible file names, and python multiprocessing on Windows is a pain.

It will uncompress all the compressed sections of the archives and place them into "__ CACHE __" in the project 
directory.

It currently creates a work/hp directory one directory above where deca_gui.exe is. So you can used File/Open Project 
and find the project.json file to open it again. Ignore the log tab on the left and take a look at the DIR tab, which 
shows the entry VFS layout. Double click on nodes and the contents (if deca can parse them) appears in the tables on 
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
|FILES|Game|Status|Notes|
|-----|------------|-----------|-----|
|TAB/ARC|GZB|Done?| double check code to see if something is not understood |
|AAF| GZB|Done?| double check code to see if something is not understood |
|SARC| GZB|Done?| double check code to see if something is not understood |
|AVTX, ATX, DDSC, HMDDSC| GZB|Done? | double check code to see if something is not understood |
|ADF| GZB | Extractable, Parsed | Partial Handling of GameDataCollection (0x178842fe)|
| |  |  | Export of modelc, meshc, hrmeshc, mdic to GLTF 2.0 (material models not correct?, missing bones) |
| |  |  | Missing code for types that have hardcoded parsers in EXE(?) |
| |  |  | stringlookup not fully grokked |
|RTPC| GZB | Extractable, Parsed |  |
|OGG| GZB| Extractable | Ogg file, can be extracted |
|TAG0| GZB | Extractable |  |
|btc| GZB | Extractable |  |
|CFX| GZB | Extractable | Autodesk Scaleform https://github.com/jindrapetrik/jpexs-decompiler |
|RIFF| GZB | Extractable |  |
|lFSB5| GZB | Extractable |  |
|.obc| GZB | Extractable | found a correlation in file size, guess at record size/count |
|RBMDL|JC3| Extractable |  |

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

## Disclaimer (IANAL)
All product names, logos, and brands are property of their respective owners. All company, product and service names used in this website are for identification purposes only. Use of these names, logos, and brands does not imply endorsement.
