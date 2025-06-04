import logging

# Color log format
class ColorFormatter(logging.Formatter):
    FORMATS = {
        logging.DEBUG: "\033[0;37m[DEBUG] %(message)s\033[0m",   # Gray
        logging.INFO: "\033[0;36m[INFO] %(message)s\033[0m",     # Cyan
        logging.WARNING: "\033[0;33m[WARN] %(message)s\033[0m",  # Yellow
        logging.ERROR: "\033[0;31m[ERROR] %(message)s\033[0m",   # Red
        logging.CRITICAL: "\033[1;41m[CRITICAL] %(message)s\033[0m",  # Red BG
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

# Setup logger
logger = logging.getLogger("auth")
handler = logging.StreamHandler()
handler.setFormatter(ColorFormatter())
logger.addHandler(handler)
logger.setLevel(logging.INFO)