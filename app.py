import cv2
import time
import queue
import threading
from streamlink import Streamlink


class VideoCapture:
    """
    Bufferless Video Capture class.

    Credit
        Ulrich Stern https://stackoverflow.com/a/54755738.
    """
    def __init__(self, name):
        self.cap = cv2.VideoCapture(name)
        self.q = queue.Queue()
        t = threading.Thread(target=self._reader)
        t.daemon = True
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


def main():
    # Get a URL for the live video stream from Twitch
    session = Streamlink()
    streams = session.streams('https://twitch.tv/saltyteemo')
    stream = streams['720p60'] if '720p60' in streams.keys() else streams['480p']
    stream_url = stream.to_url()

    cap = VideoCapture(stream_url)

    while True:
        # Wait 1 second between frame grabs
        time.sleep(1.)

        frame = cap.read()
        cv2.imshow('frame', frame)

        if chr(cv2.waitKey(1)&255) == 'q':
            break


if __name__ == '__main__':
    main()

