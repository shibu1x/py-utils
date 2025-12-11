#!/usr/bin/env python3
"""
Google Nest Mini Text-to-Speech Cast

Creates audio files and calls Chromecast API only.
Audio file hosting is assumed to be handled externally.
"""
import os
import hashlib
import argparse
from pathlib import Path
from datetime import datetime
import pychromecast
from gtts import gTTS
import requests


def is_quiet_hours(start_hour=None, end_hour=None):
    """
    Check if current time is within quiet hours.

    Args:
        start_hour: Quiet hours start (0-23)
        end_hour: Quiet hours end (0-23)

    Returns:
        bool: True if within quiet hours, False otherwise
    """
    if start_hour is None or end_hour is None:
        return False

    current_hour = datetime.now().hour

    # Cross midnight (e.g., 23:00-07:00)
    if start_hour > end_hour:
        return current_hour >= start_hour or current_hour < end_hour
    # Same day (e.g., 13:00-14:00)
    else:
        return start_hour <= current_hour < end_hour


def send_discord_notification(webhook_url, text):
    """
    Send notification to Discord via webhook.

    Args:
        webhook_url: Discord webhook URL
        text: Message text to send

    Returns:
        bool: True on success, False on failure
    """
    try:
        payload = {"content": text}
        response = requests.post(webhook_url, json=payload, timeout=10)

        if response.status_code == 204:
            print(f"✓ Discord notification sent")
            return True
        else:
            print(f"✗ Discord notification failed: HTTP {response.status_code}")
            print(f"  Response: {response.text}")
            return False

    except Exception as e:
        print(f"✗ Discord notification error: {e}")
        return False


class SimpleTTSCaster:
    def __init__(self, chromecast_name=None, chromecast_host=None):
        """
        Initialize TTS caster.

        Args:
            chromecast_name: Chromecast friendly_name (from CHROMECAST_NAME env var if omitted)
            chromecast_host: Chromecast IP address (used as search hint)
        """
        if chromecast_name is None:
            chromecast_name = os.environ.get('CHROMECAST_NAME')

        self.chromecast_name = chromecast_name
        self.chromecast_host = chromecast_host
        self.cast = None
        self.browser = None

    def connect(self):
        """Search for and connect to Chromecast by friendly_name."""
        print(f"Searching for Chromecast: {self.chromecast_name}")
        if self.chromecast_host:
            print(f"  Search hint (IP address): {self.chromecast_host}")

        try:
            known_hosts = [self.chromecast_host] if self.chromecast_host else None

            chromecasts, self.browser = pychromecast.get_listed_chromecasts(
                friendly_names=[self.chromecast_name],
                known_hosts=known_hosts,
                discovery_timeout=10
            )

            if not chromecasts:
                print(f"✗ Device not found: {self.chromecast_name}")
                if not self.chromecast_host:
                    print("\nHint: Setting CHROMECAST_HOST environment variable with IP address will speed up search")
                return None

            self.cast = chromecasts[0]
            self.cast.wait(timeout=30)

            print(f"✓ Connection successful: {self.cast.name}")
            print(f"  Model: {self.cast.model_name}")
            print(f"  UUID: {self.cast.uuid}")

            return self.cast

        except Exception as e:
            print(f"✗ Connection error: {e}")
            import traceback
            traceback.print_exc()
            return None

    def create_audio_file(self, text, output_path, lang='ja'):
        """
        Convert text to audio file.

        Args:
            text: Text to speak
            output_path: Output file path
            lang: Language code (default: ja)

        Returns:
            bool: True on success, False on failure
        """
        if os.path.exists(output_path):
            print(f"Audio file already exists (skipping gTTS): {output_path}")
            return True

        print(f"Generating audio file: {text[:50]}...")

        try:
            tts = gTTS(text=text, lang=lang)
            tts.save(output_path)
            print(f"✓ Audio file generated: {output_path}")
            return True

        except Exception as e:
            print(f"✗ Audio file generation error: {e}")
            return False

    def play_from_url(self, audio_url):
        """
        Play audio from specified URL on Chromecast.

        Args:
            audio_url: Audio file URL (external HTTP server)

        Returns:
            bool: True on success, False on failure
        """
        if not self.cast:
            print("✗ Not connected to Chromecast")
            return False

        print(f"Playing audio: {audio_url}")

        mc = self.cast.media_controller

        try:
            mc.play_media(audio_url, 'audio/mp3')
            print("✓ Playback started")
            mc.block_until_active()
            return True

        except Exception as e:
            error_msg = str(e)
            print(f"✗ Playback error: {error_msg}")
            print("\nPossible causes:")
            print("  1. Chromecast is being used by another app")
            print("  2. Network connection issue")
            print("  3. HTTP server is not accessible")
            print(f"\nCheck HTTP server: curl {audio_url}")
            return False

    def disconnect(self):
        """Disconnect from Chromecast."""
        if self.cast:
            try:
                self.cast.disconnect()
            except Exception:
                pass

        if self.browser:
            try:
                pychromecast.discovery.stop_discovery(self.browser)
            except Exception:
                pass


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Play TTS on Google Nest Mini',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Required environment variables:
  CHROMECAST_NAME, CHROMECAST_HOST, SERVER_URL

