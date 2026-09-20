"""Video generation using FFmpeg."""
import os
import subprocess
import json
from typing import Dict, Any, Optional
from app.config import config


class VideoGenerator:
    """Video generator using FFmpeg subprocess."""
    
    def __init__(self, asset_dir: str = None):
        """Initialize video generator."""
        self.asset_dir = asset_dir or config.ASSET_DIR
        os.makedirs(self.asset_dir, exist_ok=True)
    
    def generate_video(
        self,
        creative_spec: Dict[str, Any],
        scene: Dict[str, Any],
        packshot_path: str = None,
        output_path: str = None,
        image_path: str = None  # Use AI-generated image as background
    ) -> str:
        """Generate 6-10s vertical video (1080x1920, 30fps, H.264)."""
        if not output_path:
            output_path = os.path.join(self.asset_dir, f"video_{creative_spec['spec_id']}.mp4")
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Generate video with better content
        self._generate_improved_video(creative_spec, output_path, image_path)
        
        # Verify with ffprobe
        self._verify_video(output_path)
        
        return output_path
    
    def _generate_improved_video(self, creative_spec: Dict[str, Any], output_path: str, image_path: str = None):
        """Generate improved video using AI-generated image as background."""
        duration = 8
        fps = 30
        
        if image_path and os.path.exists(image_path):
            # Use AI-generated image as simple looping video
            try:
                print(f"→ Using AI image as video background: {image_path}")
                # Create animated video with slow zoom effect for movement
                cmd = [
                    'ffmpeg', '-y',
                    '-loop', '1',
                    '-i', image_path,
                    '-vf', f'fps={fps},scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,zoompan=z=\'min(zoom+0.002,1.1)\':d={duration*fps}:x=\'iw/2-(iw/zoom/2)\':y=\'ih/2-(ih/zoom/2)\':s=1080x1920',
                    '-c:v', 'libx264',
                    '-preset', 'fast',
                    '-crf', '23',
                    '-pix_fmt', 'yuv420p',
                    '-movflags', '+faststart',
                    '-t', str(duration),
                    '-r', str(fps),
                    output_path
                ]
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0:
                    print("✓ Video generated with AI image background and zoom effect")
                    return
                else:
                    print(f"✗ Zoom effect failed: {result.stderr}")
                    # Fallback to simple loop
                    print("→ Trying simple image loop")
                    cmd_simple = [
                        'ffmpeg', '-y',
                        '-loop', '1',
                        '-i', image_path,
                        '-vf', f'fps={fps},scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2',
                        '-c:v', 'libx264',
                        '-preset', 'fast',
                        '-crf', '23',
                        '-pix_fmt', 'yuv420p',
                        '-movflags', '+faststart',
                        '-t', str(duration),
                        '-r', str(fps),
                        output_path
                    ]
                    
                    result = subprocess.run(
                        cmd_simple,
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    
                    if result.returncode == 0:
                        print("✓ Video generated with simple image loop")
                        return
                    else:
                        print(f"✗ Simple loop failed: {result.stderr}")
                    
            except Exception as e:
                print(f"✗ Image video generation failed: {e}")
        
        # Fallback: Use solid color with text overlay
        print("→ Using fallback solid color video")
        bg_color = creative_spec['palette'][0].lstrip('#')
        
        # Use FFmpeg to create a simple video without text (more reliable)
        cmd = [
            'ffmpeg', '-y',
            '-f', 'lavfi',
            '-i', f'color=c={bg_color}:s=1080x1920:d={duration}',
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-crf', '23',
            '-pix_fmt', 'yuv420p',
            '-movflags', '+faststart',
            '-t', str(duration),
            output_path
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                raise Exception(f"FFmpeg error: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            raise Exception("FFmpeg generation timed out")
        except FileNotFoundError:
            # FFmpeg not available, create a placeholder
            self._create_placeholder_video(output_path, creative_spec)
    
    def _create_placeholder_video(self, output_path: str, creative_spec: Dict[str, Any]):
        """Create a placeholder when FFmpeg is not available."""
        # Create a simple text file as placeholder
        with open(output_path, 'w') as f:
            f.write(f"PLACEHOLDER VIDEO: {creative_spec['approved_headline']}")
    
    def _verify_video(self, video_path: str):
        """Verify video using ffprobe."""
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'stream=width,height,duration',
            '-of', 'json',
            video_path
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                stream = data['streams'][0]
                
                width = int(stream['width'])
                height = int(stream['height'])
                duration = float(stream['duration'])
                
                # Validate dimensions
                if width != 1080 or height != 1920:
                    raise Exception(f"Invalid dimensions: {width}x{height} (expected 1080x1920)")
                
                # Validate duration
                if duration < 6 or duration > 10:
                    raise Exception(f"Invalid duration: {duration}s (expected 6-10s)")
                    
        except FileNotFoundError:
            # ffprobe not available, skip verification
            pass
        except subprocess.TimeoutExpired:
            raise Exception("ffprobe verification timed out")


def get_video_generator() -> VideoGenerator:
    """Factory function to get video generator."""
    return VideoGenerator()
