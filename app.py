import re
import os
import cv2
import time
import queue
import threading
import numpy as np
from streamlink import Streamlink
from playsound import playsound as play_sound
from pytesseract import image_to_string as OCR

# Global variables

should_notify_betting_started = True


class RealtimeVideoCapture:
    """
    Bufferless Video Capture class.

    Credit
        Ulrich Stern https://stackoverflow.com/a/54755738.
    """

    def __init__(self, name):
        self.cap = cv2.VideoCapture(name)
        self.q = queue.Queue()
        t = threading.Thread(target=self._reader, daemon=True)
        t.start()

    def _reader(self):
        """
        Read frames as soon as they are available, discarding all but the most recent frame.
        """
        while True:
            ret, frame = self.cap.read()
            if not ret:
                break
            if not self.q.empty():
                try:
                    # Discard unprocessed frames
                    self.q.get_nowait()
                except queue.Empty:
                    pass
            self.q.put(frame)

    def read(self):
        """
        Fetch the most recent frame from the VideoCapture queue.
        """
        return self.q.get()


def get_latest_frame_from_stream(stream_url: str) -> np.ndarray:
    """
    Get the most recent frame from a live video stream.

    Creates a new instance of cv2::VideoCapture for each frame grab to avoid continuous data streaming.

    @param stream_url Desired video stream URL.
    @rtype np.ndarray
    @return Processed video frame.
    """
    cap = cv2.VideoCapture(stream_url)
    ret, frame = cap.read()
    cap.release()
    return frame


def strip_special_chars(text: str) -> str:
    stripped_text = text\
        .replace('\n', ' ')\
        .replace('"', '')\
        .replace('“', '')\
        .replace('‘', '')\
        .replace('.', '')\
        .replace(',', '')\
        .replace('-', '')\
        .replace('+', '')\
        .replace('|', '')\
        .replace('/', '')\
        .replace('\\', '')\
        .replace('(', '')\
        .replace(')', '')\
        .replace('{', '')\
        .replace('}', '')\
        .replace('~', '')\
        .replace('   ', ' ')\
        .replace('  ', ' ')
    return stripped_text


def extract_status_from_frame(frame):
    global should_notify_betting_started

    status = {
        'is_open': False,
        'time_remaining': 0,
        'bet_totals': {
            'blue': 0,
            'red': 0
        },
        'rating': 0,
        'region': 'None'
    }

    # Make a copy of the original frame
    frame_copy = frame.copy()

    # Crop the frame down to the bet totals/countdown section
    status_frame_region = frame_copy[:64, -168:]

    # Run OCR to extract text from the cropped frame
    # Examples:
    #   closed 318 rating on tr closed closed
    #   closed 318 rating on tr 56607 75960
    #   00:00 378 rating on tr fore open
    #   01:32 378 rating on tr open open
    text = OCR(status_frame_region, lang='eng')
    text = strip_special_chars(text).lower()

    search_game_info = re.search(r'rating', text)
    if search_game_info:
        # Extract rating and region from the text
        search_rating = re.search(r'[\d]{3,4}', text)
        search_region = re.search(r'(?<=rating on )\w+', text)
        status['rating'] = search_rating.group() if search_rating else 0
        status['region'] = search_region.group().upper() if search_region else 'None'

        # Extract the countdown timer from the text
        search_closed = re.search(r'closed', text)
        if search_closed:
            should_notify_betting_started = True

            # Extract the bet totals from the text
            search_bets = re.search(r'[\d]{2,8} [\d]{2,8}', text)
            bets = search_bets.group().split(' ') if search_bets else None
            if bets and len(bets) > 1:
                try:
                    status['bet_totals']['blue'] = int(bets[0])
                except ValueError:
                    pass
                try:
                    status['bet_totals']['red'] = int(bets[1])
                except ValueError:
                    pass
        else:
            status['is_open'] = True

            search_timer = re.search(r'[\d]{0,2}:[\d]{0,2}', text)
            timer = search_timer.group().split(':') if search_timer else None
            if timer and len(timer) > 1:
                minutes = 0
                seconds = 0

                try:
                    minutes = int(timer[0])
                except ValueError:
                    pass
                try:
                    seconds = int(timer[1])
                except ValueError:
                    pass

                status['time_remaining'] = minutes * 60 + seconds

    return status


def notify_game_start():
    global should_notify_betting_started

    # Play a sound effect
    sound = 'sound-effects/game-start.mp3'
    play_sound(sound, block=False)

    # Show an alert
    alert_text = 'Betting has started'
    alert_title = 'SaltyTeemo'
    cmd = """
    osascript -e 'display notification "%s" with title "%s"'
    """ % (alert_text, alert_title)
    os.system(cmd)

    should_notify_betting_started = False

    # Wait 5 minutes before checking again since a game just started
    time.sleep(5. * 60.)


def main():
    global should_notify_betting_started

    # Get a URL for the live video stream from Twitch
    session = Streamlink()
    streams = session.streams('https://twitch.tv/saltyteemo')
    stream = streams['720p60'] if '720p60' in streams.keys() else streams['480p']
    stream_url = stream.to_url()

    while True:
        # Wait 20 seconds between frame grabs
        time.sleep(10.)

        frame = get_latest_frame_from_stream(stream_url)

        betting_status = extract_status_from_frame(frame)
        if betting_status['is_open'] and should_notify_betting_started:
            notify_game_start()

        if chr(cv2.waitKey(1) & 255) == 'q':
            break


if __name__ == '__main__':
    main()
