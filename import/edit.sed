s/^  PRIMARY KEY (`ID`),/  PRIMARY KEY (`ID`) -- ,/
s/^  PRIMARY KEY (`id`),/  PRIMARY KEY (`id`) -- ,/
s/^  UNIQUE KEY `MD5UNIQUE`/  -- UNIQUE KEY `MD5UNIQUE`/
s/^  UNIQUE KEY `MD5` (`MD5`),/  --   UNIQUE KEY `MD5` (`MD5`),/
s/^  UNIQUE KEY `md5_unique` (`md5`) USING BTREE,/  -- UNIQUE KEY `md5_unique` (`md5`) USING BTREE,/
s/^  KEY /  -- KEY /
s/^  FULLTEXT KEY /  -- FULLTEXT KEY /
/^INSERT INTO `fiction_hashes` (/d
/^INSERT INTO `description_edited` (/d
/^INSERT INTO `hashes` (/d
/^INSERT INTO `topics` (/d
/^INSERT INTO `updated_edited` (/d
/^INSERT INTO `description` (/d
/^INSERT INTO `fiction_description` (/d
