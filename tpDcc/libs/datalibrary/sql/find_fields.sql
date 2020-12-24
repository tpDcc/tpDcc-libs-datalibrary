SELECT identifier, $(FIELDS)
FROM elements
WHERE identifier in ('$(IDENTIFIERS)')
