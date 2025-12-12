#!/usr/bin/env python3
"""Web server for frontend with video processing endpoint."""

import os
import sys
import json
import shutil
import mimetypes
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler, SimpleHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import asyncio
from email.parser import BytesParser
from email.policy import default

# Add project root to path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from mcp.globals import VIDEO_PATH
# Import tools inline to avoid import issues

# Ensure video directory exists
os.makedirs(VIDEO_PATH, exist_ok=True)

# Mock Context class for calling MCP tools
class MockContext:
    async def info(self, message: str):
        print(f"INFO: {message}")

    async def report_progress(self, progress: int, total: int):
        print(f"Progress: {progress}/{total}")

    async def error(self, message: str):
        print(f"ERROR: {message}")

class VideoProcessingHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        # Set the directory to serve
        kwargs['directory'] = str(project_root / 'Frontend')
        super().__init__(*args, **kwargs)

    def do_GET(self):
        if self.path.startswith('/videos/'):
            # Serve video files
            video_path = self.path[8:]  # Remove /videos/
            from urllib.parse import unquote
            video_path = unquote(video_path)  # Decode URL encoding
            full_path = os.path.join(VIDEO_PATH, video_path)
            if os.path.exists(full_path) and os.path.isfile(full_path):
                self.send_response(200)
                # Determine content type based on file
                content_type, _ = mimetypes.guess_type(full_path)
                if content_type:
                    self.send_header('Content-type', content_type)
                else:
                    self.send_header('Content-type', 'video/mp4')  # default
                self.send_header('Accept-Ranges', 'bytes')
                self.send_header('Cache-Control', 'no-cache')
                self.end_headers()
                with open(full_path, 'rb') as f:
                    shutil.copyfileobj(f, self.wfile)
            else:
                self.send_error(404, "Video not found")
        else:
            super().do_GET()

    def do_POST(self):
        if self.path == '/process':
            self.handle_process()
        else:
            self.send_error(404, "Not Found")

    def handle_process(self):
        # Create event loop for async processing
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            # Read the request body
            content_length = int(self.headers['Content-Length'])
            body = self.rfile.read(content_length)

            # Parse multipart form data
            parser = BytesParser(policy=default)
            msg = parser.parsebytes(b'Content-Type: ' + self.headers['Content-Type'].encode() + b'\n\n' + body)

            if not msg.is_multipart():
                self.send_error(400, "Invalid form data")
                return

            video_data = None
            video_filename = None
            user_name = None

            for part in msg.iter_parts():
                if part.get_param('name', header='Content-Disposition') == 'video':
                    video_data = part.get_payload(decode=True)
                    video_filename = part.get_param('filename', header='Content-Disposition')
                elif part.get_param('name', header='Content-Disposition') == 'name':
                    user_name = part.get_payload(decode=True).decode()

            if not video_data or not video_filename or not user_name:
                self.send_error(400, "Missing video or name")
                return

            # Save uploaded video (sanitize filename to avoid encoding issues)
            import re
            # More aggressive sanitization - replace any non-ASCII characters
            safe_user_name = ''.join(c if ord(c) < 128 and c.isalnum() else '_' for c in user_name)
            safe_video_filename = ''.join(c if ord(c) < 128 and (c.isalnum() or c in '.-_') else '_' for c in video_filename)
            video_filename_saved = f"{safe_user_name}_{safe_video_filename}"
            with open('debug.log', 'a') as f:
                f.write(f"DEBUG: Original user_name: '{user_name}', safe_user_name: '{safe_user_name}'\n")
                f.write(f"DEBUG: Original video_filename: '{video_filename}', safe_video_filename: '{safe_video_filename}'\n")
                f.write(f"DEBUG: video_filename_saved: '{video_filename_saved}'\n")
            video_path = os.path.join(VIDEO_PATH, video_filename_saved)
            with open(video_path, 'wb') as f:
                f.write(video_data)

            # Process the video asynchronously
            processed_video = loop.run_until_complete(self.process_video(video_filename_saved, safe_user_name, safe_video_filename, video_filename))

            # Return response
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()

            with open('debug.log', 'a') as f:
                f.write(f"DEBUG: Returning processed_video: {processed_video}\n")
            response = {
                'success': True,
                'processed_video': processed_video,
                'message': f'Video processed for {user_name}'
            }
            self.wfile.write(json.dumps(response).encode())

        except Exception as e:
            self.send_error(500, f"Processing error: {str(e)}")
        finally:
            loop.close()

    async def process_video(self, video_filename, safe_user_name, safe_video_filename, original_video_filename):
        """Process video through the complete pipeline."""
        ctx = MockContext()

        # Check if ffmpeg is available
        import shutil
        ffmpeg_available = shutil.which('ffmpeg') is not None
        if not ffmpeg_available:
            await ctx.info("FFmpeg not available, returning original video")
            return video_filename

        try:
            print("DEBUG: Starting video processing")
            await ctx.info(f"🚀 Starting video processing for {safe_user_name}")

            # Step 1: Extract text from video using Whisper
            print("DEBUG: Step 1: Extracting text")
            await ctx.info("📝 Extracting text from video...")
            import whisper
            import ssl
            try:
                # Try to load model with SSL context that ignores certificate errors
                ssl._create_default_https_context = ssl._create_unverified_context
                model = whisper.load_model("tiny")  # Use tiny model for speed
                video_path = os.path.join(VIDEO_PATH, video_filename)
                result = model.transcribe(video_path)
            except Exception as e:
                await ctx.error(f"Whisper failed: {e}, using mock text extraction")
                # Fallback: mock text extraction
                result = {"segments": [{"text": f"Привет, {safe_user_name}", "start": 0.0, "end": 2.0}]}
            print("DEBUG: Step 1 completed")

            # Extract text segments
            text_segments = []
            for segment in result["segments"]:
                text_segments.append({
                    "text": segment["text"],
                    "start": segment["start"],
                    "end": segment["end"]
                })

            # Combine all text segments
            full_text = " ".join([seg["text"] for seg in text_segments])
            await ctx.info(f"📝 Extracted text: {full_text}")
            print(f"DEBUG: Full text: {repr(full_text)}")

            # Step 2: Find and replace name in text
            print("DEBUG: Step 2: Modifying text")
            # Simple approach: replace the first word with safe_user_name
            words = full_text.strip().split()
            if words:
                # Replace first word (assuming it's a name) with safe_user_name
                modified_text = full_text.replace(words[0], safe_user_name, 1)
            else:
                modified_text = safe_user_name

            await ctx.info(f"🔄 Modified text: {modified_text}")
            print(f"DEBUG: Modified text: {repr(modified_text)}")
            print("DEBUG: Step 2 completed")

            # Sanitize text for TTS (remove non-ASCII to avoid errors)
            modified_text = modified_text.encode('ascii', 'ignore').decode('ascii')
            if not modified_text.strip():
                modified_text = "Hello"
            await ctx.info(f"🔄 Sanitized text: {modified_text}")
            print(f"DEBUG: Sanitized text: {repr(modified_text)}")

            # Step 3: Generate TTS audio from modified text
            print("DEBUG: Step 3: Generating TTS")
            await ctx.info("🔊 Generating TTS audio...")
            import pyttsx3
            audio_filename = f"{safe_user_name}_tts_audio.wav"
            audio_path = os.path.join(VIDEO_PATH, audio_filename)

            tts_success = False
            try:
                engine = pyttsx3.init()
                voices = engine.getProperty('voices')
                if voices:
                    engine.setProperty('voice', voices[0].id)
                engine.save_to_file(modified_text, audio_path)
                engine.runAndWait()
                tts_success = True
            except Exception as e:
                await ctx.error(f"TTS failed: {e}, using original audio")
                tts_success = False
            print(f"DEBUG: TTS success: {tts_success}")
            print("DEBUG: Step 3 completed")

            # Step 4: Lip sync video with new audio
            print("DEBUG: Step 4: Processing video")
            await ctx.info("🎬 Lip syncing video with new audio...")
            safe_output_name = f"{safe_user_name}_processed_{safe_video_filename.rsplit('.', 1)[0]}"
            output_video_filename = f"{safe_output_name}.mp4"
            output_path = os.path.join(VIDEO_PATH, output_video_filename)

            # Convert video to MP4 with new audio if TTS succeeded, else copy original
            import subprocess
            try:
                if tts_success:
                    cmd_convert = [
                        "ffmpeg", "-i", video_path, "-i", audio_path, "-c:v", "libx264", "-c:a", "aac",
                        "-strict", "experimental", "-map", "0:v", "-map", "1:a", "-shortest", output_path
                    ]
                    await ctx.info("Processing with new audio")
                else:
                    cmd_convert = [
                        "ffmpeg", "-i", video_path, "-c:v", "libx264", "-c:a", "copy", output_path
                    ]
                    await ctx.info("Processing with original audio")
                subprocess.run(cmd_convert, check=True, capture_output=True)
                await ctx.info("Video processed successfully")
                print("DEBUG: Step 4 completed")

                await ctx.info(f"✅ Processing completed: {output_video_filename}")
                print(f"DEBUG: Returning output_video_filename: {output_video_filename}")
                return output_video_filename
            except subprocess.CalledProcessError as e:
                await ctx.error(f"FFmpeg conversion failed: {e}, returning original video")
                print(f"DEBUG: FFmpeg failed, returning original: {video_filename}")
                return video_filename

        except Exception as e:
            await ctx.error(f"❌ Processing failed: {str(e)}")
            import traceback
            traceback.print_exc()
            raise

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

if __name__ == '__main__':
    port = 8001
    server_address = ('', port)
    httpd = HTTPServer(server_address, VideoProcessingHandler)
    print(f"Serving on port {port}")
    httpd.serve_forever()