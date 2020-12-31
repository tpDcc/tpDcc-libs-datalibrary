INSERT OR IGNORE INTO map_dependencies (element_uuid, requirement_uuid, name)
VALUES (
(SELECT uuid FROM elements WHERE identifier = '$(ROOT_IDENTIFIER)'),
(SELECT uuid FROM elements WHERE identifier = '$(DEPENDENCY_IDENTIFIER)'),
'$(NAME)'
);