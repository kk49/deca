```
SELECT * FROM core_nodes WHERE node_id IN (
    SELECT node_id_src FROM core_string_references WHERE string_rowid IN (
		SELECT rowid FROM core_strings WHERE string LIKE "%gnome%")) ORDER BY v_path


SELECT v_path FROM core_nodes WHERE node_id IN 
    (SELECT node_id_src FROM core_string_references WHERE string_rowid IN 
        (SELECT rowid FROM core_strings WHERE string LIKE "%flash%"))
```