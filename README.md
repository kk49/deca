# (DE)Constructor for (A)pex (DECA)

["Everything should be built top-down, except the first time." - Alan Perlis](http://www.cs.yale.edu/homes/perlis-alan/quotes.html)

A hacked up tool for exploring/extracting files from Avalanche Studios APEX engine files, 
mainly to explore Generation Zero BETA files until it's released.

Written in Python, tested only on Linux, code is a mess, because this is an experiment...

## Status
* Extracting all files from GenZ Beta archives
* Parsing files from GenZ Beta archives 
  * 99% ARC/TAB
  * 99% SARC
  * 99% AVTX/DDSC/ATX (image data)
  * 99% AAF
  * 95% ADF
    * Missing GameDataCollection (0x178842fe)
    * Missing MDIC (0xb5b062f1)
    * Missing code for types that do not seem to exist in GZB
    * stringlookup not fully grokked
    * models, hrmesh, mesh, not fully grokked
  * 75% RTPC - parsed but not grokked
  * 10% OBC - found a correlation in file size, guess at record size/count
  * 00% TAG0
  * not touched
    * btc, CFX, RIFF, OGG, lFSB5 



## References
#### Gibbed's Just Cause 3 archive exporter
https://github.com/gibbed/Gibbed.JustCause3

Learned basics RPTC and ADF files here and filled in some other holes.

#### Timothée Feuillet's fork of Rick Gibbed's tools
"A Fork of the Just Cause 3 tools by Rick Gibbed" 
https://github.com/tim42/gibbed-justcause3-tools-fork

This filled in some holes for the ADF parsing

#### Various Microsoft(tm) websites

Got most of the info for parsing the custom image formats came from the source documentation for DirectX
