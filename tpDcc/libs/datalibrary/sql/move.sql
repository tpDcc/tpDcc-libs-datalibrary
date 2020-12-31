UPDATE elements
SET
    identifier = '$(NEW_IDENTIFIER)',
    uuid = '$(NEW_UUID)',
    directory = '$(NEW_DIRECTORY)',
    user = '$(USER)',
    modified = '$(MODIFIED)',
    ctime = '$(CTIME)'
WHERE identifier = '$(IDENTIFIER)';
