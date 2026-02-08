import asyncio
import json
import logging
import os
import threading
from typing import Optional

import numpy as np
import websockets
from scipy.signal import resample

from RealtimeSTT import AudioToTextRecorder

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logging.getLogger('websockets').setLevel(logging.WARNING)

STT_MODEL = os.getenv("STT_MODEL", "small.en")
STT_REALTIME_MODEL = os.getenv("STT_REALTIME_MODEL", "tiny.en")
STT_LANGUAGE = os.getenv("STT_LANGUAGE", "en")
STT_SILERO_SENSITIVITY = float(os.getenv("STT_SILERO_SENSITIVITY", "0.4"))
STT_WEBRTC_SENSITIVITY = int(os.getenv("STT_WEBRTC_SENSITIVITY", "3"))
STT_POST_SPEECH_SILENCE = float(os.getenv("STT_POST_SPEECH_SILENCE", "0.7"))

recorder_ready = threading.Event()
client_websocket = None
main_loop: Optional[asyncio.AbstractEventLoop] = None


def decode_and_resample(audio_data: bytes | bytearray, original_sample_rate: int, target_sample_rate: int) -> bytes:
    try:
        audio_np = np.frombuffer(bytes(audio_data), dtype=np.int16)
        if original_sample_rate == target_sample_rate:
            return audio_np.tobytes()
        num_original_samples = len(audio_np)
        num_target_samples = int(num_original_samples * target_sample_rate / original_sample_rate)
        resampled_audio = resample(audio_np, num_target_samples)
        return np.asarray(resampled_audio, dtype=np.int16).tobytes()
    except Exception:
        return bytes(audio_data)


async def send_to_client(message: str) -> None:
    global client_websocket
    if client_websocket is not None and client_websocket.open:
        try:
            await client_websocket.send(message)
        except websockets.exceptions.ConnectionClosed:
            client_websocket = None


def text_detected(text: str) -> None:
    global main_loop
    if main_loop is None:
        return
    payload = json.dumps({"type": "realtime", "text": text})
    asyncio.run_coroutine_threadsafe(send_to_client(payload), main_loop)


recorder_config = {
    "spinner": False,
    "use_microphone": False,
    "model": STT_MODEL,
    "realtime_model_type": STT_REALTIME_MODEL,
    "language": STT_LANGUAGE,
    "silero_sensitivity": STT_SILERO_SENSITIVITY,
    "webrtc_sensitivity": STT_WEBRTC_SENSITIVITY,
    "post_speech_silence_duration": STT_POST_SPEECH_SILENCE,
    "enable_realtime_transcription": True,
    "realtime_processing_pause": 0,
    "on_realtime_transcription_stabilized": text_detected,
}


recorder = AudioToTextRecorder(**recorder_config)


def run_recorder() -> None:
    recorder_ready.set()
    run_method = getattr(recorder, "run", None)
    if callable(run_method):
        run_method()
        return
    start_method = getattr(recorder, "start", None)
    if callable(start_method):
        start_method()
        return
    raise RuntimeError("AudioToTextRecorder does not expose a runnable method.")


async def echo(websocket):
    global client_websocket
    client_websocket = websocket
    try:
        async for message in websocket:
            if not recorder_ready.is_set():
                continue
            if not isinstance(message, (bytes, bytearray)):
                continue
            try:
                metadata_length = int.from_bytes(message[:4], byteorder="little")
                metadata_json = message[4:4 + metadata_length].decode("utf-8")
                metadata = json.loads(metadata_json)
                sample_rate = int(metadata.get("sampleRate", 16000))
                chunk = message[4 + metadata_length:]
                resampled_chunk = decode_and_resample(bytes(chunk), sample_rate, 16000)
                recorder.feed_audio(resampled_chunk)
            except Exception:
                continue
    finally:
        if client_websocket == websocket:
            client_websocket = None


async def main() -> None:
    global main_loop
    main_loop = asyncio.get_running_loop()

    recorder_thread = threading.Thread(target=run_recorder, daemon=True)
    recorder_thread.start()
    recorder_ready.wait()

    async with websockets.serve(echo, "0.0.0.0", 8001):
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
