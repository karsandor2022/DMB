import wavelink
import datetime

def format_time(ms):
    if not ms: return "00:00"
    return str(datetime.timedelta(milliseconds=ms)).split('.')[0]

def create_progress_bar(player: wavelink.Player):
    if not player.playing or not player.current:
        return "⏹️ **Stopped**"

    if player.current.is_stream:
        return f"🔴 **Live Stream** | `{format_time(player.position)}` playing"

    duration = player.current.length
    position = player.position
    
    if duration == 0: return "Loading..."

    percent = position / duration
    total_blocks = 20
    filled_blocks = int(percent * total_blocks)
    filled_blocks = max(0, min(total_blocks, filled_blocks))
    
    bar = "▬" * filled_blocks + "🔘" + "-" * (total_blocks - filled_blocks)
    return f"`{format_time(position)}` [{bar}] `{format_time(duration)}`"

async def apply_eq(player: wavelink.Player, preset: str):
    player.eq_preset = preset
    filters = wavelink.Filters()
    bands = []
    
    # We use dictionaries now instead of wavelink.EqualizerBand
    if preset == "flat":
        bands = []
    elif preset == "bass":
        # Boost Lows (Hz: 25, 40, 63, 100, 160)
        bands = [
            {'band': 0, 'gain': 0.5}, {'band': 1, 'gain': 0.4},
            {'band': 2, 'gain': 0.3}, {'band': 3, 'gain': 0.2},
            {'band': 4, 'gain': 0.1}
        ]
    elif preset == "treble":
        # Boost Highs
        bands = [
            {'band': 10, 'gain': 0.2}, {'band': 11, 'gain': 0.3},
            {'band': 12, 'gain': 0.4}, {'band': 13, 'gain': 0.5},
            {'band': 14, 'gain': 0.5}
        ]
    elif preset == "metal":
        # Scoop Mids (V-Shape)
        bands = [
            {'band': 0, 'gain': 0.4}, {'band': 1, 'gain': 0.3},
            {'band': 7, 'gain': -0.3}, {'band': 8, 'gain': -0.3},
            {'band': 13, 'gain': 0.4}, {'band': 14, 'gain': 0.5}
        ]
        
    if bands:
        filters.equalizer.set(bands=bands)
    
    await player.set_filters(filters)