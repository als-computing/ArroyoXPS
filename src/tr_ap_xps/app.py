import asyncio
import base64
import io

import numpy as np
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image

app = FastAPI()

origins = [
    "http://localhost.tiangolo.com",
    "https://localhost.tiangolo.com",
    "http://localhost",
    "http://localhost:8080",
    "http://localhost:3000",
    "http://localhost:3001",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.websocket("/simImages")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = {"description": "", "images": [], "plots": []}
            # Generate 3 random RGB images
            img_types = ["raw", "vfft", "ifft"]
            plot_types = ["sum", "fitted"]
            for i in range(3):
                array = np.random.randint(256, size=(512, 512, 3), dtype=np.uint8)
                img = Image.fromarray(array, "RGB")

                # Convert image to base64
                buffered = io.BytesIO()
                img.save(buffered, format="JPEG")
                img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")

                key = img_types[i]
                data["images"].append({"image": img_str, "key": key})

            for i in range(2):
                gaussianPlot = {
                    "X": np.random.randint(20) + 5,
                    "H": np.random.randint(20) + 5,
                    "FWHM": np.random.randint(20) + 1,
                }
                plot = {"terms": gaussianPlot, "key": plot_types[i]}
                data["plots"].append(plot)
            # provide description
            data["description"] = "3 sample images and 2 sample plots"

            # Send all data
            await websocket.send_json(data)
            await asyncio.sleep(0.1)  # Sending 10 new images every second
    except Exception as e:
        print("Error:", e)
    finally:
        await websocket.close()


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8001, reload=True)
