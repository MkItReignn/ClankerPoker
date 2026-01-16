# Blind Schedule Configurations

This directory contains blind schedule configurations for No-Limit Texas Hold'em tournaments. The system supports multiple tournament modes, all loaded into memory and accessible via the registry.

## File Structure

```
config/blind_schedule/
├── blind_schedule.json          # Main config (default_mode + mode definitions)
├── schedules/
│   ├── standard.json            # Standard mode schedule entries
│   ├── turbo.json               # Turbo mode schedule entries
│   └── marathon.json            # Marathon mode schedule entries
└── README.md
```

## Available Modes

### Standard (default)
**Balanced tournament structure**
- **Starting Stack**: 10,000 chips (100 big blinds at level 2)
- **Pace**: Moderate - allows for strategic play with increasing pressure
- **Level Duration**: 15 hands early → 12 hands mid → 10 hands late → 8 hands → 6 hands → 5 hands final
- **Blind Progression**: Gradual increases (25-50% early, 50-100% mid, 100%+ late)
- **Total Levels**: 17 levels covering ~147 hands
- **Best For**: Most tournament games, balanced action and strategy

### Turbo
**Fast-paced** - High action, shorter duration
- **Starting Stack**: 10,000 chips (100 big blinds at level 1)
- **Pace**: Aggressive - forces action quickly
- **Level Duration**: 8 hands early → 6 hands mid → 5 hands → 4 hands → 3 hands final
- **Blind Progression**: Rapid increases (50-100% per level)
- **Total Levels**: 13 levels covering ~66 hands
- **Best For**: Quick games, side events, high-stakes action

### Marathon
**Deep stack** - Slow progression, extended play
- **Starting Stack**: 10,000 chips (200 big blinds at level 1)
- **Pace**: Slow - allows for deep strategic play
- **Level Duration**: 20 hands early → 18 hands mid → 15 hands → 12 hands → 10 hands → 8 hands → 6 hands → 5 hands final
- **Blind Progression**: Gentle increases (25-50% per level)
- **Total Levels**: 19 levels covering ~213 hands
- **Best For**: Serious tournaments, large fields, players who want maximum strategic depth

## How to Use

The system loads all modes from `blind_schedule.json` and makes them available in memory. The default mode is specified in the main config file.

### Accessing Modes in Code

```python
from src.config.tournament import BlindScheduleConfigLoader

loader = BlindScheduleConfigLoader()
registry = loader.load()

# Get the default mode
default_schedule = registry.get_default()

# Get a specific mode
turbo_schedule = registry.get_mode("turbo")
marathon_schedule = registry.get_mode("marathon")

# List all available modes
available_modes = registry.list_modes()  # ['marathon', 'standard', 'turbo']
```

### Changing the Default Mode

Edit `blind_schedule.json` and change the `default_mode` field:

```json
{
  "default_mode": "turbo",  // Change from "standard" to "turbo"
  "modes": { ... }
}
```

### Adding a New Mode

1. Create a new schedule file in `schedules/` (e.g., `schedules/custom.json`)
2. Add the mode definition to `blind_schedule.json`:

```json
{
  "default_mode": "standard",
  "modes": {
    "standard": { ... },
    "turbo": { ... },
    "marathon": { ... },
    "custom": {
      "description": "My custom tournament structure",
      "file": "schedules/custom.json"
    }
  }
}
```

## Configuration Structure

### Main Config (`blind_schedule.json`)

```json
{
  "default_mode": "standard",
  "modes": {
    "standard": {
      "description": "Human-readable description",
      "file": "schedules/standard.json"
    }
  }
}
```

### Schedule Files (`schedules/*.json`)

Each schedule file contains only the entries:

```json
{
  "mode": "standard|turbo|marathon",
  "description": "Human-readable description of the schedule",
  "entries": [
    {
      "level": {
        "level": 1,
        "small_blind": 25,
        "big_blind": 50
      },
      "start_hand": 1,
      "duration_hands": 15
    }
  ]
}
```

### Fields

- **mode** (optional): Identifier for the schedule type
- **description** (optional): Human-readable description
- **entries** (required): Array of blind level entries
  - **level**: Blind level definition
    - **level**: Level number (1, 2, 3, ...)
    - **small_blind**: Small blind amount in chips
    - **big_blind**: Big blind amount in chips
  - **start_hand**: First hand number this level applies to (1-indexed, inclusive)
  - **duration_hands**: Number of hands this level lasts

### Rules

- Entries must be in ascending order by `start_hand`
- Entries must not overlap (each hand belongs to exactly one level)
- Entries must not have gaps (all hands from 1 to the last entry must be covered)
- The last entry continues indefinitely (no end hand limit)

## Design Principles

These schedules follow professional tournament blind structure principles:

1. **Starting Stack Depth**: Players start with 50-200 big blinds to allow strategic play
2. **Progressive Pressure**: Early levels are slower, late levels accelerate to force action
3. **Blind Increases**: Typically 25-100% per level, with larger jumps in turbo formats
4. **Level Duration**: Decreases as blinds increase to maintain tournament momentum
5. **Big Blind Progression**: Smooth increases prevent jarring transitions

## Customization

To create your own blind schedule:

1. Copy one of the existing files as a template
2. Adjust blind amounts and durations to your preference
3. Ensure entries are sequential with no gaps or overlaps
4. Test with your tournament configuration

## Notes

- The system uses **hand-based** progression, not time-based
- Starting chip stack is configured in `config/tournament/tournament.json`
- Blind schedules should be designed to work with your starting stack size
- For 10,000 chip starting stacks, aim for 50-200 big blinds at the first meaningful level
