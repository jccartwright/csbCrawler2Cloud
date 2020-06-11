# Extract CSB files

from datetime import datetime, timezone
import json
import os
import sys
import tarfile
from tarfile import TarFile
from typing import Any, Union

import yaml
import app.spatialutil as spatial_util
import hashlib


class CsbCrawler:
    output_dir = ""
    data_dir = ""
    bucket = ""
    test_data_dir = ""
    manifest_file = ""

    enable_upload = False
    access_key = ""
    secret_key = ""

    metadata = []

    @staticmethod
    def time_formatter(obs_time_str):
        try:
            obs_time = datetime.strptime(obs_time_str, '%Y%m%dT%H%M%SZ')
            return obs_time.isoformat("T", timespec="seconds")
        except ValueError as ve:
            print("Invalid date format, skipping...")
            return None

    def add_uuid_to_csv(self, tar, tar_info):
        csv_file = tar.extractfile(tar_info)
        file_name = os.path.basename(tar_info.name)
        uuid = file_name[9:41]

        print("Adding " + uuid + " to csv")
        new_file_name = self.output_dir + "working/" + file_name[:-4] + ".csv"
        new_csv_file = open(new_file_name, "w+")
        new_csv_file.write("UUID,LON,LAT,DEPTH,TIME,PLATFORM_NAME,PROVIDER\n")

        # Skip header
        csv_file.readline()
        cnt = 1

        # Loop through csv_file and write info back out with uuid included.
        for _ in csv_file:
            # TODO add more validation checks?
            line = (csv_file.readline()).decode("UTF-8").strip()
            tokens = line.split(",")

            if len(tokens) == 4:
                obs_time_str = tokens[3]
                obs_time = self.time_formatter(obs_time_str)
                if (obs_time != None):
                    new_line = uuid + "," + tokens[1] + "," + tokens[0] + "," + tokens[2] + "," + obs_time + "," + self.metadata["platform"]["name"] + "," + self.metadata["providerContactPoint"]["orgName"]
                    #print("Line {}: {}".format(cnt, new_line))
                    new_csv_file.write(new_line + "\n")

            cnt += 1

        csv_file.close()
        new_csv_file.close()
        # Perform spatial join on new csv file
        pts_to_share = spatial_util.spatial_join(self, new_csv_file.name)

        if pts_to_share is not None:
            # Remove unnecessary columns
            pts_to_share = pts_to_share[['UUID', 'LON', 'LAT', 'DEPTH', 'TIME', 'PLATFORM_NAME', 'PROVIDER']]

            # Write back out as a csv
            pts_to_share.to_csv(self.output_dir + "csv/" + file_name[:-4] + "_filtered.csv", index=False)

    def parse_metadata(self, metadata_file):
        # Date is represented in filename YYYYMMDD
        file_name = os.path.basename(metadata_file.name)
        metadata = json.load(metadata_file)
        print(metadata)
        return metadata

    # Extract file
    def extract_metadata(self, tar):
        metadata = None
        for tar_info in tar:

            if tar_info.isreg() and tar_info.name[-13:] == "metadata.json":
                file = tar.extractfile(tar_info)
                metadata = self.parse_metadata(file)
                break

        return metadata

    def process_csv_files(self, tar):
        for tar_info in tar:

            if tar_info.isreg() and (tar_info.name[-4:] == ".xyz"):
                if tar_info.name[-4:] == ".xyz":
                    print("extracting... " + tar_info.name)
                    self.add_uuid_to_csv(tar, tar_info)



    # Print every file with its size recursing through dirs
    def recurse_dir(self, dir_path):
        for item in os.listdir(dir_path):
            item_full_path = os.path.join(dir_path, item)

            if os.path.isdir(item_full_path):
                self.recurse_dir(item_full_path)
            else:
                if item[-7:] == ".tar.gz":
                    # Get md5 checksum of file
                    hash_md5 = hashlib.md5()
                    with open(item_full_path, "rb") as f:
                        for chunk in iter(lambda: f.read(4096), b""):
                            hash_md5.update(chunk)
                    md5sum = hash_md5.hexdigest()
                    # Get file stats
                    stat = os.stat(item_full_path)
                    isodate = datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat()
                    fileinfo = "%s, %s bytes, %s, md5sum=%s" % (item_full_path, stat.st_size, isodate, md5sum)
                    print(fileinfo)
                    # Write manifest entry
                    with open(self.manifest_file, "a") as mf:
                        mf.write(fileinfo + "\n")
                    tar: Union[TarFile, Any] = tarfile.open(item_full_path, "r:gz")
                    self.metadata = self.extract_metadata(tar)
                    self.process_csv_files(tar)
                    tar.close()

    def __init__(self, root_dir):
        print("root_dir=" + root_dir)
        with open(root_dir + "/config/config.yaml") as f:
            docs = yaml.load(f, Loader=yaml.FullLoader)
            # Use config _dir values as-is if they are absolute (start with '/'), otherwise, they are relative to root_dir.
            self.output_dir    = docs["output_dir"]    if docs["output_dir"].startswith('/')    else (root_dir + '/' + docs["output_dir"])
            self.data_dir      = docs["data_dir"]      if docs["data_dir"].startswith('/')      else (root_dir + '/' + docs["data_dir"])
            self.test_data_dir = docs["test_data_dir"] if docs["test_data_dir"].startswith('/') else (root_dir + '/' + docs["test_data_dir"])
            self.manifest_file = docs["manifest_file"] if docs["manifest_file"].startswith('/') else (root_dir + '/' + docs["manifest_file"])
            if os.path.exists(self.manifest_file):
                sys.exit("Manifest file must not exist at start: " + self.manifest_file)
            self.enable_upload = docs["enable_upload"]
            print("Uploads enabled: %s" % (self.enable_upload))
            self.bucket = docs["bucket"]

        # Load credentials
        with open(root_dir + "/config/credentials.yaml") as f:
            secrets = yaml.load(f, Loader=yaml.FullLoader)
            self.access_key = secrets["ACCESS_KEY"]
            self.secret_key = secrets["SECRET_KEY"]
