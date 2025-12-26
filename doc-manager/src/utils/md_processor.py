import frontmatter
import uuid_utils as uuid
import re
import os
from datetime import datetime

class MDProcessor:
    @staticmethod
    def generate_uuid_v7(timestamp=None):
        if timestamp is not None:
            timestamp = int(timestamp)
        return str(uuid.uuid7(timestamp=timestamp))

    @staticmethod
    def get_date_from_uuid(uuid_str):
        """Extracts YYYY-MM-DD from a UUID v7 string. Returns today if failed."""
        try:
            uid = uuid.UUID(uuid_str)
            if uid.version == 7:
                # UUIDv7 timestamp is milliseconds since epoch in the first 48 bits
                # But the python uuid object might expose 'time' differently depending on version?
                # Actually, standard python uuid module doesn't fully support v7 properties directly in all versions yet.
                # But we can extract manually from int.
                # First 48 bits.
                ts_ms = uid.int >> 80
                dt = datetime.fromtimestamp(ts_ms / 1000.0)
                return dt.strftime("%Y-%m-%d")
        except:
            pass
        return datetime.today().strftime("%Y-%m-%d")

    @staticmethod
    def extract_uuid(content, filename=None):
        """
        Extract UUID from frontmatter or content.
        If filename is a UUID, use it.
        """
        # 1. Try frontmatter
        try:
            post = frontmatter.loads(content)
            if 'id' in post.metadata:
                return str(post.metadata['id']), post.content
            if 'uuid' in post.metadata:
                return str(post.metadata['uuid']), post.content
        except:
            pass

        # 2. Try regex (standard UUID pattern)
        uuid_pattern = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
        match = re.search(uuid_pattern, content, re.IGNORECASE)
        if match:
            # We assume the content remains the same unless it's specifically frontmatter
            return match.group(0), content

        # 3. Check filename
        if filename:
            name_without_ext = os.path.splitext(os.path.basename(filename))[0]
            if re.match(uuid_pattern, name_without_ext, re.IGNORECASE):
                return name_without_ext, content

        return None, content

    @staticmethod
    def prepare_metadata(content):
        """Extract basic keywords/metadata if possible from MD structure"""
        meta = {}
        try:
            post = frontmatter.loads(content)
            meta = post.metadata
        except:
            pass
        return meta
