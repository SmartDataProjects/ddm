CREATE TABLE `sites` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `name` varchar(32) CHARACTER SET latin1 COLLATE latin1_general_cs NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
