```
select * from core_vnodes where uid in (
    select src_node from core_hash_string_references where hash_row_id in (
		select rowid from core_hash_strings where string like "%gnome%")) ORDER by v_path
```