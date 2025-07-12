import logging
import sys

import uvicorn
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from utils.security import create_matrix_admin_token

logging.basicConfig(stream=sys.stdout, level=logging.INFO)

root_logger = logging.getLogger()

if len(root_logger.handlers) != 1:
    raise Exception(f"Got {len(root_logger.handlers)} handlers, want 1")


root_logger.handlers[0].setFormatter(
    uvicorn.logging.DefaultFormatter(
        fmt="%(asctime)s %(levelprefix)s %(name)-13s %(message)s"
    )
)

from endpoints.user import router as user_router

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", tags=["health"])
async def health_check():
    return {"status": "ok"}


app.include_router(user_router, tags=["user"])

if __name__ == "__main__":
    uvicorn.run(app)