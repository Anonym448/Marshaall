CREATE TABLE IF NOT EXISTS users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(50) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  role ENUM('admin','viewer') NOT NULL DEFAULT 'viewer',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS events (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  ts DATETIME(6) NOT NULL,
  event_type VARCHAR(50) NULL,
  src_ip VARCHAR(45) NULL,
  dest_ip VARCHAR(45) NULL,
  proto VARCHAR(16) NULL,
  signature VARCHAR(255) NULL,
  severity TINYINT NULL,
  raw_json LONGTEXT NOT NULL,

  INDEX idx_events_ts (ts),
  INDEX idx_events_type (event_type),
  INDEX idx_events_severity (severity),
  INDEX idx_events_signature (signature)
);
