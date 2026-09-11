import os
import uuid
from datetime import datetime
from abc import ABC, abstractmethod


class StorageBackend(ABC):

    @abstractmethod
    def save(self, file_data, finding_id, filename, variant):
        pass

    @abstractmethod
    def delete(self, path):
        pass

    @abstractmethod
    def exists(self, path):
        pass


class LocalStorage(StorageBackend):

    def __init__(self, media_root):
        self.media_root = media_root

    def _build_path(self, finding_id, filename, variant):
        now = datetime.utcnow()
        safe_name = f"{variant}_{uuid.uuid4().hex[:12]}.jpg"
        if filename.endswith(".webp"):
            safe_name = f"{variant}_{uuid.uuid4().hex[:12]}.webp"
        rel_dir = os.path.join(str(now.year), f"{now.month:02d}", finding_id)
        rel_path = os.path.join(rel_dir, safe_name)
        abs_dir = os.path.join(self.media_root, rel_dir)
        os.makedirs(abs_dir, exist_ok=True)
        return rel_path, os.path.join(self.media_root, rel_path)

    def save(self, file_data, finding_id, filename, variant):
        rel_path, abs_path = self._build_path(finding_id, filename, variant)
        if hasattr(file_data, "save"):
            file_data.save(abs_path)
        else:
            with open(abs_path, "wb") as f:
                f.write(file_data)
        return rel_path

    def save_bytes(self, data, finding_id, ext, variant):
        now = datetime.utcnow()
        safe_name = f"{variant}_{uuid.uuid4().hex[:12]}.{ext}"
        rel_dir = os.path.join(str(now.year), f"{now.month:02d}", finding_id)
        rel_path = os.path.join(rel_dir, safe_name)
        abs_dir = os.path.join(self.media_root, rel_dir)
        os.makedirs(abs_dir, exist_ok=True)
        abs_path = os.path.join(self.media_root, rel_path)
        with open(abs_path, "wb") as f:
            f.write(data)
        return rel_path

    def delete(self, path):
        abs_path = os.path.join(self.media_root, path)
        if os.path.exists(abs_path):
            os.remove(abs_path)

    def exists(self, path):
        abs_path = os.path.join(self.media_root, path)
        return os.path.exists(abs_path)

    def get_abs_path(self, rel_path):
        return os.path.join(self.media_root, rel_path)
