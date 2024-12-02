import os
import pygame
import time
from threading import Thread
import logging

logger = logging.getLogger('AudioManager')

class AudioManager:
    def __init__(self, audio_dir):
        self.audio_dir = audio_dir
        pygame.mixer.init()
        
    def play_number(self, number):
        """Play audio for a queue number (e.g., 'A001')"""
        try:
            # Create playlist of audio files to play
            playlist = []
            
            # Add "Antrian" sound
            playlist.append(os.path.join(self.audio_dir, "antrian.wav"))
            
            # Add counter letter sound (e.g., "A")
            playlist.append(os.path.join(self.audio_dir, f"{number[0].lower()}.wav"))
            
            # Convert number to integer and create number sounds
            num = int(number[1:])
            if num == 0:
                playlist.append(os.path.join(self.audio_dir, "0.wav"))
            else:
                # Handle hundreds
                hundreds = num // 100
                if hundreds > 0:
                    playlist.append(os.path.join(self.audio_dir, f"{hundreds}.wav"))
                    playlist.append(os.path.join(self.audio_dir, "ratus.wav"))
                
                # Handle remaining two digits
                remainder = num % 100
                if remainder > 0:
                    if remainder < 20:  # Direct number
                        playlist.append(os.path.join(self.audio_dir, f"{remainder}.wav"))
                    else:
                        # Handle tens
                        tens = (remainder // 10) * 10
                        ones = remainder % 10
                        playlist.append(os.path.join(self.audio_dir, f"{tens}.wav"))
                        if ones > 0:
                            playlist.append(os.path.join(self.audio_dir, f"{ones}.wav"))
            
            # Add "Counter" sound
            playlist.append(os.path.join(self.audio_dir, "counter.wav"))
            
            # Play the sequence in a separate thread
            Thread(target=self._play_sequence, args=(playlist,), daemon=True).start()
            
        except Exception as e:
            logger.error(f"Error playing audio for number {number}: {e}")
    
    def _play_sequence(self, playlist):
        """Play a sequence of audio files"""
        try:
            for audio_file in playlist:
                if os.path.exists(audio_file):
                    sound = pygame.mixer.Sound(audio_file)
                    sound.play()
                    # Wait for the sound to finish
                    time.sleep(sound.get_length())
                else:
                    logger.warning(f"Audio file not found: {audio_file}")
        except Exception as e:
            logger.error(f"Error playing audio sequence: {e}")

    def play_notification(self):
        """Play a simple notification sound"""
        try:
            sound_file = os.path.join(self.audio_dir, "simple_notification.wav")
            if os.path.exists(sound_file):
                sound = pygame.mixer.Sound(sound_file)
                sound.play()
        except Exception as e:
            logger.error(f"Error playing notification: {e}")
