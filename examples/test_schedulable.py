import asyncio
from typing import *

from mousse import schedulable, init_logger


logger = init_logger()


@schedulable
def greet(name: str):
    logger.info(f"Hello {name}")
    
    
if __name__ == "__main__":
    greet("datnh21")
    
    loop = asyncio.get_event_loop()
    task = greet.within(loop).after(repeated=True, seconds=1).call("mousse")
    
    loop.run_until_complete(task.wait())
