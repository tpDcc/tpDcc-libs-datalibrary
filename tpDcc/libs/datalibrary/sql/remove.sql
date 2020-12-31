DELETE FROM map_tags
WHERE element_id = (
    SELECT id
    FROM elements
    WHERE identifier='$(IDENTIFIER)'
);

DELETE FROM map_dependencies
WHERE element_uuid = (
    SELECT uuid
    FROM elements
    WHERE identifier='$(IDENTIFIER)'
)
OR requirement_uuid = (
    SELECT uuid
    FROM elements
    WHERE identifier='$(IDENTIFIER)'
);

DELETE FROM thumbnails
WHERE uuid = (
    SELECT uuid
    FROM elements
    WHERE identifier='$(IDENTIFIER)'
    );

DELETE FROM versions
WHERE uuid = (
    SELECT uuid
    FROM elements
    WHERE identifier='$(IDENTIFIER)'
    );

DELETE FROM metadata
WHERE uuid = (
    SELECT uuid
    FROM elements
    WHERE identifier='$(IDENTIFIER)'
    );

DELETE FROM elements
WHERE identifier='$(IDENTIFIER)';
