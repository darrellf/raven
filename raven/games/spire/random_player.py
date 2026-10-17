"""A player that picks a random legal command. Costs nothing, proves the plumbing."""

import random

from raven.games.spire.actions import legal_commands


class RandomPlayer:
    def __init__(self, rng=None, end_turn_chance=0.1):
        self.rng = rng or random.Random()
        # In combat, usually play something rather than end the turn at once.
        self.end_turn_chance = end_turn_chance

    def choose(self, message, avoid=()):
        """Pick a command for `message`, skipping `avoid` unless nothing else is left.

        Returns None if there's no legal command.
        """
        legal = legal_commands(message)
        options = [c for c in legal if c not in avoid] or legal
        if not options:
            return None

        plays = [c for c in options if c.startswith(("PLAY", "POTION"))]
        others = [c for c in options if c not in plays]
        if plays and (not others or self.rng.random() >= self.end_turn_chance):
            return self.rng.choice(plays)
        return self.rng.choice(others)
