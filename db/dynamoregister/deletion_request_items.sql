DROP TABLE IF EXISTS `deletion_request_items`;

CREATE TABLE `deletion_request_items` (
  `request_id` int(10) unsigned NOT NULL,
  `item` varchar(512) CHARACTER SET latin1 COLLATE latin1_general_cs NOT NULL,
  KEY `request` (`request_id`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;
