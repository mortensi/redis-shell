"""
File utilities for redis-shell.

This module contains utilities for file operations, path handling, and file-related completions.
"""

import os
import glob
from typing import List, Optional, Tuple


class PathHandler:
    """Handles file path operations and completions."""

    @staticmethod
    def parse_path(incomplete: str) -> Tuple[str, str, bool, str]:
        """
        Parse an incomplete path into components.

        Args:
            incomplete: The incomplete path string

        Returns:
            Tuple containing:
                - base_dir: The directory to search in
                - prefix: The prefix to match against
                - is_absolute: Whether the path is absolute
                - path_prefix: The path prefix (everything before the last component)
        """
        current_dir = os.getcwd()

        # If incomplete starts with a path separator, treat it as an absolute path
        if incomplete.startswith(os.path.sep):
            base_dir = os.path.dirname(incomplete) or os.path.sep
            is_absolute = True
        # If incomplete contains a path separator, treat it as a relative path
        elif os.path.sep in incomplete:
            base_dir = os.path.join(current_dir, os.path.dirname(incomplete))
            is_absolute = False
        # Otherwise, use the current directory
        else:
            base_dir = current_dir
            is_absolute = False

        # Get the part of the path that should be completed (after the last separator)
        if os.path.sep in incomplete:
            prefix = os.path.basename(incomplete)
            path_prefix = os.path.dirname(incomplete) + os.path.sep if incomplete.find(os.path.sep) >= 0 else ""
        else:
            prefix = incomplete
            path_prefix = ""

        # If the base directory doesn't exist, find the closest existing parent
        original_base_dir = base_dir
        while not os.path.exists(base_dir) and base_dir != os.path.dirname(base_dir):
            base_dir = os.path.dirname(base_dir)

        return original_base_dir, prefix, is_absolute, path_prefix

    @staticmethod
    def get_directory_completions(incomplete: str) -> List[str]:
        """
        Get directory completions for an incomplete path.

        Args:
            incomplete: The incomplete path string

        Returns:
            List of directory completions
        """
        base_dir, prefix, is_absolute, path_prefix = PathHandler.parse_path(incomplete)

        try:
            # Get all directories in the base directory
            dirs = []
            if os.path.isdir(base_dir):
                for item in os.listdir(base_dir):
                    full_path = os.path.join(base_dir, item)
                    if os.path.isdir(full_path):
                        # Add trailing slash to directories
                        if is_absolute and incomplete.endswith(os.path.sep):
                            # If the incomplete path ends with a separator, just append the directory name
                            dirs.append(incomplete + item + os.path.sep)
                        elif is_absolute:
                            # For absolute paths, preserve the directory structure
                            if prefix and item.startswith(prefix):
                                dirs.append(path_prefix + item + os.path.sep)
                            elif not prefix:
                                dirs.append(path_prefix + item + os.path.sep)
                        elif os.path.sep in incomplete:
                            # For relative paths with directories, preserve the directory structure
                            if prefix and item.startswith(prefix):
                                dirs.append(path_prefix + item + os.path.sep)
                            elif not prefix:
                                dirs.append(path_prefix + item + os.path.sep)
                        else:
                            # For simple completions in the current directory
                            if prefix and item.startswith(prefix):
                                dirs.append(item + os.path.sep)
                            elif not prefix:
                                dirs.append(item + os.path.sep)
            return dirs
        except (FileNotFoundError, PermissionError):
            return []

    @staticmethod
    def get_file_completions(incomplete: str, pattern: str, file_prefix: Optional[str] = None) -> List[str]:
        """
        Get file completions for an incomplete path matching a pattern and optional prefix.

        Args:
            incomplete: The incomplete path string
            pattern: The glob pattern to match files against
            file_prefix: Optional prefix that files must start with

        Returns:
            List of file completions
        """
        base_dir, prefix, is_absolute, path_prefix = PathHandler.parse_path(incomplete)

        try:
            # Get all files in the base directory that match the pattern
            files = []
            full_pattern = os.path.join(base_dir, pattern)

            for file_path in glob.glob(full_pattern):
                if os.path.isfile(file_path):
                    file_name = os.path.basename(file_path)

                    # Check if the file matches the required prefix
                    if file_prefix and not file_name.startswith(file_prefix):
                        continue

                    # Format the path based on whether we're using absolute or relative paths
                    if is_absolute:
                        # For absolute paths, preserve the directory structure
                        if prefix and file_name.startswith(prefix):
                            files.append(path_prefix + file_name)
                        elif not prefix:
                            files.append(path_prefix + file_name)
                    elif os.path.sep in incomplete:
                        # For relative paths with directories, preserve the directory structure
                        if prefix and file_name.startswith(prefix):
                            files.append(path_prefix + file_name)
                        elif not prefix:
                            files.append(path_prefix + file_name)
                    else:
                        # For simple completions in the current directory
                        if prefix and file_name.startswith(prefix):
                            files.append(file_name)
                        elif not prefix:
                            files.append(file_name)

            return files
        except (FileNotFoundError, PermissionError):
            return []

    @staticmethod
    def get_path_completions(incomplete: str, file_pattern: Optional[str] = None, file_prefix: Optional[str] = None) -> List[str]:
        """
        Get completions for an incomplete path, including both directories and files.

        Args:
            incomplete: The incomplete path string
            file_pattern: Optional glob pattern to match files against
            file_prefix: Optional prefix that files must start with

        Returns:
            List of path completions
        """
        # First, get directory completions
        completions = PathHandler.get_directory_completions(incomplete)

        # If a file pattern is provided, also get file completions
        if file_pattern:
            completions.extend(PathHandler.get_file_completions(incomplete, file_pattern, file_prefix))

        return completions
