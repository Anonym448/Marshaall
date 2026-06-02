-- 002_evolution.sql - Evolución del esquema para SIEM completo
-- Ejecutar después de 001_schema.sql

-- =============================================================
-- 1. EXTENDER events: campos de Suricata que faltan
-- =============================================================
ALTER TABLE events
  ADD COLUMN IF NOT EXISTS flow_id   BIGINT       NULL AFTER severity,
  ADD COLUMN IF NOT EXISTS src_port  INT          NULL AFTER flow_id,
  ADD COLUMN IF NOT EXISTS dest_port INT          NULL AFTER src_port,
  ADD COLUMN IF NOT EXISTS category  VARCHAR(100) NULL AFTER dest_port,
  ADD INDEX IF NOT EXISTS idx_events_flow (flow_id);

-- =============================================================
-- 2. ALERTAS: estado y gestión
-- =============================================================
CREATE TABLE IF NOT EXISTS alert_status (
  event_id    BIGINT NOT NULL,
  status      ENUM('nueva','investigacion','cerrada') NOT NULL DEFAULT 'nueva',
  assigned_to VARCHAR(50) NULL,
  updated_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  updated_by  VARCHAR(50) NULL,
  PRIMARY KEY (event_id),
  CONSTRAINT fk_alert_event FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS alert_comments (
  id         BIGINT AUTO_INCREMENT PRIMARY KEY,
  event_id   BIGINT NOT NULL,
  author     VARCHAR(50) NOT NULL,
  body       TEXT NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_alertcomment_event FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE,
  INDEX idx_alertcomment_event (event_id)
);

-- =============================================================
-- 3. INCIDENTES
-- =============================================================
CREATE TABLE IF NOT EXISTS incidents (
  id          BIGINT AUTO_INCREMENT PRIMARY KEY,
  title       VARCHAR(200) NOT NULL,
  description TEXT NULL,
  severity    TINYINT NOT NULL DEFAULT 3,
  status      ENUM('abierto','en_progreso','cerrado') NOT NULL DEFAULT 'abierto',
  created_by  VARCHAR(50) NOT NULL,
  tags        VARCHAR(500) NULL,
  created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_incident_status (status),
  INDEX idx_incident_severity (severity)
);

CREATE TABLE IF NOT EXISTS incident_alerts (
  incident_id BIGINT NOT NULL,
  event_id    BIGINT NOT NULL,
  added_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  added_by    VARCHAR(50) NULL,
  PRIMARY KEY (incident_id, event_id),
  CONSTRAINT fk_ia_incident FOREIGN KEY (incident_id) REFERENCES incidents(id) ON DELETE CASCADE,
  CONSTRAINT fk_ia_event    FOREIGN KEY (event_id)    REFERENCES events(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS incident_comments (
  id          BIGINT AUTO_INCREMENT PRIMARY KEY,
  incident_id BIGINT NOT NULL,
  author      VARCHAR(50) NOT NULL,
  body        TEXT NOT NULL,
  created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_ic_incident FOREIGN KEY (incident_id) REFERENCES incidents(id) ON DELETE CASCADE,
  INDEX idx_ic_incident (incident_id)
);

-- =============================================================
-- 4. USUARIOS: añadir rol analista y campo active
-- =============================================================
ALTER TABLE users
  MODIFY COLUMN role ENUM('admin','analista','viewer') NOT NULL DEFAULT 'viewer';

ALTER TABLE users
  ADD COLUMN IF NOT EXISTS active TINYINT(1) NOT NULL DEFAULT 1;
