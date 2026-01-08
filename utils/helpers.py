import wavelink
import datetime

def format_time(ms):
    if not ms:
        return "00:00"
    return str(datetime.timedelta(milliseconds=ms)).split('.')[0]

def create_progress_bar(player: wavelink.Player):
    """Generates a text-based progress bar for the Embed."""
    # 1. Check if audio is playing
    if not player.playing or not player.current:
        return "⏹️ **Stopped**"

    # 2. Handle Live Streams (Infinite length)
    if player.current.is_stream:
        return f"🔴 **Live Stream** | `{format_time(player.position)}` playing"

    # 3. Calculate Percentage
    # We guard against 0 division just in case
    duration = player.current.length
    position = player.position
    
    if duration == 0:
        return "Loading..."

    percent = position / duration
    total_blocks = 20 # Length of the bar
    filled_blocks = int(percent * total_blocks)

    # Clamp values to 0-20 (prevents visual bugs if lag occurs)
    filled_blocks = max(0, min(total_blocks, filled_blocks))
    
    # 4. Construct the String
    # ▬ represents played, 🔘 is current, ➖ is remaining
    bar = "▬" * filled_blocks + "🔘" + "➖" * (total_blocks - filled_blocks)
    
    return f"`{format_time(position)}` [{bar}] `{format_time(duration)}`"


async def apply_eq(player: wavelink.Player, preset: str):
    """(Your EQ logic from before keeps working here)"""
    filters = wavelink.Filters()
    bands = []
    
    if preset == "bass":
        bands = [wavelink.EqualizerBand(i, 0.30) for i in range(5)]
    elif preset == "treble":
        bands = [wavelink.EqualizerBand(i, 0.25) for i in range(10, 15)]
    elif preset == "metal":
        bands = [
            wavelink.EqualizerBand(0, 0.2), wavelink.EqualizerBand(1, 0.2),
            wavelink.EqualizerBand(7, -0.2), wavelink.EqualizerBand(8, -0.2),
            wavelink.EqualizerBand(13, 0.2), wavelink.EqualizerBand(14, 0.2)
        ]
        
    if bands:
        filters.equalizer.set(bands=bands)
    
    await player.set_filters(filters)