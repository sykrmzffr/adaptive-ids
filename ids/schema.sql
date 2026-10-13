PRAGMA journal_mode = WAL;      -- dashboard can read while the IDS writes
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS traffic_log (
    log_id            INTEGER PRIMARY KEY,
    timestamp         REAL    NOT NULL,      -- unix time, end of the 5 s window
    source_ip         TEXT    NOT NULL,
    total_packets     INTEGER NOT NULL,
    flow_count        INTEGER NOT NULL,
    flow_duration     REAL,                  -- microseconds (longest flow in window)
    threat_score      REAL,                  -- NULL if the window was skipped
    threshold_at_time REAL,                  -- NULL during learning
    threshold_mode    TEXT    NOT NULL CHECK (threshold_mode IN ('adaptive','fixed')),
    status            TEXT    NOT NULL CHECK (status IN ('learning','normal','alert','skipped')),
    latency_ms        REAL                   -- for section 3.6.5
);
CREATE INDEX IF NOT EXISTS ix_traffic_time ON traffic_log(timestamp);
CREATE INDEX IF NOT EXISTS ix_traffic_ip   ON traffic_log(source_ip);

CREATE TABLE IF NOT EXISTS alerts (
    alert_id          INTEGER PRIMARY KEY,
    log_id            INTEGER NOT NULL REFERENCES traffic_log(log_id),
    timestamp         REAL    NOT NULL,
    source_ip         TEXT    NOT NULL,
    threat_score      REAL    NOT NULL,
    threshold_at_time REAL    NOT NULL,
    attack_class      TEXT                   -- NULL if the model is binary
);
CREATE INDEX IF NOT EXISTS ix_alerts_time ON alerts(timestamp);

CREATE TABLE IF NOT EXISTS blocked_ips (
    block_id    INTEGER PRIMARY KEY,
    alert_id    INTEGER REFERENCES alerts(alert_id),
    source_ip   TEXT    NOT NULL,
    block_start REAL    NOT NULL,
    block_end   REAL    NOT NULL,            -- block_start + 900 (15 minutes)
    status      TEXT    NOT NULL CHECK (status IN ('active','expired','removed'))
);
CREATE INDEX IF NOT EXISTS ix_blocked_status ON blocked_ips(status);
