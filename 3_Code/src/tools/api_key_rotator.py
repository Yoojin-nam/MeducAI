"""
API Key Rotator with Hybrid State Management

Features:
- Loads multiple API keys from .env (GOOGLE_API_KEY_1, GOOGLE_API_KEY_2, ..., no upper limit)
- Auto-detects all numbered keys in environment (supports any number of keys, e.g., GOOGLE_API_KEY_1 through GOOGLE_API_KEY_100+)
- Memory-based rotation: fast key switching within process
- File-based state tracking: failure timestamps (persists across processes)
- Automatic fallback on quota exhaustion (429 with "limit: 0")
- Thread-safe (for multi-threaded scenarios)

Usage:
    rotator = ApiKeyRotator(base_dir=Path("."))
    api_key = rotator.get_current_key()  # Get current active key
    client = build_client(api_key)
    
    try:
        result = client.call(...)
        rotator.record_success()
    except QuotaExhaustedError:
        rotator.rotate_on_quota_exhausted()  # Auto-rotate to next key
        api_key = rotator.get_current_key()
        client = build_client(api_key)
        result = client.call(...)

Tip (recommended ops):
  - Keep key numbering stable in `.env` (GOOGLE_API_KEY_1/2/3... should map to fixed accounts).
  - If you want to start a run from a specific key without renumbering, set:
      API_KEY_ROTATOR_START_INDEX=1   # 1-based (recommended)
    or:
      GOOGLE_API_KEY_START_INDEX=1    # also 1-based
"""

import json
import os
import re
import time
import threading
import tempfile
import copy
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from dotenv import load_dotenv


