> Commit 97bfeaf216ce11a2b8e08eeac2be2fd9568b9d7c:

ALTER TABLE activities_track ADD COLUMN `filetype` varchar(10);
UPDATE activities_track SET filetype="tcx" WHERE filetype is NULL

