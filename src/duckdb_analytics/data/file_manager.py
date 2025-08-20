"""File management and data ingestion."""

from pathlib import Path
from typing import List, Dict, Any, Optional, Union
import hashlib
import json
import logging
from datetime import datetime
import pandas as pd
import pyarrow.parquet as pq

logger = logging.getLogger(__name__)


class FileManager:
    """Manages data files and their metadata."""
    
    def __init__(self, data_dir: Union[str, Path] = "./data"):
        """
        Initialize file manager.
        
        Args:
            data_dir: Directory for data files
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._file_registry: Dict[str, Dict[str, Any]] = {}
        
    def scan_directory(self, directory: Optional[Path] = None) -> List[Dict[str, Any]]:
        """
        Scan directory for data files.
        
        Args:
            directory: Directory to scan (default: data_dir)
            
        Returns:
            List of file metadata dictionaries
        """
        scan_dir = directory or self.data_dir
        files = []
        
        # Scan for CSV and Parquet files
        for pattern in ["*.csv", "*.parquet", "*.parq"]:
            for filepath in scan_dir.glob(f"**/{pattern}"):
                if filepath.is_file():
                    file_info = self.get_file_info(filepath)
                    files.append(file_info)
                    self._register_file(file_info)
        
        logger.info(f"Found {len(files)} data files in {scan_dir}")
        return files
    
    def get_file_info(self, filepath: Union[str, Path]) -> Dict[str, Any]:
        """
        Get metadata for a data file.
        
        Args:
            filepath: Path to data file
            
        Returns:
            File metadata dictionary
        """
        filepath = Path(filepath)
        
        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")
        
        info = {
            "path": str(filepath.absolute()),
            "name": filepath.name,
            "size": filepath.stat().st_size,
            "modified": datetime.fromtimestamp(filepath.stat().st_mtime).isoformat(),
            "format": filepath.suffix.lower().replace(".", ""),
            "hash": self._get_file_hash(filepath)
        }
        
        # Get schema information
        try:
            if info["format"] == "csv":
                info["schema"] = self._get_csv_schema(filepath)
                info["rows"] = self._count_csv_rows(filepath)
            elif info["format"] in ["parquet", "parq"]:
                info["schema"] = self._get_parquet_schema(filepath)
                info["rows"] = self._count_parquet_rows(filepath)
        except Exception as e:
            logger.warning(f"Failed to get schema for {filepath}: {e}")
            info["schema"] = None
            info["rows"] = None
        
        return info
    
    def _get_file_hash(self, filepath: Path, chunk_size: int = 8192) -> str:
        """Calculate file hash for deduplication."""
        hasher = hashlib.md5()
        with filepath.open("rb") as f:
            while chunk := f.read(chunk_size):
                hasher.update(chunk)
        return hasher.hexdigest()
    
    def _get_csv_schema(self, filepath: Path) -> Dict[str, str]:
        """Get schema information for CSV file."""
        # Read first few rows to infer schema
        df = pd.read_csv(filepath, nrows=100)
        return {col: str(dtype) for col, dtype in df.dtypes.items()}
    
    def _get_parquet_schema(self, filepath: Path) -> Dict[str, str]:
        """Get schema information for Parquet file."""
        parquet_file = pq.ParquetFile(filepath)
        schema = parquet_file.schema
        return {field.name: str(field.type) for field in schema}
    
    def _count_csv_rows(self, filepath: Path) -> int:
        """Count rows in CSV file efficiently."""
        with filepath.open("r", encoding="utf-8") as f:
            return sum(1 for _ in f) - 1  # Subtract header row
    
    def _count_parquet_rows(self, filepath: Path) -> int:
        """Count rows in Parquet file."""
        parquet_file = pq.ParquetFile(filepath)
        return parquet_file.metadata.num_rows
    
    def _register_file(self, file_info: Dict[str, Any]) -> None:
        """Register file in internal registry."""
        self._file_registry[file_info["hash"]] = file_info
    
    def validate_file(self, filepath: Union[str, Path]) -> bool:
        """
        Validate data file format and readability.
        
        Args:
            filepath: Path to data file
            
        Returns:
            True if file is valid
        """
        filepath = Path(filepath)
        
        if not filepath.exists():
            return False
        
        try:
            if filepath.suffix.lower() == ".csv":
                pd.read_csv(filepath, nrows=1)
            elif filepath.suffix.lower() in [".parquet", ".parq"]:
                pq.ParquetFile(filepath)
            else:
                return False
            return True
        except Exception as e:
            logger.error(f"File validation failed for {filepath}: {e}")
            return False
    
    def save_registry(self, registry_path: Optional[Path] = None) -> None:
        """Save file registry to JSON."""
        registry_path = registry_path or self.data_dir / ".file_registry.json"
        with registry_path.open("w") as f:
            json.dump(self._file_registry, f, indent=2)
        logger.info(f"Saved file registry to {registry_path}")
    
    def load_registry(self, registry_path: Optional[Path] = None) -> None:
        """Load file registry from JSON."""
        registry_path = registry_path or self.data_dir / ".file_registry.json"
        if registry_path.exists():
            with registry_path.open("r") as f:
                self._file_registry = json.load(f)
            logger.info(f"Loaded file registry from {registry_path}")
    
    def get_registered_files(self) -> List[Dict[str, Any]]:
        """Get all registered files."""
        return list(self._file_registry.values())
    
    def find_files_by_pattern(self, pattern: str) -> List[Dict[str, Any]]:
        """Find files matching a pattern."""
        matching_files = []
        for file_info in self._file_registry.values():
            if pattern.lower() in file_info["name"].lower():
                matching_files.append(file_info)
        return matching_files
    
    def get_file_by_hash(self, file_hash: str) -> Optional[Dict[str, Any]]:
        """Get file info by hash."""
        return self._file_registry.get(file_hash)
    
    def convert_csv_to_parquet(
        self,
        csv_path: Union[str, Path],
        parquet_path: Optional[Union[str, Path]] = None,
        compression: str = "snappy"
    ) -> Path:
        """
        Convert CSV file to Parquet format.
        
        Args:
            csv_path: Path to CSV file
            parquet_path: Output Parquet path (auto-generated if None)
            compression: Compression algorithm
            
        Returns:
            Path to created Parquet file
        """
        csv_path = Path(csv_path)
        if parquet_path is None:
            parquet_path = csv_path.with_suffix(".parquet")
        else:
            parquet_path = Path(parquet_path)
        
        # Read CSV and write as Parquet
        df = pd.read_csv(csv_path)
        df.to_parquet(parquet_path, compression=compression, engine="pyarrow")
        
        logger.info(f"Converted {csv_path} to {parquet_path}")
        return parquet_path
    
    def get_sample_data(
        self,
        filepath: Union[str, Path],
        n_rows: int = 100
    ) -> pd.DataFrame:
        """
        Get sample data from file.
        
        Args:
            filepath: Path to data file
            n_rows: Number of rows to sample
            
        Returns:
            Sample DataFrame
        """
        filepath = Path(filepath)
        
        if filepath.suffix.lower() == ".csv":
            return pd.read_csv(filepath, nrows=n_rows)
        elif filepath.suffix.lower() in [".parquet", ".parq"]:
            df = pd.read_parquet(filepath, engine="pyarrow")
            return df.head(n_rows)
        else:
            raise ValueError(f"Unsupported file format: {filepath.suffix}")