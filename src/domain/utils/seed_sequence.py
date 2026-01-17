"""Utilities for generating deterministic seed sequences from a base seed."""

from __future__ import annotations

from random import Random


class SeedSequence:
    """
    Generates a deterministic sequence of integers from a base seed.

    Each element in the sequence can be used as a seed for shuffling operations.
    The sequence is deterministic: given the same base seed, it always produces
    the same sequence of integers.

    Usage:
        sequence = SeedSequence(base_seed=42)
        shuffle_seed_0 = sequence[0]  # For button initialization
        shuffle_seed_1 = sequence[1]  # For hand 1
        shuffle_seed_2 = sequence[2]  # For hand 2
    """

    def __init__(self, base_seed: int) -> None:
        """Initialize with a base seed.

        Args:
            base_seed: The base seed value for generating the sequence.
        """
        self._base_seed = base_seed
        # Pre-generate a cache of seeds for efficiency
        # We'll generate on-demand but cache for performance
        self._cache: dict[int, int] = {}

    def __getitem__(self, index: int) -> int:
        """
        Get the seed value at the given index.

        Args:
            index: Zero-based index in the sequence (0 = button init, 1 = hand 1, etc.)

        Returns:
            A deterministic integer seed value for the given index.

        Raises:
            ValueError: If index is negative.
        """
        if index < 0:
            raise ValueError(f"Index must be non-negative, got {index}")

        if index in self._cache:
            return self._cache[index]

        # Generate deterministic seed for this index
        # Use a master RNG seeded with base_seed to generate seeds for each index
        master_rng = Random(self._base_seed)

        # Fast-forward to the desired index by generating seeds sequentially
        # This ensures determinism: same base_seed always produces same sequence
        for i in range(index + 1):
            if i not in self._cache:
                # Generate a 64-bit seed value
                seed_value = master_rng.getrandbits(64)
                self._cache[i] = seed_value

        return self._cache[index]

    def get_shuffle_seed_for_button_init(self) -> int:
        """Get seed for button initialization (index 0).

        Returns:
            Seed value for button initialization shuffle.
        """
        return self[0]

    def get_shuffle_seed_for_hand(self, hand_number: int) -> int:
        """
        Get seed for shuffling deck for a specific hand.

        Args:
            hand_number: The hand number (1-indexed)

        Returns:
            Seed value for this hand (uses index = hand_number)

        Raises:
            ValueError: If hand_number is less than 1.
        """
        if hand_number < 1:
            raise ValueError(f"Hand number must be at least 1, got {hand_number}")
        return self[hand_number]
