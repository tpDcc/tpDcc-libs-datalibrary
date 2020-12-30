SELECT
       identifier, map_dependencies.name
FROM elements JOIN map_dependencies ON requirement_uuid == uuid
WHERE uuid in (
    SELECT requirement_uuid
    FROM map_dependencies
    WHERE element_uuid IN (
        SELECT uuid
        FROM elements
        WHERE identifier = '$(IDENTIFIER)'
    )
)
