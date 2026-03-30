"""
ProgressLogger: Terminal progress bars and file logging for S1~S5 scripts.

Provides:
- Multiple tqdm progress bars (group/entity/card/image levels)
- File logging for detailed debug information
- Thread-safe progress updates for parallel processing
"""

import logging
import os
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

from tqdm import tqdm


class ProgressLogger:
    """
    Manages terminal progress bars and file logging for pipeline scripts.
    
    Features:
    - Multiple progress bars displayed simultaneously (group/entity/card/image)
    - File logging for detailed debug information
    - Thread-safe updates for parallel processing
    """
    
    def __init__(
        self,
        run_tag: str,
        script_name: str,
        arm: str,
        base_dir: Path,
        enable_progress: bool = True,
        enable_file_log: bool = True,
    ):
        """
        Initialize ProgressLogger.
        
        Args:
            run_tag: Run tag identifier
            script_name: Script name (e.g., "s1_s2", "s3", "s4", "s5")
            arm: Arm identifier (A, B, C, D, E, F)
            base_dir: Base directory of MeducAI project
            enable_progress: Enable terminal progress bars (default: True)
            enable_file_log: Enable file logging (default: True)
        """
        self.run_tag = run_tag
        self.script_name = script_name
        self.arm = arm
        self.base_dir = Path(base_dir).resolve()
        self.enable_progress = enable_progress and sys.stdout.isatty()
        self.enable_file_log = enable_file_log
        
        # Thread lock for thread-safe updates
        self._lock = threading.Lock()
        
        # Progress bars (initialized as None, created on first use)
        self._group_bar: Optional[tqdm] = None
        self._entity_bar: Optional[tqdm] = None
        self._card_bar: Optional[tqdm] = None
        self._image_bar: Optional[tqdm] = None
        
        # Progress state
        self._group_current = 0
        self._group_total = 0
        self._entity_current = 0
        self._entity_total = 0
        self._card_current = 0
        self._card_total = 0
        self._image_current = 0
        self._image_total = 0
        
        # File logger
        self._file_logger: Optional[logging.Logger] = None
        self._log_file_path: Optional[Path] = None
        
        if self.enable_file_log:
            self._setup_file_logging()
    
    def _setup_file_logging(self) -> None:
        """Set up file logging for detailed debug information."""
        try:
            # Create logs directory
            log_dir = self.base_dir / "2_Data" / "metadata" / "generated" / self.run_tag / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate log filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_filename = f"{self.script_name}_arm{self.arm}_{timestamp}.log"
            self._log_file_path = log_dir / log_filename
            
            # Create logger
            self._file_logger = logging.getLogger(f"meducai_{self.script_name}_{self.arm}_{timestamp}")
            self._file_logger.setLevel(logging.DEBUG)
            
            # File handler (append mode)
            file_handler = logging.FileHandler(self._log_file_path, encoding="utf-8", mode="a")
            file_handler.setLevel(logging.DEBUG)
            
            # Formatter
            formatter = logging.Formatter(
                "%(asctime)s [%(levelname)s] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
            file_handler.setFormatter(formatter)
            
            self._file_logger.addHandler(file_handler)
            
            # Prevent propagation to root logger
            self._file_logger.propagate = False
            
        except Exception as e:
            # If file logging fails, continue without it
            print(f"[ProgressLogger] Warning: Failed to set up file logging: {e}", file=sys.stderr)
            self._file_logger = None
    
    def _get_position(self, level: str) -> int:
        """
        Get tqdm position for a given level.
        
        Positions:
        - group: 0
        - entity: 1
        - card: 2
        - image: 3
        """
        positions = {"group": 0, "entity": 1, "card": 2, "image": 3}
        return positions.get(level, 0)
    
    def init_group(self, total: int, desc: str = "Processing groups") -> None:
        """Initialize group progress bar."""
        if not self.enable_progress:
            return
        
        with self._lock:
            if self._group_bar is None:
                self._group_total = total
                self._group_bar = tqdm(
                    total=total,
                    desc=desc,
                    position=self._get_position("group"),
                    leave=True,
                    ncols=100,
                    file=sys.stdout,
                )
    
    def update_group(self, current: int, total: Optional[int] = None, group_id: str = "") -> None:
        """Update group progress bar."""
        if not self.enable_progress:
            return
        
        with self._lock:
            if total is not None:
                self._group_total = total
                if self._group_bar is not None:
                    self._group_bar.total = total
            
            if self._group_bar is None:
                self.init_group(self._group_total or total or 1)
            
            if self._group_bar is not None:
                self._group_current = current
                postfix = f"({group_id})" if group_id else ""
                self._group_bar.set_postfix_str(postfix)
                self._group_bar.n = current
                self._group_bar.refresh()
    
    def init_entity(self, total: int, desc: str = "Processing entities") -> None:
        """Initialize entity progress bar."""
        if not self.enable_progress:
            return
        
        with self._lock:
            if self._entity_bar is None:
                self._entity_total = total
                self._entity_bar = tqdm(
                    total=total,
                    desc=desc,
                    position=self._get_position("entity"),
                    leave=True,
                    ncols=100,
                    file=sys.stdout,
                )
    
    def update_entity(self, current: int, total: Optional[int] = None, entity_id: str = "") -> None:
        """Update entity progress bar."""
        if not self.enable_progress:
            return
        
        with self._lock:
            if total is not None:
                self._entity_total = total
                if self._entity_bar is not None:
                    self._entity_bar.total = total
            
            if self._entity_bar is None:
                self.init_entity(self._entity_total or total or 1)
            
            if self._entity_bar is not None:
                self._entity_current = current
                postfix = f"({entity_id})" if entity_id else ""
                self._entity_bar.set_postfix_str(postfix)
                self._entity_bar.n = current
                self._entity_bar.refresh()
    
    def init_card(self, total: int, desc: str = "Processing cards") -> None:
        """Initialize card progress bar."""
        if not self.enable_progress:
            return
        
        with self._lock:
            if self._card_bar is None:
                self._card_total = total
                self._card_bar = tqdm(
                    total=total,
                    desc=desc,
                    position=self._get_position("card"),
                    leave=True,
                    ncols=100,
                    file=sys.stdout,
                )
    
    def update_card(self, current: int, total: Optional[int] = None, card_role: str = "") -> None:
        """Update card progress bar."""
        if not self.enable_progress:
            return
        
        with self._lock:
            if total is not None:
                self._card_total = total
                if self._card_bar is not None:
                    self._card_bar.total = total
            
            if self._card_bar is None:
                self.init_card(self._card_total or total or 1)
            
            if self._card_bar is not None:
                self._card_current = current
                postfix = f"({card_role})" if card_role else ""
                self._card_bar.set_postfix_str(postfix)
                self._card_bar.n = current
                self._card_bar.refresh()
    
    def init_image(self, total: int, desc: str = "Generating images") -> None:
        """Initialize image progress bar."""
        if not self.enable_progress:
            return
        
        with self._lock:
            if self._image_bar is None:
                self._image_total = total
                self._image_bar = tqdm(
                    total=total,
                    desc=desc,
                    position=self._get_position("image"),
                    leave=True,
                    ncols=100,
                    file=sys.stdout,
                )
    
    def update_image(self, current: int, total: Optional[int] = None, image_name: str = "") -> None:
        """Update image progress bar."""
        if not self.enable_progress:
            return
        
        with self._lock:
            if total is not None:
                self._image_total = total
                if self._image_bar is not None:
                    self._image_bar.total = total
            
            if self._image_bar is None:
                self.init_image(self._image_total or total or 1)
            
            if self._image_bar is not None:
                self._image_current = current
                postfix = f"({image_name[:30]})" if image_name else ""
                self._image_bar.set_postfix_str(postfix)
                self._image_bar.n = current
                self._image_bar.refresh()
    
    def reset_entity(self) -> None:
        """Reset entity progress bar (for new group)."""
        with self._lock:
            if self._entity_bar is not None:
                self._entity_bar.n = 0
                self._entity_bar.refresh()
            self._entity_current = 0
    
    def reset_card(self) -> None:
        """Reset card progress bar (for new entity)."""
        with self._lock:
            if self._card_bar is not None:
                self._card_bar.n = 0
                self._card_bar.refresh()
            self._card_current = 0
    
    def reset_image(self) -> None:
        """Reset image progress bar (for new group/entity)."""
        with self._lock:
            if self._image_bar is not None:
                self._image_bar.n = 0
                self._image_bar.refresh()
            self._image_current = 0
    
    def debug(self, message: str) -> None:
        """Log debug message to file only (no terminal output)."""
        if self._file_logger is not None:
            self._file_logger.debug(message)
    
    def info(self, message: str) -> None:
        """Log info message to file and print to terminal."""
        if self._file_logger is not None:
            self._file_logger.info(message)
        print(message, flush=True)
    
    def warning(self, message: str) -> None:
        """Log warning message to file and print to terminal."""
        if self._file_logger is not None:
            self._file_logger.warning(message)
        print(f"⚠️  {message}", file=sys.stderr, flush=True)
    
    def error(self, message: str) -> None:
        """Log error message to file and print to terminal."""
        if self._file_logger is not None:
            self._file_logger.error(message)
        print(f"❌ {message}", file=sys.stderr, flush=True)
    
    def close(self) -> None:
        """Close progress bars and file logger."""
        with self._lock:
            # Close progress bars
            if self._group_bar is not None:
                self._group_bar.close()
                self._group_bar = None
            
            if self._entity_bar is not None:
                self._entity_bar.close()
                self._entity_bar = None
            
            if self._card_bar is not None:
                self._card_bar.close()
                self._card_bar = None
            
            if self._image_bar is not None:
                self._image_bar.close()
                self._image_bar = None
            
            # Close file logger handlers
            if self._file_logger is not None:
                for handler in self._file_logger.handlers[:]:
                    handler.close()
                    self._file_logger.removeHandler(handler)
                self._file_logger = None
    
    def get_log_file_path(self) -> Optional[Path]:
        """Get the path to the log file."""
        return self._log_file_path
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False

