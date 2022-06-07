from mousse import init_logger, get_logger

init_logger(log_dir="logs")
logger = get_logger()

logger.info("Call from global scope")


def foo():
    logger.info("Call from foo")
    def bar():
        logger.info("Call from bar")
        
    bar()


if __name__ == "__main__":
    foo()
