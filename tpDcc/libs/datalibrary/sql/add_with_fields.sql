INSERT OR IGNORE INTO elements (identifier,metadata,$(FIELDS))
VALUES ('$(IDENTIFIER)', "$(METADATA)", $(FIELDS_VALUES));