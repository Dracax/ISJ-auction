import logging
import sys


def setup_logging(level=logging.INFO):
    """
    Configure logging to output to console with time, process, thread, level, and message.

    Args:
        level: The logging level (default: logging.INFO)
    """
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Clear any existing handlers
    root_logger.handlers.clear()

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)

    # Create formatter with time, process, thread, level, and message
    formatter = logging.Formatter(
        fmt='%(asctime)s - PID:%(process)d - Thread:%(thread)d - %(levelname)s - [%(module)s: %(funcName)s] - %(message)s',
        datefmt='%H:%M:%S'
    )

    # Set formatter for console handler
    console_handler.setFormatter(formatter)

    # Add handler to root logger
    root_logger.addHandler(console_handler)

    file_handler = logging.FileHandler(
        'application.log',
        mode='a',
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)


if __name__ == '__main__':
    # Example usage
    setup_logging(logging.DEBUG)

    logging.debug('This is a debug message')
    logging.info('This is an info message')
    logging.warning('This is a warning message')
    logging.error('This is an error message')
    logging.critical('This is a critical message')
