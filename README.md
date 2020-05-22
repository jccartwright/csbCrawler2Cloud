# csbCrawler2Cloud
Python script to load csb data to s3 buckets. Python 3 recommended.

### Environment variable
Assumes
 -  `CSBCRAWLER` is set to the root of this project
    - If you are at the project root, run 
    ```bash
       $ export CSBCRAWLER=`pwd`
    ```
    - To confirm the current value
    ```bash
       $ printenv CSBCRAWLER
       /Users/ktanaka/src/github/cedardevs/csbCrawler2Cloud
    ```

### Libraries
Uses
 - boto3
 - pyyaml
 - geopandas
 
Example installation command: `pip3 install --user boto3`

### File convention assumed  
The data lands on NCEI disk as a tarball with 3 files:
 - YYYYMMDD_uuid_geojson.json
 - YYYYMMDD_uuid_metadata.json
 - YYYYMMDD_uuid_pointData.xyz
 
 
 
### Athena Notes
-- Generate timestamp column
 SELECT *, from_iso8601_timestamp("xyz"."time") ts FROM csbathenadb.xyz 

-- Create parquet table 
CREATE TABLE csbathenadb.csb_mv
WITH (
  format='PARQUET',
  external_location='s3://csbxyzfiles/optimized/'
) AS SELECT
  xyz.*
, "metadata"."name"
, "metadata"."provider"
FROM
  xyz
, metadata
WHERE ("xyz"."uuid" = "metadata"."uuid")

-- Query using dates
SELECT
  *
FROM
  xyz
WHERE
  from_iso8601_timestamp("xyz"."time")
BETWEEN 
  from_iso8601_timestamp('2015-01-01T00:00:00') 
AND 
  from_iso8601_timestamp('2019-01-01T23:59:00')   
  
### Example Request 
{
  "uuid": "",
  "email": "david.neufeld@colorado.edu",
  "platform.name": "Tenacity",
  "bbox": "-140.0,24.0,-111.0,32.0",
  "sdate": "2015-01-01T00:00:00",
  "edate": "2019-01-01T23:59:00"
}

## Dev Notes
### tar.gz Manifest
Refering to this article for generating md5sum on a file:
https://stackoverflow.com/questions/3431825/generating-an-md5-checksum-of-a-file
