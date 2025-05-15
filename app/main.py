import logging

from dotenv import load_dotenv
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

load_dotenv('.env')

import uvicorn
from fastapi import FastAPI
from api.router import router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()


class Log500Middleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)

            # Если status_code == 500, мы логируем детали запроса
            if response.status_code == 500:
                body = await request.body()
                logger.error(
                    f"Ошибка 500 на запрос: {request.method} {request.url}\n"
                    f"Headers: {dict(request.headers)}\n"
                    f"Body: {body.decode('utf-8') if body else 'пустое тело запроса'}"
                )

            return response

        except Exception as e:
            body = await request.body()
            logger.exception(
                f"Исключение при обработке запросa: {request.method} {request.url}\n"
                f"Headers: {dict(request.headers)}\n"
                f"Body: {body.decode('utf-8') if body else 'пустое тело запроса'}\n"
                f"Ошибка: {str(e)}"
            )
            raise e


# Добавляем middleware в приложение FastAPI
app = FastAPI()
app.add_middleware(Log500Middleware)

app.include_router(router, prefix='/api')
uvicorn.run(app, host="0.0.0.0", port=8000)
