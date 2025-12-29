import threading
import yaml

# Shared cache to track paths recently written by the system (AI)
# key: absolute path, value: file hash
_last_system_writes = {}
_lock = threading.Lock()

# Per-UUID build locks to prevent concurrent builds
_active_builds = set()
_build_lock = threading.Lock()

def mark_system_write(path: str, file_hash: str):
    with _lock:
        _last_system_writes[path] = file_hash

def is_system_write(path: str, file_hash: str) -> bool:
    with _lock:
        stored_hash = _last_system_writes.get(path)
        return stored_hash == file_hash

def clear_system_write(path: str):
    with _lock:
        if path in _last_system_writes:
            del _last_system_writes[path]

def try_acquire_build(uuid: str) -> bool:
    with _build_lock:
        if uuid in _active_builds:
            return False
        _active_builds.add(str(uuid))
        return True

def release_build(uuid: str):
    with _build_lock:
        u_str = str(uuid)
        if u_str in _active_builds:
            _active_builds.remove(u_str)

def format_frontmatter(metadata: dict, body: str) -> str:
    """Helper to generate standard YAML frontmatter."""
    fm = yaml.safe_dump(metadata, allow_unicode=True, default_flow_style=False)
    return f"---\n{fm}---\n\n{body}"
