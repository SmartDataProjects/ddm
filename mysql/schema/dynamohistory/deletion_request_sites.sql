CREATE TABLE `deletion_request_sites` (
  `request_id` int(10) unsigned NOT NULL,
  `site_id` int(10) unsigned NOT NULL,
  KEY `request` (`request_id`),
  KEY `site` (`site_id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
