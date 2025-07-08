import asyncio
import aiohttp
import logging
import random
import numpy as np
from datetime import datetime
 
# Configuración
API_URL = "https://simyo.wyred.es/api/actions/no_customer/touch_point"
N_CONCURRENT = 5     # Número máximo de peticiones concurrentes
RATE_PER_MIN = 200    # x peticiones por minuto
DURATION_MINUTES = 1 # Duración de la simulación
TOTAL_REQUESTS = RATE_PER_MIN * DURATION_MINUTES
 
# Logging
logging.basicConfig(
    filename="api_requests.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
 
semaphore = asyncio.Semaphore(N_CONCURRENT)
 
async def post_request(session, payload):
    async with semaphore:
        try:
            async with session.post(API_URL, json=payload) as response:
                result = await response.text()
                logging.info(f"Status: {response.status}, Response: {result}")
        except Exception as e:
            logging.error(f"Request failed: {str(e)}")
 
async def schedule_requests():
    async with aiohttp.ClientSession() as session:
        tasks = []
        for _ in range(TOTAL_REQUESTS):
            interval = np.random.exponential(scale=60 / RATE_PER_MIN)  # Poisson inter-arrival
            await asyncio.sleep(interval)
            payload = {
                "msisdn": "697289128",
                "touch_point": "mm_pre_routing",
                "inbound_channel_type": "ivr",
                "variables": {
                    "DNIS": "697289128",
                    "ANI": "697289128",
                    "MSISDN": "697289128"
                }
            }
            tasks.append(asyncio.create_task(post_request(session, payload)))
        await asyncio.gather(*tasks)
 
if __name__ == "__main__":
    asyncio.run(schedule_requests())