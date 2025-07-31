import logging

def setup_logfile_redirect(logger: logging.Logger, log_file: str):
    """将日志输出重定向到文件"""
    handler = logging.FileHandler(log_file, encoding="utf-8")
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return handler