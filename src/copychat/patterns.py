"""Default patterns and extensions for file filtering."""

# Default extensions we care about (without dots)
DEFAULT_EXTENSIONS = {
    # Web
    "html",
    "css",
    "scss",
    "js",
    "jsx",
    "ts",
    "tsx",
    "json",
    # Python
    "py",
    "pyi",
    "pyw",
    # Ruby
    "rb",
    "erb",
    # JVM
    "java",
    "kt",
    "scala",
    "gradle",
    # Systems
    "c",
    "h",
    "cpp",
    "hpp",
    "rs",
    "go",
    # Shell
    "sh",
    "bash",
    "zsh",
    "fish",
    # Config
    "yaml",
    "yml",
    "toml",
    "ini",
    "conf",
    # Docs
    "md",
    "mdx",
    "rst",
    "txt",
    # Other
    "sql",
    "graphql",
    "xml",
    "dockerfile",
    "gitignore",
}

# Directories that should always be excluded
EXCLUDED_DIRS = {
    # Version Control
    ".git",
    ".svn",
    ".hg",
    # Dependencies
    "node_modules",
    "venv",
    ".venv",
    "env",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "target",
    "build",
    "dist",
    # IDE
    ".idea",
    ".vscode",
    # Other
    ".next",
    ".nuxt",
    ".output",
    "coverage",
}

# Files or patterns that should always be excluded
EXCLUDED_PATTERNS = {
    # Build artifacts
    "*.pyc",
    "*.pyo",
    "*.pyd",
    "*.so",
    "*.dll",
    "*.dylib",
    "*.class",
    "*.jar",
    "*.war",
    "*.min.js",
    "*.min.css",
    # Logs and databases
    "*.log",
    "*.sqlite",
    "*.db",
    # OS files
    ".DS_Store",
    "Thumbs.db",
    "desktop.ini",
    # Package files
    "package-lock.json",
    "yarn.lock",
    "poetry.lock",
    # Environment and secrets
    ".env",
    ".env.*",
    "*.env",
    # Other
    "*.bak",
    "*.swp",
    "*.swo",
    "*~",
}
