SELECT thumbnail
FROM thumbnails
WHERE uuid IN (
    SELECT uuid
    FROM elements
    WHERE identifier='$(IDENTIFIER)'
)
