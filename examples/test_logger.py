from mousse import get_logger

logger = get_logger()
logger.load_config("config/logger.yaml")

logger.info("Call from global scope")
logger.error("This is a error")


def foo():
    logger.info("Call from foo")

    def bar():
        logger.info("Call from bar")

    bar()


if __name__ == "__main__":
    foo()
