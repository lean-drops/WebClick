# app/archiver/local_archiver.py

import csv
from pathlib import Path
from typing import List, Dict
import shutil
import json
from .base_archiver import BaseArchiver, logger


class LocalArchiver(BaseArchiver):
    def __init__(self, source_dir: str, backup_dir: str, manifest_format: str = "csv"):
        super().__init__(source_dir, backup_dir)
        self.manifest_format = manifest_format.lower()

    def write_manifest(self, timestamp: str, manifest: List[Dict[str, str]]):
        manifest_file = self.backup_dir / f"{timestamp}.{self.manifest_format}"
        if self.manifest_format == "csv":
            with open(manifest_file, "w", newline='') as f:
                writer = csv.DictWriter(f, fieldnames=["filename", "hash"])
                writer.writeheader()
                writer.writerows(manifest)
        elif self.manifest_format == "json":
            with open(manifest_file, "w") as f:
                json.dump(manifest, f, indent=4)
        logger.info(f"Manifest written to {manifest_file}")

    def copy_files(self):
        for entry in self.manifest:
            source_path = self.source_dir / entry["filename"]
            backup_path = self.backup_dir / f"{entry['hash']}.bck"
            if not backup_path.exists():
                shutil.copy2(source_path, backup_path)
                logger.info(f"Copied {source_path} to {backup_path}")
            else:
                logger.info(f"Backup already exists for {source_path}")
