SELECT metadata
FROM metadata
WHERE uuid IN (
    SELECT uuid
    FROM elements
    WHERE identifier='$(IDENTIFIER)'
) AND version='$(VERSION)'
LIMIT 1