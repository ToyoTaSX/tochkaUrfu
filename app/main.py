from dotenv import load_dotenv
load_dotenv('../.env')

import uvicorn
from fastapi import FastAPI
from api.router import router

app = FastAPI()
app.include_router(router, prefix='/api')
uvicorn.run(app, host="127.0.0.1", port=8000)