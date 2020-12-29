-- INSERT OR IGNORE INTO thumbnails (uuid, thumbnail)
-- SELECT '$(UUID)','$(THUMB)'
-- WHERE NOT EXISTS(
--   SELECT 1 FROM thumbnails WHERE UUID='$(UUID)'
-- );

REPLACE INTO thumbnails (uuid, thumbnail)
VALUES ('$(UUID)', '$(THUMB)')