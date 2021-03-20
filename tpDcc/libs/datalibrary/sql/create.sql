CREATE TABLE fields
(
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    sortable BOOLEAN,
    groupable BOOLEAN
);
CREATE UNIQUE INDEX fields_id_uindex ON fields(id);

-- We need to insert entries in this way to support sqlite3 in Python 2
-- Also, not that we cannot use TRUE/FALSE, se we use 1/0 instead
INSERT into fields (name, sortable, groupable) VALUES ('uuid', 0, 0);
INSERT into fields (name, sortable, groupable) VALUES ('name', 1, 0);
INSERT into fields (name, sortable, groupable) VALUES ('directory', 1, 0);
INSERT into fields (name, sortable, groupable) VALUES ('type', 1, 1);
INSERT into fields (name, sortable, groupable) VALUES ('extension', 1, 1);
INSERT into fields (name, sortable, groupable) VALUES ('folder', 1, 0);
INSERT into fields (name, sortable, groupable) VALUES ('modified', 1, 0);
INSERT into fields (name, sortable, groupable) VALUES ('user', 1, 1);
INSERT into fields (name, sortable, groupable) VALUES ('ctime', 1, 0);

CREATE TABLE elements
(
    id INTEGER PRIMARY KEY,
    identifier TEXT NOT NULL,
    uuid TEXT NOT NULL,
    name TEXT,
    directory TEXT,
    type TEXT,
    extension TEXT,
    folder BOOLEAN,
    user TEXT,
    modified TIME,
    ctime INTEGER
);
CREATE UNIQUE INDEX elements_id_uindex ON elements(id);
CREATE UNIQUE INDEX elements_identifier_uindex ON elements(identifier);
CREATE UNIQUE INDEX elements_uuid_uindex ON elements(uuid);

CREATE TABLE map_dependencies
(
  element_uuid TEXT NOT NULL,
  requirement_uuid TEXT NOT NULL,
  name TEXT,
  PRIMARY KEY(element_uuid, requirement_uuid),
  CONSTRAINT map_dependencies_element_id_fk FOREIGN KEY (element_uuid) REFERENCES elements (uuid) ON UPDATE CASCADE ON DELETE CASCADE,
  CONSTRAINT map_dependencies_requirement_id_fk FOREIGN KEY (requirement_uuid) REFERENCES elements (uuid) ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE TABLE tags
(
    id INTEGER PRIMARY KEY,
    tag TEXT NOT NULL
);
CREATE UNIQUE INDEX tags_id_uindex ON tags (id);
CREATE UNIQUE INDEX tags_tag_uindex ON tags (tag);

CREATE TABLE map_tags
(
    element_id INT NOT NULL,
    tag_id INT NOT NULL,
    PRIMARY KEY(element_id, tag_id),
    CONSTRAINT map_tags_element_id_fk FOREIGN KEY (element_id) REFERENCES elements (id),
    CONSTRAINT map_tags_tags_id_fk FOREIGN KEY (tag_id) REFERENCES tags (id)
);

CREATE TABLE versions
(
    uuid TEXT NOT NULL,
    version TEXT NOT NULL,
    name TEXT NOT NULL,
    comment TEXT,
    user TEXT,
    PRIMARY KEY(uuid),
    CONSTRAINT map_versions_uuid_fk FOREIGN KEY (uuid) REFERENCES elements (uuid) ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE TABLE thumbnails
(
    uuid TEXT NOT NULL,
    thumbnail TEXT,
    PRIMARY KEY(uuid),
    CONSTRAINT map_versions_uuid_fk FOREIGN KEY (uuid) REFERENCES elements (uuid) ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE TABLE metadata
(
    uuid TEXT NOT NULL,
    version TEXT NOT NULL,
    metadata TEXT,
    PRIMARY KEY(uuid),
    CONSTRAINT map_metadata_uuid_fk FOREIGN KEY (uuid) REFERENCES elements (uuid) ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE TABLE settings
(
  id INTEGER PRIMARY KEY,
  settings TEXT UNIQUE
);

INSERT into settings (settings)
VALUES ("{}")
