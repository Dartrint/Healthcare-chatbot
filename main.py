from app.config import API_HOST, API_PORT

if __name__ == '__main__':
    import uvicorn

    uvicorn.run("app.api:app", host=API_HOST, port=API_PORT, reload=True)
