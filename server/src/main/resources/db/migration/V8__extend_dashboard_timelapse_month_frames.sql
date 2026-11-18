ALTER TABLE dashboard_timelapse_station_frame
    ADD COLUMN IF NOT EXISTS frame_index INTEGER,
    ADD COLUMN IF NOT EXISTS frame_date DATE;

UPDATE dashboard_timelapse_station_frame frame
SET frame_index = frame.frame_hour,
    frame_date = period.start_date
FROM dashboard_timelapse_period period
WHERE frame.period_id = period.id
  AND (frame.frame_index IS NULL OR frame.frame_date IS NULL);

ALTER TABLE dashboard_timelapse_station_frame
    ALTER COLUMN frame_index SET NOT NULL,
    ALTER COLUMN frame_date SET NOT NULL;

ALTER TABLE dashboard_timelapse_station_frame
    DROP CONSTRAINT IF EXISTS uq_dashboard_timelapse_station_frame;

ALTER TABLE dashboard_timelapse_station_frame
    ADD CONSTRAINT uq_dashboard_timelapse_station_frame
        UNIQUE (period_id, frame_index, station_id);

CREATE INDEX IF NOT EXISTS idx_dashboard_timelapse_frame_period_index
    ON dashboard_timelapse_station_frame (period_id, frame_index);

CREATE INDEX IF NOT EXISTS idx_dashboard_timelapse_frame_period_date_hour
    ON dashboard_timelapse_station_frame (period_id, frame_date, frame_hour);
