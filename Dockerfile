FROM python:3.11-slim

# Dependencies for PyQt6 + OpenCV on Linux (macOS Docker)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libegl1 libxkbcommon0 libdbus-1-3 \
    libglib2.0-0 libsm6 libxext6 libxrender1 \
    libxcb-xinerama0 libxcb-shape0 libxcb-render0 \
    libfontconfig1 libxcursor1 libxi6 libxtst6 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# X11 platform for Qt on macOS via XQuartz
ENV QT_QPA_PLATFORM=xcb

CMD ["python", "run.py"]
