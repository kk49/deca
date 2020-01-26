* unify string hash tables
* theHunter uses 4byte hash for event ids?
* try all hash ideas when resolving unknown hash, give lookup number of known bytes
* get strings from JC3 and the hunter and GZ EXE and make one master list, older games may expose more
* Change bob's error source to generateor?

* Handle rival images, how are the name generated

* strings
  * hash4
  * hash6
  * string
* string_define -> node
* string_usage -> node

* event_id_usage -> ???
* object_id_usage -> node
* object_id_define -> node

* track audio files to events, determine how translatable audio files are used  
  * Example file hash == 00FFFE21 file number 15604
  * Mission pm_03_southcoast, 218561533  (flicka translated to english)
  * ```
    # Structure(0xC4AB11E3), Data Offset: 95832(0x00017658)
    {
      Id:
        462990682  # sint32(0x192FE633), Data Offset: 95832(0x00017658)
      Name:
        b'mission_wb_pm_03_missionitem_04_header' (0x2c250f28)  # String Hash(0xC03F64BF), Data Offset: 95836(0x0001765c)
      NameShort:
        b'attach_paper' (0x6907c7bc)  # String Hash(0xC03F64BF), Data Offset: 95840(0x00017660)
      Type:
        3  # sint32(0x192FE633), Data Offset: 95844(0x00017664)
      Event:
        OBJID 6 0x0000ca9556052e33 (0xca9556052e33)  # String Hash(0x7421FAD9), Data Offset: 95848(0x00017668)
      Text:
        b'mission_wb_pm_03_missionitem_04_content' (0xa6094cd9)  # String Hash(0xC03F64BF), Data Offset: 95856(0x00017670)
      PlayAudioEvent:
        OBJID 6 0x0000189e8146ac44 (0x189e8146ac44)  # String Hash(0x7421FAD9), Data Offset: 95860(0x00017674)
      StopAudioEvent:
        OBJID 6 0x00006f0f9f8d3f83 (0x6f0f9f8d3f83)  # String Hash(0x7421FAD9), Data Offset: 95866(0x0001767a)
      Enabled:
        1  # uint08(0x0CA2821D), Data Offset: 95872(0x00017680)
      Image:
        b''  # string(0x8955583E), Data Offset: 29584(0x00007390), Info Offset: 95880(0x00017688)
      Entity:
        b'pm03_audio_item_01'  # string(0x8955583E), Data Offset: 95992(0x000176f8), Info Offset: 95888(0x00017690)
      DependenciesRequired:
        # Array of sint32s(0xFB9FD4CC), Data Offset: 96(0x00000060), Info Offset: 95896(0x00017698)
        [
        ]
      DependenciesOptional:
        # Array of sint32s(0xFB9FD4CC), Data Offset: 96(0x00000060), Info Offset: 95912(0x000176a8)
        [
        ]
      Persist:
        1  # uint08(0x0CA2821D), Data Offset: 95928(0x000176b8)
    }
    ```