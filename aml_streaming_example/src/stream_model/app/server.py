from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from langserve import add_routes
from fastapi.responses import StreamingResponse
import asyncio


app = FastAPI()


async def fake_data_streamer():
    for i in 'Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.'.split(' '):
        yield i
        await asyncio.sleep(0.5)


@app.get("/")
async def redirect_root_to_docs():
    return RedirectResponse("/docs")

@app.get('/stream')
async def main():
    return StreamingResponse(fake_data_streamer(), media_type='text/event-stream')



if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)