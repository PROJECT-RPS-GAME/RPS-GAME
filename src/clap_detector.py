"""Detect a clap from two hands moving together in the camera image."""
import math


class ClapDetector:
    ARM_DISTANCE = 1.8
    CONTACT_DISTANCE = 1.3
    APPROACH_WINDOW = 0.8

    def __init__(self):
        self._armed = False
        self._approach_started = None
        self._previous_distance = None

    @staticmethod
    def _palm(hand):
        landmarks = hand.landmarks
        palm = tuple(sum(landmarks[i][axis] for i in (0, 5, 9, 13, 17)) / 5
                     for axis in (0, 1))
        width = math.hypot(landmarks[5][0] - landmarks[17][0],
                           landmarks[5][1] - landmarks[17][1])
        return palm, width

    def update(self, hands, now):
        """Return True once when two hands close together after being apart."""
        if len(hands) != 2:
            self._armed = False
            self._approach_started = None
            self._previous_distance = None
            return False

        (palm_a, width_a), (palm_b, width_b) = (self._palm(hand) for hand in hands)
        scale = (width_a + width_b) / 2
        if scale <= 1e-6:
            self._armed = False
            self._approach_started = None
            self._previous_distance = None
            return False

        distance = math.hypot(palm_a[0] - palm_b[0], palm_a[1] - palm_b[1]) / scale
        previous = self._previous_distance
        self._previous_distance = distance

        if distance >= self.ARM_DISTANCE:
            self._armed = True
            self._approach_started = None
            return False
        if not self._armed:
            return False

        if self._approach_started is None:
            self._approach_started = now
        approaching = previous is not None and distance < previous
        in_time = now - self._approach_started <= self.APPROACH_WINDOW
        if approaching and in_time and distance <= self.CONTACT_DISTANCE:
            self._armed = False
            self._approach_started = None
            return True
        return False
