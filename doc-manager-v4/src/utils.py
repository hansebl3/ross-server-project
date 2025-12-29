import uuid6
import hashlib
import os
import re
from typing import Dict, Any, Tuple, Optional, List

def extract_tags(content: str) -> List[str]:
    """
    Extracts keywords from 'keywords:' section and sanitizes them 
    into valid Obsidian tags (no spaces, no brackets).
    """
    tags = []
    # Match keywords block: "keywords:" followed by bullet points
    kw_match = re.search(r'keywords:\s*\n((?:\s*-\s*.*\n?)+)', content, re.IGNORECASE)
    if kw_match:
        kw_block = kw_match.group(1)
        for line in kw_block.split('\n'):
            if line.strip() and '- ' in line:
                # 1. Remove bullet '- '
                # 2. Remove brackets '[' and ']'
                clean = line.strip().replace('- ', '').replace('[', '').replace(']', '').strip()
                # 3. Replace spaces with underscores
                tag = clean.replace(' ', '_')
                if tag:
                    tags.append(tag)
    return tags

def generate_uuid_v7() -> str:
    """Generates a time-sortable UUID v7 string."""
    return str(uuid6.uuid7())

def calculate_file_hash(content: str, path: str) -> str:
    """
    Calculates a consistent hash for a file based on its content and path.
    """
    normalized_content = content.replace('\r\n', '\n')
    data = f"{path}|{normalized_content}".encode('utf-8')
    data = f"{path}|{normalized_content}".encode('utf-8')
    return hashlib.sha256(data).hexdigest()

def set_file_permissions(path: str, uid: int = 1000, gid: int = 1000):
    """
    Sets ownership and permissions for a file, and touches parent directory
    to ensure watchers (like Obsidian) detect the change.
    """
    try:
        # Set ownership to host user (default: ross/1000)
        os.chown(path, uid, gid)
        # Set rw-r--r--
        os.chmod(path, 0o644)
        
        # Touch parent directory to force-trigger watchers
        parent_dir = os.path.dirname(path)
        os.utime(parent_dir, None)
    except Exception as e:
        # Log or ignore if permission denied (e.g. running as non-root)
        print(f"Warning: Failed to set permissions/touch for {path}: {e}")

def parse_frontmatter(content: str) -> Tuple[Dict[str, Any], str]:
    """
    Parses YAML frontmatter and returns (metadata, remaining_body).
    """
    if not content.strip().startswith('---'):
        return {}, content.strip()
    
    try:
        parts = content.split('---', 2)
        if len(parts) >= 3:
            metadata = yaml.safe_load(parts[1]) or {}
            body = parts[2].strip()
            return metadata, body
    except Exception:
        pass
        
    return {}, content.strip()

class PathManager:
    """
    Centralizes path generation logic for the Shadow Library, preserving sub-directories.
    """
    def __init__(self, shadow_root: str):
        self.shadow_root = os.path.abspath(shadow_root)
        self.l1_root = os.path.join(self.shadow_root, "L1")
        self.l2_root = os.path.join(self.shadow_root, "L2")

    def _get_sub_path(self, category: str, original_path: str) -> Tuple[str, str]:
        """
        Extracts the sub-directory structure after the category.
        Example: 01_Sources/Personal/Journal/entry.md -> ('Journal', '[L1] entry.md')
        """
        parts = original_path.split(os.sep)
        try:
            # Find the index of the category to get everything after it
            idx = parts.index(category)
            sub_dirs = parts[idx+1:-1]
            filename = parts[-1]
            return os.path.join(*sub_dirs) if sub_dirs else "", filename
        except (ValueError, IndexError):
            return "", parts[-1]

    def get_l1_dir(self, category: str, sub_path: str = "") -> str:
        return os.path.join(self.l1_root, category, sub_path)

    def get_l1_path(self, category: str, original_path: str) -> str:
        sub_dir, filename = self._get_sub_path(category, original_path)
        return os.path.join(self.get_l1_dir(category, sub_dir), f"[L1] {filename}")

    def get_l1_review_dir(self, category: str, sub_path: str = "") -> str:
        return os.path.join(self.get_l1_dir(category, sub_path), "Reviews")

    def get_l1_review_path(self, category: str, shadow_path: str) -> str:
        # Note: shadow_path is already the [L1] ... path
        # We place reviews in a 'Reviews' subfolder relative to the shadow file
        base_dir = os.path.dirname(shadow_path)
        filename = os.path.basename(shadow_path).replace(".md", ".review.md")
        return os.path.join(base_dir, "Reviews", filename)

    def get_l2_dir(self, category: str) -> str:
        return os.path.join(self.l2_root, category)

    def get_l2_path(self, category: str, safe_title: str) -> str:
        return os.path.join(self.get_l2_dir(category), f"[L2] {safe_title}.md")

    def get_l2_review_dir(self, category: str) -> str:
        return os.path.join(self.get_l2_dir(category), "Reviews")

    def get_l2_review_path(self, category: str, safe_title: str) -> str:
        return os.path.join(self.get_l2_review_dir(category), f"[L2] {safe_title}.review.md")

    def ensure_dirs_for_path(self, target_path: str):
        """Ensures that the directory for the given path exists."""
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
