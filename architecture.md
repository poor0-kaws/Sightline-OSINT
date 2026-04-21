# Architecture Notes

Data Flow: fetch -> save raw -> clean -> decide same thing -> create links -> store in graph -> show in UI
+-------------------+
  |   DATA SOURCES    |
  |-------------------|
  | APIs              |
  | CSV uploads       |
  | Web scrapers      |
  | Webhooks          |
  | Manual input      |
  +---------+---------+
            |
            v
  +-------------------+
  |  INGESTION LAYER  |
  |-------------------|
  | Accepts incoming  |
  | data from many    |
  | different shapes  |
  | and formats       |
  +---------+---------+
            |
            v
  +-------------------+
  |  JOB / TASK QUEUE |
  |-------------------|
  | Stores work that  |
  | needs to happen   |
  | Example:          |
  | - fetch API       |
  | - run scraper     |
  | - parse CSV       |
  | - retry failed job|
  +---------+---------+
            |
            v
  +-------------------+
  |   WORKERS         |
  |-------------------|
  | Celery workers    |
  | pick up jobs and  |
  | do the actual     |
  | fetching/parsing  |
  +---------+---------+
            |
            v
  +-------------------+
  |   RAW STORAGE     |
  |-------------------|
  | Save original     |
  | payloads first    |
  | Example:          |
  | - raw JSON        |
  | - raw CSV row     |
  | - raw HTML page   |
  | - raw webhook     |
  +---------+---------+
            |
            v
  +-------------------+
  | NORMALIZATION     |
  |-------------------|
  | Convert messy     |
  | source-specific   |
  | data into one     |
  | standard format   |
  | Example types:    |
  | - Person          |
  | - Email           |
  | - Domain          |
  | - IP              |
  | - Company         |
  +---------+---------+
            |
            v
  +-------------------+
  | ENTITY RESOLUTION |
  |-------------------|
  | Decide when two   |
  | records are the   |
  | same real thing   |
  | Example:          |
  | "Jon Smith" and   |
  | "Jonathan Smith"  |
  | may be same person|
  +---------+---------+
            |
            v
  +-------------------+
  | RELATIONSHIP      |
  | EXTRACTION        |
  |-------------------|
  | Create links      |
  | between entities  |
  | Example:          |
  | Person -> uses -> |
  | Email             |
  | Domain -> points  |
  | to -> IP          |
  +---------+---------+
            |
            v
  +-------------------+
  | GRAPH DATABASE    |
  |-------------------|
  | Neo4j stores:     |
  | - entities        |
  | - relationships   |
  | - source links    |
  | - timestamps      |
  | - confidence      |
  +---------+---------+
            |
            v
  +-------------------+
  | INVESTIGATION API |
  |-------------------|
  | FastAPI reads and |
  | writes graph data |
  | for the frontend  |
  +---------+---------+
            |
            v
  +-------------------+
  | INVESTIGATION UI  |
  |-------------------|
  | React canvas UI   |
  | shows:            |
  | - graph           |
  | - node details    |
  | - evidence        |
  | - annotations     |
  | - reports         |
  +-------------------+

