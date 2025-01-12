"""HacsLogger"""


class HacsLogger:
    """Custom logger class for HACS."""

    import logging

    prefix = "custom_components.hacs"

    def debug(self, message, part=None):
        """Info messages."""
        part = self.prefix if part is None else f"{self.prefix}.{part}"
        self.logging.getLogger(part).debug(message)

    def info(self, message, part=None):
        """Info messages."""
        part = self.prefix if part is None else f"{self.prefix}.{part}"
        self.logging.getLogger(part).info(message)

    def warning(self, message, part=None):
        """Info messages."""
        part = self.prefix if part is None else f"{self.prefix}.{part}"
        self.logging.getLogger(part).warning(message)

    def error(self, message, part=None):
        """Info messages."""
        part = self.prefix if part is None else f"{self.prefix}.{part}"
        self.logging.getLogger(part).error(message)

    def critical(self, message, part=None):
        """Info messages."""
        part = self.prefix if part is None else f"{self.prefix}.{part}"
        self.logging.getLogger(part).critical(message)
