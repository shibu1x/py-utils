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
import pychromecast
from gtts import gTTS


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

Example:
  export CHROMECAST_NAME="Room speaker"
  export CHROMECAST_HOST=192.168.0.2
  export SERVER_URL=http://192.168.0.3:8080
  python tts_cast.py "Hello, world"
        """
    )

    parser.add_argument('text', help='Text to speak')
    parser.add_argument('--lang', '-l', default='ja', help='Language code (default: ja)')

    args = parser.parse_args()

    chromecast_name = os.environ.get('CHROMECAST_NAME')
    chromecast_host = os.environ.get('CHROMECAST_HOST')
    server_url = os.environ.get('SERVER_URL')

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
