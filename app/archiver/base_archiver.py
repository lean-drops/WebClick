# app/archiver/base_archiver.py

import os
import csv
import shutil
from pathlib import Path
from abc import ABC, abstractmethod
import logging
from hashlib import sha256
from typing import List, Dict
from datetime import datetime

logger = logging.getLogger("archiver_logger")

HASH_LEN = 16

class BaseArchiver(ABC):
    def __init__(self, source_dir: str, backup_dir: str):
        self.source_dir = Path(source_dir)
        self.backup_dir = Path(backup_dir)
        self.manifest = []
        os.makedirs(self.backup_dir, exist_ok=True)
        logger.info(f"Initialized archiver with source: {self.source_dir} and backup: {self.backup_dir}")

    def backup(self):
        self.manifest = self.hash_all()
        timestamp = self.current_time()
        self.write_manifest(timestamp, self.manifest)
        self.copy_files()
        return self.manifest

    @abstractmethod
    def write_manifest(self, timestamp: str, manifest: List[Dict[str, str]]):
        pass

    @abstractmethod
    def copy_files(self):
        pass

    def hash_all(self) -> List[Dict[str, str]]:
        result = []
        for file_path in self.source_dir.rglob("*.*"):
            if file_path.is_file():
                with open(file_path, "rb") as f:
                    data = f.read()
                hash_code = sha256(data).hexdigest()[:HASH_LEN]
                relative_path = file_path.relative_to(self.source_dir).as_posix()
                result.append({"filename": relative_path, "hash": hash_code})
        logger.info(f"Hashed {len(result)} files.")
        return result

    def current_time(self) -> str:
        return datetime.utcnow().strftime("%Y%m%d%H%M%S")

