SELECT version, name, comment, user
FROM versions
WHERE uuid IN (
    SELECT uuid
    FROM elements
    WHERE identifier='$(IDENTIFIER)'
)
ORDER BY version DESC
LIMIT 1