class ApiKeyRotator:
    """
    Hybrid API key rotator with memory + file-based state tracking.
    
    State file format (JSON):
    {
        "keys": {
            "GOOGLE_API_KEY_1": {
                "daily_requests": 0,
                "last_reset_date": "2025-12-25",
                "last_failure_time": null,
                "last_usage_time": null,
                "is_active": true,
                "failure_count": 0,
                "consecutive_failures": 0,
                "total_requests": 0
            },
            ...
        },
        "current_key_index": 0,
        "last_updated": "2025-12-25T20:00:00"
    }
    """
    
    def __init__(
        self,
        base_dir: Path,
        key_prefix: str = "GOOGLE_API_KEY",
        max_keys: Optional[int] = None,
        state_file: Optional[Path] = None,
    ):
        """
        Initialize API key rotator.
        
        Args:
            base_dir: Project base directory (for .env and state file)
            key_prefix: Environment variable prefix (default: "GOOGLE_API_KEY")
            max_keys: Maximum number of keys to load (None = auto-detect all available keys, no limit).
                      Recommended: use None to automatically detect all keys (GOOGLE_API_KEY_1, GOOGLE_API_KEY_2, ..., GOOGLE_API_KEY_N).
            state_file: Optional custom state file path (default: base_dir/2_Data/metadata/.api_key_status.json)
        """
        self.base_dir = Path(base_dir).resolve()
        self.key_prefix = key_prefix
        self.max_keys = max_keys
        # NOTE: record_success()/rotate_on_quota_exhausted() call _save_state(), which also
        # takes this lock. We therefore must use an RLock (re-entrant) to avoid deadlocks.
        self._lock = threading.RLock()
        # Separate lock to serialize filesystem writes without blocking state updates.
        self._file_lock = threading.Lock()
        # Background saver to keep record_success() fast under high concurrency.
        self._save_event = threading.Event()
        self._stop_event = threading.Event()
        self._bg_saver = threading.Thread(
            target=self._save_loop,
            name="ApiKeyRotatorSaver",
            daemon=True,
        )
        self._bg_saver.start()
        
        # Load .env
        env_path = self.base_dir / ".env"
        if env_path.exists():
            # Override=True so .env can intentionally control per-run behavior like
            # API_KEY_ROTATOR_START_INDEX, even if a parent process exported stale values.
            load_dotenv(dotenv_path=env_path, override=True)
        
        # Load keys from environment
        self.keys: List[str] = []
        self.key_numbers: List[int] = []  # Track actual key numbers (e.g., [1, 3, 5] if GOOGLE_API_KEY_1, _3, _5 exist)
        
        if max_keys is not None:
            # Legacy mode: load up to max_keys sequentially
            for i in range(1, max_keys + 1):
                key_name = f"{key_prefix}_{i}"
                key_value = os.getenv(key_name, "").strip()
                if key_value:
                    self.keys.append(key_value)
                    self.key_numbers.append(i)
        else:
            # Auto-detect mode: find all numbered keys (no upper limit)
            # Strategy: Scan environment variables to find all keys matching the pattern
            # This handles non-consecutive keys and any number of keys (e.g., GOOGLE_API_KEY_1, GOOGLE_API_KEY_2, ..., GOOGLE_API_KEY_100+)
            found_keys: Dict[int, str] = {}
            pattern = re.compile(rf"^{re.escape(key_prefix)}_(\d+)$")
            
            # Scan all environment variables
            for env_key, env_value in os.environ.items():
                match = pattern.match(env_key)
                if match:
                    key_num = int(match.group(1))
                    key_value = env_value.strip()
                    if key_value:  # Only add non-empty keys
                        found_keys[key_num] = key_value
            
            # Sort by key number and extract values (supports any number of keys)
            if found_keys:
                sorted_nums = sorted(found_keys.keys())
                self.keys = [found_keys[k] for k in sorted_nums]
                self.key_numbers = sorted_nums
        
        if not self.keys:
            # Fallback to single GOOGLE_API_KEY if numbered keys not found
            fallback_key = os.getenv("GOOGLE_API_KEY", "").strip()
            if fallback_key:
                self.keys = [fallback_key]
                self.key_numbers = [1]  # Use 1 as default number for single key
                print(f"[API Rotator] Warning: No numbered keys found, using single GOOGLE_API_KEY")
            else:
                raise RuntimeError(
                    f"[API Rotator] No API keys found. "
                    f"Expected {key_prefix}_1, {key_prefix}_2, ... or GOOGLE_API_KEY in .env"
                )
        
        # API Rotator initialization logging suppressed for cleaner terminal output
        # This info is logged to file via progress_logger if available
        
        # State file path
        if state_file is None:
            state_dir = self.base_dir / "2_Data" / "metadata"
            state_dir.mkdir(parents=True, exist_ok=True)
            self.state_file = state_dir / ".api_key_status.json"
        else:
            self.state_file = Path(state_file).resolve()
        
        # Load state from file
        self.state = self._load_state()
        
        # If state was cleaned up or index was fixed, save it immediately
        if self.state.pop("_needs_save", False):
            self._save_state()
        
        # Optional: override starting key index via environment (useful for per-run pinning).
        # - API_KEY_ROTATOR_START_INDEX: 1-based index (recommended)
        # - {KEY_PREFIX}_START_INDEX: 1-based index (e.g., GOOGLE_API_KEY_START_INDEX)
        #
        # Rationale: Avoid renumbering keys in .env (which changes key identity in the state file).
        # IMPORTANT: START_INDEX env var takes precedence over state file value.
        start_idx_env = os.getenv("API_KEY_ROTATOR_START_INDEX", "").strip()
        if not start_idx_env:
            start_idx_env = os.getenv(f"{self.key_prefix}_START_INDEX", "").strip()
        
        if start_idx_env:
            # START_INDEX is set: use it and ignore state file value
            try:
                start_1based = int(start_idx_env)
                if 1 <= start_1based <= len(self.keys):
                    self._current_index = start_1based - 1
                    self.state["current_key_index"] = self._current_index
                    # Persist immediately so subprocesses pick the same starting key.
                    self._save_state()
                    print(f"[API Rotator] Using START_INDEX={start_1based} from env (overriding state file)")
                else:
                    print(
                        f"[API Rotator] Warning: Invalid start index {start_1based} "
                        f"(valid range: 1..{len(self.keys)}). Falling back to state file."
                    )
                    # Fall back to state file value
                    self._current_index = self.state.get("current_key_index", 0) % len(self.keys)
            except Exception:
                print(f"[API Rotator] Warning: Could not parse start index env='{start_idx_env}'. Falling back to state file.")
                # Fall back to state file value
                self._current_index = self.state.get("current_key_index", 0) % len(self.keys)
        else:
            # No START_INDEX: use state file value (if available)
            # State file value is already validated in _load_state(), but double-check here
            saved_index = self.state.get("current_key_index", 0)
            if 0 <= saved_index < len(self.keys):
                self._current_index = saved_index
            else:
                print(f"[API Rotator] Warning: State file current_key_index ({saved_index}) is invalid. Using 0.")
                self._current_index = 0
                self.state["current_key_index"] = 0
                # Save corrected state immediately
                self._save_state()
        
        # Batch save counter (for performance optimization)
        self._unsaved_count = 0
        
        # Reset daily counters if needed
        self._reset_daily_counters_if_needed()
    
    def _load_state(self) -> Dict:
        """Load state from file, or return default state."""
        if not self.state_file.exists():
            return {
                "keys": {},
                "current_key_index": 0,
                "last_updated": datetime.now().isoformat(),
            }
        
        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                state = json.load(f)
            
            # Build set of currently available key IDs
            available_key_ids = {f"{self.key_prefix}_{num}" for num in self.key_numbers}
            
            # Clean up state: remove keys that no longer exist (commented out)
            keys_state = state.get("keys", {})
            removed_keys = []
            for key_id in list(keys_state.keys()):
                if key_id not in available_key_ids:
                    removed_keys.append(key_id)
                    del keys_state[key_id]
            
            # Track if cleanup occurred (for saving state)
            cleanup_occurred = len(removed_keys) > 0
            
            if cleanup_occurred:
                print(f"[API Rotator] Cleaned up {len(removed_keys)} key(s) from state file (no longer in environment): {', '.join(removed_keys)}")
            
            # Ensure all currently available keys have state entries
            for i, key in enumerate(self.keys):
                key_id = f"{self.key_prefix}_{self.key_numbers[i]}"
                if key_id not in state.get("keys", {}):
                    state.setdefault("keys", {})[key_id] = {
                        "daily_requests": 0,
                        "last_reset_date": datetime.now().date().isoformat(),
                        "last_failure_time": None,
                        "last_usage_time": None,
                        "is_active": True,
                        "failure_count": 0,
                        "consecutive_failures": 0,
                        "total_requests": 0,
                    }
                else:
                    # Ensure existing keys have new fields (backward compatibility)
                    key_state = state["keys"][key_id]
                    if "last_usage_time" not in key_state:
                        key_state["last_usage_time"] = None
                    if "consecutive_failures" not in key_state:
                        key_state["consecutive_failures"] = 0
                    if "total_requests" not in key_state:
                        key_state["total_requests"] = key_state.get("daily_requests", 0)
            
            # Validate and fix current_key_index if it's out of range
            saved_index = state.get("current_key_index", 0)
            index_fixed = False
            if saved_index < 0 or saved_index >= len(self.keys):
                print(f"[API Rotator] Warning: Saved current_key_index ({saved_index}) is out of range (0..{len(self.keys)-1}). Resetting to 0.")
                state["current_key_index"] = 0
                index_fixed = True
            
            # If cleanup or index fix occurred, mark state as needing save
            # (We'll save it in __init__ after loading)
            if cleanup_occurred or index_fixed:
                state["_needs_save"] = True
            
            return state
        except Exception as e:
            print(f"[API Rotator] Warning: Failed to load state file: {e}. Using defaults.")
            return {
                "keys": {},
                "current_key_index": 0,
                "last_updated": datetime.now().isoformat(),
            }
    
    def _save_loop(self) -> None:
        """
        Background saver loop.

        This keeps the hot path (record_success) from blocking on filesystem I/O.
        """
        while not self._stop_event.is_set():
            # Wake periodically so stop_event is respected even if no saves are pending.
            self._save_event.wait(timeout=0.5)
            if self._stop_event.is_set():
                break
            if not self._save_event.is_set():
                continue
            # Coalesce multiple save requests into a single save.
            self._save_event.clear()
            try:
                self._save_state_sync()
            except Exception as e:
                print(f"[API Rotator] Warning: Background save failed: {e}")

    def _save_state_sync(self) -> None:
        """
        Save state to file.

        Important: we do NOT hold the rotator state lock while doing filesystem I/O.
        Under high concurrency, holding the lock during json dump/rename can stall all workers.
        """
        # Snapshot state quickly under lock.
        with self._lock:
            self.state["last_updated"] = datetime.now().isoformat()
            state_snapshot = copy.deepcopy(self.state)

        # Serialize actual file writes (but do not block state updates).
        with self._file_lock:
            try:
                self.state_file.parent.mkdir(parents=True, exist_ok=True)
                # Atomic write: write to a unique temp file, then replace.
                with tempfile.NamedTemporaryFile(
                    mode="w",
                    encoding="utf-8",
                    delete=False,
                    dir=str(self.state_file.parent),
                    prefix=self.state_file.name + ".",
                    suffix=".tmp",
                ) as f:
                    json.dump(state_snapshot, f, indent=2, ensure_ascii=False)
                    temp_path = Path(f.name)
                os.replace(str(temp_path), str(self.state_file))
            except Exception as e:
                print(f"[API Rotator] Warning: Failed to save state file: {e}")
                try:
                    if "temp_path" in locals():
                        Path(temp_path).unlink(missing_ok=True)  # type: ignore[arg-type]
                except Exception:
                    pass

    def _save_state(self) -> None:
        """Compatibility wrapper for code paths that expect a synchronous save."""
        self._save_state_sync()
    
    def _reset_daily_counters_if_needed(self) -> None:
        """Reset daily request counters if a new day has started."""
        today = datetime.now().date().isoformat()
        updated = False
        
        for key_id in self.state.get("keys", {}):
            key_state = self.state["keys"][key_id]
            last_reset = key_state.get("last_reset_date", today)
            
            if last_reset != today:
                key_state["daily_requests"] = 0
                key_state["last_reset_date"] = today
                # Reactivate keys that failed yesterday (RPD reset)
                if not key_state.get("is_active", True):
                    key_state["is_active"] = True
                    key_state["failure_count"] = 0
                    key_state["consecutive_failures"] = 0
                    print(f"[API Rotator] Reactivated {key_id} (new day)")
                updated = True
        
        if updated:
            self._save_state()
    
    def get_current_key(self) -> str:
        """
        Get the current active API key.
        
        Returns:
            Current API key string
        
        Raises:
            RuntimeError: If all keys are inactive (exhausted). Keys will be automatically
                         reactivated when the day resets via _reset_daily_counters_if_needed().
        """
        with self._lock:
            # Find next active key if current is inactive
            attempts = 0
            while attempts < len(self.keys):
                key_index = self._current_index
                key_id = f"{self.key_prefix}_{self.key_numbers[key_index]}"
                key_state = self.state.get("keys", {}).get(key_id, {})
                
                if key_state.get("is_active", True):
                    return self.keys[key_index]
                
                # Current key is inactive, try next
                self._current_index = (self._current_index + 1) % len(self.keys)
                attempts += 1
            
            # All keys inactive - raise exception instead of auto-reactivate
            # This prevents infinite loops when all keys have been exhausted (e.g., during sleep/wait periods)
            # Keys will be reactivated automatically when the day resets (via _reset_daily_counters_if_needed)
            raise RuntimeError(
                f"[API Rotator] All {len(self.keys)} API keys are inactive (exhausted). "
                f"Please wait for quota reset (typically 24 hours) or manually reactivate keys. "
                f"Keys will be automatically reactivated when the day resets."
            )

    def set_current_index(self, index: int, *, persist: bool = True) -> None:
        """
        Force-select the current key index (0-based).

        Prefer using API_KEY_ROTATOR_START_INDEX / {KEY_PREFIX}_START_INDEX in .env
        for per-run pinning. This method is useful for programmatic switching.
        """
        with self._lock:
            idx = int(index) % len(self.keys)
            self._current_index = idx
            self.state["current_key_index"] = idx
            if persist:
                self._save_state()
    
    def record_success(self, batch_save: bool = True) -> None:
        """
        Record a successful API call (increment daily counter, reset consecutive failures).
        
        Args:
            batch_save: If True, only save to file every 10 calls (default: True for performance)
        """
        with self._lock:
            key_index = self._current_index
            key_id = f"{self.key_prefix}_{self.key_numbers[key_index]}"
            now_iso = datetime.now().isoformat()
            
            if key_id not in self.state.get("keys", {}):
                self.state.setdefault("keys", {})[key_id] = {
                    "daily_requests": 0,
                    "last_reset_date": datetime.now().date().isoformat(),
                    "last_failure_time": None,
                    "last_usage_time": None,
                    "is_active": True,
                    "failure_count": 0,
                    "consecutive_failures": 0,
                    "total_requests": 0,
                }
            
            key_state = self.state["keys"][key_id]
            key_state["daily_requests"] = key_state.get("daily_requests", 0) + 1
            key_state["total_requests"] = key_state.get("total_requests", 0) + 1
            key_state["last_usage_time"] = now_iso
            # Reset consecutive failures on success
            key_state["consecutive_failures"] = 0
            
            # Batch save for performance: only save every 10 calls
            if batch_save:
                if not hasattr(self, '_unsaved_count'):
                    self._unsaved_count = 0
                self._unsaved_count += 1
                if self._unsaved_count >= 10:
                    # Request a background save; do not block worker threads on disk I/O.
                    self._save_event.set()
                    self._unsaved_count = 0
            else:
                # Caller requested immediate durability; still avoid holding the state lock during I/O.
                # This is synchronous, but far less likely to stall other threads.
                self._save_state_sync()
    
    def record_failure(self, error_message: str = "", auto_rotate_threshold: int = 3) -> Optional[Tuple[str, int]]:
        """
        Record a failed API call and optionally auto-rotate if consecutive failures exceed threshold.
        
        Args:
            error_message: Error message from API (for logging)
            auto_rotate_threshold: Number of consecutive failures before auto-rotation (default: 3)
        
        Returns:
            (new_key, new_index) if auto-rotation occurred, None otherwise
        """
        with self._lock:
            key_index = self._current_index
            key_id = f"{self.key_prefix}_{self.key_numbers[key_index]}"
            now_iso = datetime.now().isoformat()
            
            if key_id not in self.state.get("keys", {}):
                self.state.setdefault("keys", {})[key_id] = {
                    "daily_requests": 0,
                    "last_reset_date": datetime.now().date().isoformat(),
                    "last_failure_time": None,
                    "last_usage_time": None,
                    "is_active": True,
                    "failure_count": 0,
                    "consecutive_failures": 0,
                    "total_requests": 0,
                }
            
            key_state = self.state["keys"][key_id]
            key_state["last_failure_time"] = now_iso
            key_state["last_usage_time"] = now_iso
            key_state["failure_count"] = key_state.get("failure_count", 0) + 1
            key_state["total_requests"] = key_state.get("total_requests", 0) + 1
            key_state["consecutive_failures"] = key_state.get("consecutive_failures", 0) + 1
            
            consecutive = key_state["consecutive_failures"]
            
            # Auto-rotate if consecutive failures exceed threshold
            if consecutive >= auto_rotate_threshold:
                print(
                    f"[API Rotator] {key_id} has {consecutive} consecutive failures "
                    f"(threshold: {auto_rotate_threshold}). Auto-rotating..."
                )
                # Use the existing rotation logic (but don't mark as quota exhausted)
                try:
                    # Reset daily counters if needed BEFORE rotation
                    # This reactivates keys that may have been reset (new day)
                    self._reset_daily_counters_if_needed()
                    
                    # Force save before rotation
                    if hasattr(self, '_unsaved_count') and self._unsaved_count > 0:
                        self._save_state()
                        self._unsaved_count = 0
                    
                    # Mark current key as inactive due to consecutive failures
                    key_state["is_active"] = False
                    key_state["consecutive_failures"] = 0  # Reset after rotation
                    
                    # Find next active key
                    attempts = 0
                    while attempts < len(self.keys):
                        self._current_index = (self._current_index + 1) % len(self.keys)
                        new_index = self._current_index
                        new_key_id = f"{self.key_prefix}_{self.key_numbers[new_index]}"
                        new_key_state = self.state.get("keys", {}).get(new_key_id, {})
                        
                        if new_key_state.get("is_active", True):
                            self.state["current_key_index"] = new_index
                            self._save_state()
                            print(f"[API Rotator] Auto-rotated to {new_key_id} (index {new_index})")
                            return self.keys[new_index], new_index
                        
                        attempts += 1
                    
                    # All keys exhausted - raise exception instead of auto-reactivate
                    # This prevents infinite loops when all keys have been exhausted
                    raise RuntimeError(
                        f"[API Rotator] All {len(self.keys)} API keys exhausted during auto-rotation. "
                        f"Please wait for quota reset (typically 24 hours) or add more API keys. "
                        f"Keys will be automatically reactivated when the day resets."
                    )
                except Exception as e:
                    print(f"[API Rotator] Warning: Error during auto-rotation: {e}")
                    # Fall through - don't return rotated key
            else:
                # Save state update (batch for performance)
                if hasattr(self, '_unsaved_count'):
                    self._unsaved_count += 1
                    if self._unsaved_count >= 10:
                        self._save_event.set()
                        self._unsaved_count = 0
                else:
                    self._save_event.set()
            
            return None
    
    def rotate_on_quota_exhausted(self, error_message: str = "") -> Tuple[str, int]:
        """
        Rotate to next key when quota exhausted (429 with "limit: 0").
        
        Args:
            error_message: Error message from API (for logging)
        
        Returns:
            (new_key, new_index): The new API key and its index
        """
        with self._lock:
            # Reset daily counters if needed BEFORE rotation
            # This reactivates keys that may have been reset (new day)
            self._reset_daily_counters_if_needed()
            
            # Force save any pending changes before rotation
            if hasattr(self, '_unsaved_count') and self._unsaved_count > 0:
                self._save_state()
                self._unsaved_count = 0
            
            old_index = self._current_index
            old_key_id = f"{self.key_prefix}_{self.key_numbers[old_index]}"
            
            # Mark current key as inactive
            now_iso = datetime.now().isoformat()
            if old_key_id not in self.state.get("keys", {}):
                self.state.setdefault("keys", {})[old_key_id] = {
                    "daily_requests": 0,
                    "last_reset_date": datetime.now().date().isoformat(),
                    "last_failure_time": None,
                    "last_usage_time": None,
                    "is_active": True,
                    "failure_count": 0,
                    "consecutive_failures": 0,
                    "total_requests": 0,
                }
            
            old_key_state = self.state["keys"][old_key_id]
            old_key_state["is_active"] = False
            old_key_state["last_failure_time"] = now_iso
            old_key_state["last_usage_time"] = now_iso
            old_key_state["failure_count"] = old_key_state.get("failure_count", 0) + 1
            old_key_state["total_requests"] = old_key_state.get("total_requests", 0) + 1
            # Reset consecutive failures since we're rotating (rotation is the action taken)
            old_key_state["consecutive_failures"] = 0
            
            print(
                f"[API Rotator] Quota exhausted for {old_key_id} (index {old_index}). "
                f"Rotating to next key..."
            )
            
            # Find next active key
            # Strategy: Try all keys in order, but also check if previously inactive keys
            # have been inactive for a while (same day) - they might have recovered
            attempts = 0
            today = datetime.now().date().isoformat()
            while attempts < len(self.keys):
                self._current_index = (self._current_index + 1) % len(self.keys)
                new_index = self._current_index
                new_key_id = f"{self.key_prefix}_{self.key_numbers[new_index]}"
                new_key_state = self.state.get("keys", {}).get(new_key_id, {})
                
                # Check if key is active (default to True if not in state)
                is_active = new_key_state.get("is_active", True)
                
                # If key is marked inactive but it's the same day, give it a chance
                # (RPD quotas reset daily, so a key that was exhausted earlier might work later)
                if not is_active:
                    last_reset = new_key_state.get("last_reset_date", today)
                    last_failure_time = new_key_state.get("last_failure_time")
                    
                    # If it's the same day and key was marked inactive, check if we should try it anyway
                    # Only skip if it failed recently (within last hour) on the same day
                    if last_reset == today and last_failure_time:
                        try:
                            last_failure_dt = datetime.fromisoformat(last_failure_time.replace('Z', '+00:00').replace('+00:00', ''))
                            if hasattr(last_failure_dt, 'replace'):
                                # Handle timezone-naive datetime
                                if last_failure_dt.tzinfo is None:
                                    time_since_failure = (datetime.now() - last_failure_dt).total_seconds()
                                else:
                                    time_since_failure = (datetime.now(last_failure_dt.tzinfo) - last_failure_dt).total_seconds()
                                
                                # If failed more than 1 hour ago on the same day, try it again
                                # (RPD might have reset or key might have recovered)
                                if time_since_failure > 3600:  # 1 hour
                                    print(f"[API Rotator] Key {new_key_id} was marked inactive but failed >1h ago. Retrying...")
                                    # Reactivate the key to give it a chance
                                    new_key_state["is_active"] = True
                                    is_active = True
                        except (ValueError, AttributeError):
                            # If we can't parse the time, try the key anyway
                            print(f"[API Rotator] Key {new_key_id} was marked inactive but can't parse failure time. Retrying...")
                            new_key_state["is_active"] = True
                            is_active = True
                
                if is_active:
                    self.state["current_key_index"] = new_index
                    self._save_state()  # Always save on rotation (critical state change)
                    print(f"[API Rotator] Switched to {new_key_id} (index {new_index})")
                    return self.keys[new_index], new_index
                
                attempts += 1
            
            # All keys exhausted? Raise exception instead of resetting
            # This prevents infinite rotation loops
            raise RuntimeError(
                f"[API Rotator] All {len(self.keys)} API keys exhausted. "
                f"Please wait for quota reset (typically 24 hours) or add more API keys."
            )
    
    def get_key_status(self) -> Dict:
        """
        Get current status of all keys (for debugging/monitoring).
        
        Returns:
            Dict with key status information including failure rates, usage ratios, and last usage times
        """
        with self._lock:
            status = {
                "current_key_index": self._current_index,
                "current_key_id": f"{self.key_prefix}_{self.key_numbers[self._current_index]}",
                "total_keys": len(self.keys),
                "keys": {},
            }
            
            # Calculate total usage across all keys for usage ratio
            total_daily_requests = sum(
                self.state.get("keys", {}).get(f"{self.key_prefix}_{self.key_numbers[j]}", {}).get("daily_requests", 0)
                for j in range(len(self.keys))
            )
            
            for i, key in enumerate(self.keys):
                key_id = f"{self.key_prefix}_{self.key_numbers[i]}"
                key_state = self.state.get("keys", {}).get(key_id, {})
                
                daily_requests = key_state.get("daily_requests", 0)
                total_requests = key_state.get("total_requests", 0)
                failure_count = key_state.get("failure_count", 0)
                
                # Calculate failure rate (0.0 to 1.0)
                failure_rate = (failure_count / total_requests) if total_requests > 0 else 0.0
                
                # Calculate usage ratio (daily_requests / total_daily_requests if total > 0)
                usage_ratio = (daily_requests / total_daily_requests) if total_daily_requests > 0 else 0.0
                
                status["keys"][key_id] = {
                    "is_active": key_state.get("is_active", True),
                    "daily_requests": daily_requests,
                    "total_requests": total_requests,
                    "failure_count": failure_count,
                    "consecutive_failures": key_state.get("consecutive_failures", 0),
                    "failure_rate": round(failure_rate, 4),  # 4 decimal places
                    "usage_ratio": round(usage_ratio, 4),  # 4 decimal places
                    "last_failure_time": key_state.get("last_failure_time"),
                    "last_usage_time": key_state.get("last_usage_time"),
                    "last_reset_date": key_state.get("last_reset_date"),
                    "is_current": (i == self._current_index),
                }
            
            return status
    
    def is_quota_exhausted_error(self, error: Exception) -> bool:
        """
        Check if error indicates quota exhaustion (non-retryable 429).
        
        Args:
            error: Exception from API call
        
        Returns:
            True if error indicates quota exhaustion
        """
        error_str = str(error).lower()
        error_str_lower = error_str.lower()
        
        # Quota exhaustion indicators:
        # - "quota exceeded"
        # - "exceeded your current quota"
        # - 429 with "limit: 0"
        # - 429 RESOURCE_EXHAUSTED (includes RPD limits)
        # - "resource has been exhausted"
        is_quota_exhausted = (
            "quota exceeded" in error_str_lower or
            "exceeded your current quota" in error_str_lower or
            ("429" in error_str and "limit: 0" in error_str_lower) or
            ("429" in error_str and "resource_exhausted" in error_str_lower) or
            "resource has been exhausted" in error_str_lower
        )
        
        return is_quota_exhausted

