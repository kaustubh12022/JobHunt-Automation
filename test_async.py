import asyncio
import time
from src.ai_engine import call_ai_scoring_async
from src.logger import logger

async def process(idx):
    start = time.time()
    logger.info(f"Task {idx} starting at {start:.3f}...")
    res = await call_ai_scoring_async(f"Say hello from task {idx}")
    elapsed = time.time() - start
    logger.info(f"Task {idx} finished in {elapsed:.3f}s")

async def main():
    logger.info("Starting concurrent test...")
    tasks = [process(i) for i in range(5)]
    start = time.time()
    await asyncio.gather(*tasks)
    elapsed = time.time() - start
    logger.info(f"All 5 tasks finished in {elapsed:.3f}s")

if __name__ == "__main__":
    asyncio.run(main())