Optional environment variables:
  QUIET_START_HOUR: Start hour for quiet period (0-23)
  QUIET_END_HOUR: End hour for quiet period (0-23)
  WEBHOOK_URL: Discord webhook URL (required when using --discord)

Example:
  export CHROMECAST_NAME="Room speaker"
  export CHROMECAST_HOST=192.168.0.2
  export SERVER_URL=http://192.168.0.3:8080
  export QUIET_START_HOUR=23
  export QUIET_END_HOUR=7
  export WEBHOOK_URL=https://discord.com/api/webhooks/...
  python tts_cast.py "Hello, world"
  python tts_cast.py --discord "Hello, world"
        """
    )

    parser.add_argument('text', help='Text to speak')
    parser.add_argument('--lang', '-l', default='ja', help='Language code (default: ja)')
    parser.add_argument('--discord', '-d', action='store_true', help='Send notification to Discord')

    args = parser.parse_args()

    chromecast_name = os.environ.get('CHROMECAST_NAME')
    chromecast_host = os.environ.get('CHROMECAST_HOST')
    server_url = os.environ.get('SERVER_URL')
    webhook_url = os.environ.get('WEBHOOK_URL')

    # Quiet hours configuration
    quiet_start = os.environ.get('QUIET_START_HOUR')
    quiet_end = os.environ.get('QUIET_END_HOUR')

    quiet_start_hour = None
    quiet_end_hour = None

    if quiet_start:
        try:
            quiet_start_hour = int(quiet_start)
            if not 0 <= quiet_start_hour <= 23:
                print(f"Warning: QUIET_START_HOUR must be 0-23, got {quiet_start_hour}")
                quiet_start_hour = None
        except ValueError:
            print(f"Warning: QUIET_START_HOUR must be an integer, got {quiet_start}")

    if quiet_end:
        try:
            quiet_end_hour = int(quiet_end)
            if not 0 <= quiet_end_hour <= 23:
                print(f"Warning: QUIET_END_HOUR must be 0-23, got {quiet_end_hour}")
                quiet_end_hour = None
        except ValueError:
            print(f"Warning: QUIET_END_HOUR must be an integer, got {quiet_end}")

    # Check if Discord webhook URL is provided when --discord option is used
    if args.discord and not webhook_url:
        print("Error: WEBHOOK_URL environment variable not set")
        print("Please set WEBHOOK_URL when using --discord option")
        print("\nExample:")
        print('  export WEBHOOK_URL=https://discord.com/api/webhooks/...')
        return 1

    # Send Discord notification first (ignores quiet hours)
    if args.discord:
        print("=" * 60)
        print(f"Sending Discord notification: {args.text}")
        print("=" * 60)
        print()

        if not send_discord_notification(webhook_url, args.text):
            print("Warning: Discord notification failed")

        print()

    # Check if current time is within quiet hours (only for Chromecast)
    if is_quiet_hours(quiet_start_hour, quiet_end_hour):
        current_time = datetime.now().strftime('%H:%M')
        print(f"Quiet hours: Chromecast notifications are disabled ({quiet_start_hour}:00-{quiet_end_hour}:00)")
        print(f"Current time: {current_time}")
        return 0

    missing_vars = []
    if not chromecast_name:
        missing_vars.append('CHROMECAST_NAME')
    if not chromecast_host:
        missing_vars.append('CHROMECAST_HOST')
    if not server_url:
        missing_vars.append('SERVER_URL')

    if missing_vars:
        print(f"Error: Required environment variable(s) not set: {', '.join(missing_vars)}")
        print("\nExample:")
        print('  export CHROMECAST_NAME="Room speaker"')
        print('  export CHROMECAST_HOST=192.168.0.2')
        print('  export SERVER_URL=http://192.168.0.3:8080')
        return 1

    script_dir = Path(__file__).parent
    audio_dir = script_dir / 'data'
    os.makedirs(audio_dir, exist_ok=True)

    text_hash = hashlib.md5(args.text.encode('utf-8')).hexdigest()
    filename = f"{text_hash}.mp3"
    audio_file_path = audio_dir / filename

    audio_url = f"{server_url.rstrip('/')}/{filename}"

    caster = SimpleTTSCaster(chromecast_name=chromecast_name, chromecast_host=chromecast_host)

    print("=" * 60)
    print("Settings:")
    print(f"  Text: {args.text}")
    print(f"  Language: {args.lang}")
    print(f"  Chromecast name: {caster.chromecast_name}")
    print(f"  Chromecast host: {caster.chromecast_host}")
    if quiet_start_hour is not None and quiet_end_hour is not None:
        print(f"  Quiet hours: {quiet_start_hour}:00-{quiet_end_hour}:00")
    print(f"  Audio file: {audio_file_path}")
    print(f"  Audio URL: {audio_url}")
    print("=" * 60)
    print()

    try:
        if not caster.create_audio_file(args.text, audio_file_path, args.lang):
            return 1

        print()

        if not caster.connect():
            return 1

        print()

        if not caster.play_from_url(audio_url):
            return 1

        print()
        print("=" * 60)
        print("✓ All operations completed successfully")
        print("=" * 60)

        return 0

    except KeyboardInterrupt:
        print("\nInterrupted")
        return 1

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        caster.disconnect()


if __name__ == '__main__':
    exit(main())
