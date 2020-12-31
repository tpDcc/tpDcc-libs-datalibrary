SELECT requirement_uuid, name
FROM map_dependencies
WHERE element_uuid IN (
    SELECT uuid
    FROM elements
    WHERE identifier = '$(IDENTIFIER)'
)