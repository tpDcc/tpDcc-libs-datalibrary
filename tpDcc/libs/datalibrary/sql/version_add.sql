INSERT OR IGNORE INTO versions (uuid, version, name, comment, user)
SELECT '$(UUID)','$(VERSION)','$(NAME)','$(COMMENT)','$(USER)'
WHERE NOT EXISTS(
  SELECT 1 FROM versions WHERE NAME='$(NAME)'
);

-- INSERT OR IGNORE INTO
--   map_versions(element_id, version_id)
-- SELECT
--     (
--     SELECT id as eid
--     FROM elements
--     WHERE uuid='$(UUID)'
--     LIMIT 1
--   ),
--   (
--     SELECT id as vid
--     FROM versions
--     WHERE name='$(NAME)'
--     LIMIT 1
--   )
-- WHERE NOT EXISTS (
--   SELECT * FROM map_versions
--   WHERE element_id=(
--     SELECT id as eid
--     FROM elements
--     WHERE uuid='$(UUID)'
--     LIMIT 1
--   )
--         AND version_id=(
--     SELECT id as vid
--     FROM versions
--     WHERE name='$(NAME)'
--     LIMIT 1
--   )
-- );
