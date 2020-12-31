UPDATE elements
SET
    identifier = '$(NEW_IDENTIFIER)',
    uuid = '$(NEW_UUID)',
    name = '$(NEW_NAME)',
    user = '$(USER)',
    modified = '$(MODIFIED)',
    ctime = '$(CTIME)'
WHERE identifier = '$(IDENTIFIER)';
