import cv2
import websockets
import asyncio
import base64
import json

WEBSOCKET_URL = "ws://127.0.0.1:8000/video/ws/video?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjo3LCJyb2xlIjoidXNlciIsImV4cCI6MTc0Mzk0MzU0NH0.hMo49jXfKFPkHtSHRILx6zA2P2dScVgUlQg56A1_ZJY"

async def send_video():
    async with websockets.connect(WEBSOCKET_URL) as websocket:
        cap = cv2.VideoCapture(0)  # Open webcam

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            _, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()

            await websocket.send(frame_bytes)

            try:
                response = await websocket.recv()
                data = json.loads(response)
                print(f"Received: {data}")
            except Exception as e:
                print(f"Error receiving data: {str(e)}")
                break

        cap.release()

asyncio.run(send_video())
