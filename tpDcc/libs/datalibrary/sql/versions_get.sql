SELECT version, name, comment, user
FROM versions
WHERE uuid IN (
    SELECT uuid
    FROM elements
    WHERE identifier='$(IDENTIFIER)'
)