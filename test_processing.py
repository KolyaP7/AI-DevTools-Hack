#!/usr/bin/env python3
"""Test script for video processing pipeline."""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from web_server import VideoProcessingHandler

# Mock request handler for testing
class MockHandler(VideoProcessingHandler):
    def __init__(self):
        # Don't call super().__init__ as it needs directory
        pass

async def test_processing():
    """Test the video processing pipeline."""
    handler = MockHandler()

    # Test with one of the available videos
    video_filename = "коля_IMG_9022.MOV"
    user_name = "Александр"

    print(f"Testing processing of {video_filename} for user {user_name}")

    try:
        result = await handler.process_video(video_filename, user_name)
        print(f"✅ Processing completed successfully: {result}")
        return True
    except Exception as e:
        print(f"❌ Processing failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    import asyncio
    success = asyncio.run(test_processing())
    sys.exit(0 if success else 1)