CREATE TABLE fields
(
    id INTEGER PRIMARY KEY ,
    name TEXT NOT NULL,
    sortable BOOLEAN,
    groupable BOOLEAN
);
CREATE UNIQUE INDEX fields_id_uindex ON fields(id);

INSERT into fields (name, sortable, groupable)
VALUES ('name', TRUE, FALSE),
       ('directory', TRUE, FALSE),
       ('type', TRUE, TRUE),
       ('extension', TRUE, TRUE),
       ('folder', TRUE, FALSE),
       ('modified', TRUE, FALSE),
       ('user', TRUE, TRUE),
       ('ctime', TRUE, FALSE),
       ('metadata', FALSE, FALSE);


CREATE TABLE elements
(
    id INTEGER PRIMARY KEY,
    identifier TEXT NOT NULL,
    name TEXT,
    directory TEXT,
    type TEXT,
    extension TEXT,
    folder BOOLEAN,
    user TEXT,
    modified TIME,
    ctime INTEGER,
    metadata TEXT
);
CREATE UNIQUE INDEX elements_id_uindex ON elements(id);
CREATE UNIQUE INDEX elements_identifier_uindex ON elements(identifier);

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

CREATE TABLE settings
(
  id INTEGER PRIMARY KEY,
  settings TEXT UNIQUE
);

INSERT into settings (settings)
VALUES ("{}")
