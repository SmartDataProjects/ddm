<?php

include_once(__DIR__ . '/../dynamo/common/db_conf.php');
include_once(__DIR__ . '/common.php');

// General note:
// MySQL DATETIME accepts and returns local time. Always use UNIX_TIMESTAMP and FROM_UNIXTIME to interact with the DB.

class ActivityLock {
  private $_db = NULL;
  private $_uid = 0;
  private $_uname = '';
  private $_sid = 0;
  private $_sname = '';
  private $_read_only = true;
  private $_apps = array();

  public function __construct($cert_dn, $issuer_dn, $service, $as_user = NULL)
  {
    global $db_conf;

    // get the list of application names from information_schema
    $info_schema = new mysqli($db_conf['host'], $db_conf['user'], $db_conf['password'], 'information_schema');
    $query = 'SELECT `COLUMN_TYPE` FROM `COLUMNS` WHERE `TABLE_SCHEMA` = "dynamoregister" AND `TABLE_NAME` = "activity_lock" AND `COLUMN_NAME` = "application"';
    $stmt = $info_schema->prepare($query);
    $stmt->bind_result($types);
    $stmt->execute();
    $stmt->fetch();
    $stmt->close();

    foreach (explode(',', substr($types, 5, strlen($types) - 6)) as $quoted)
      $this->_apps[] = trim($quoted, " '\"");

    $this->_db = new mysqli($db_conf['host'], $db_conf['user'], $db_conf['password'], 'dynamoregister');

    $authorized = get_user($this->_db, $cert_dn, $issuer_dn, $service, $as_user, $this->_uid, $this->_uname, $this->_sid);

    if ($this->_uid == 0 || $this->_sid == 0)
      $this->send_response(400, 'BadRequest', 'Unknown user');

    $this->_read_only = !$authorized;
  }

  public function execute($command, $request)
  {
    if (!in_array($command, array('check', 'lock', 'unlock')))
      $this->send_response(400, 'BadRequest', 'Invalid command (possible values: check, lock, unlock)');

    if ($command != 'check' && $this->_read_only)
      $this->send_response(400, 'BadRequest', 'User not authorized');

    $this->sanitize_request($command, $request);

    if ($command == 'check') {
      $this->exec_check($request);
    }
    else if ($command == 'lock') {
      $this->exec_lock($request);
    }
    else if ($command == 'unlock') {
      $this->exec_unlock($request);
    }
  }

  private function exec_check($request)
  {
    $query = 'SELECT `users`.`name`, `services`.`name`, `activity_lock`.`timestamp`, `activity_lock`.`note` FROM `activity_lock`';
    $query .= ' INNER JOIN `users` ON `users`.`id` = `activity_lock`.`user_id`';
    $query .= ' INNER JOIN `services` ON `services`.`id` = `activity_lock`.`service_id`';
    $query .= ' WHERE `activity_lock`.`application` = ?';
    $query .= ' ORDER BY `activity_lock`.`timestamp` ASC LIMIT 1';

    $stmt = $this->_db->prepare($query);
    $stmt->bind_param('s', $request['app']);
    $stmt->bind_result($uname,  $sname, $timestamp, $note);
    $stmt->execute();
    $active = $stmt->fetch();
    $stmt->close();

    if (!$active)
      $this->send_response(200, 'OK', 'Not locked');

    $data = array();

    $data['user'] = $uname;
    if ($sname != 'user')
      $data['service'] = $sname;

    $data['timestamp'] = $timestamp;
    if ($note !== NULL)
      $data['note'] = $note;

    $this->send_response(200, 'OK', 'Locked', array($data));
  }

  private function exec_lock($request)
  {
    $this->lock_table(true);

    $query = 'SELECT `user_id`, `service_id` FROM `activity_lock`';
    $query .= ' WHERE `application` = ? ORDER BY `timestamp` ASC';
    $stmt = $this->_db->prepare($query);
    $stmt->bind_param('s', $request['app']);
    $stmt->bind_result($uid, $sid);
    $stmt->execute();
    $num_locks = 0;
    while ($stmt->fetch()) {
      if ($num_locks == 0 && $uid == $this->_uid && $sid == $this->_sid) {
        // this user has the first lock
        $stmt->close();
        $this->send_response(200, 'OK', 'Application already locked');
      }

      ++$num_locks;
    }
    $stmt->close();

    $query = 'INSERT IGNORE INTO `activity_lock` (`user_id`, `service_id`, `application`, `timestamp`, `note`) VALUES (?, ?, ?, NOW(), ?)';
    $stmt = $this->_db->prepare($query);
    $stmt->bind_param('iiss', $this->_uid, $this->_sid, $request['app'], $note);
    $stmt->execute();
    $stmt->close();

    if ($num_locks == 0)
      $this->send_response(200, 'OK', 'Locked');
    else
      $this->send_response(200, 'WAIT', sprintf('Locked by %d other users', $num_locks));
  }

  private function exec_unlock($request)
  {
    $query = 'DELETE FROM `activity_lock` WHERE `user_id` = ? AND `service_id` = ? AND `application` = ?';
    $stmt = $this->_db->prepare($query);
    $stmt->bind_param('iis', $this->_uid, $this->_sid, $request['app']);
    $stmt->execute();
    $unlocked = ($stmt->affected_rows != 0);
    $stmt->close();

    if ($unlocked)
      $this->send_response(200, 'OK', 'Unlocked');
    else
      $this->send_response(200, 'OK', 'Application already unlocked');
  }

  private function sanitize_request($command, &$request)
  {
    $allowed_fields = array('app');

    if ($command == 'lock')
      $allowed_fields[] = 'note';

    foreach (array_keys($request) as $key) {
      if (in_array($key, $allowed_fields)) {
        $request[$key] = $this->_db->real_escape_string($request[$key]);
      }
      else
        unset($request[$key]);
    }

    if (!isset($request['app']))
      $this->send_response(400, 'BadRequest', 'No app given');
    else if(!in_array($request['app'], $this->_apps))
      $this->send_response(400, 'BadRequest', 'Unknown app');
  }

  private function lock_table($updating)
  {
    if ($updating)
      $query = 'LOCK TABLES `activity_lock` WRITE';
    else
      $query = 'UNLOCK TABLES';

    $this->_db->query($query);
  }

  private function send_response($code, $result, $message, $data = NULL)
  {
    // Table lock will be released at the end of the session. Explicit unlocking is in principle unnecessary.
    $this->lock_table(false);
    send_response($code, $result, $message, $data);
  }
}

?>
