import wavelink
import datetime

def format_time(ms):
    return str(datetime.timedelta(milliseconds=ms)).split('.')[0]

def create_progress_bar(player: wavelink.Player):
    if not player.current or player.current.length == 0: return "[🔘]"
    percent = player.position / player.current.length
    filled = int(percent * 20)
    return f"`{format_time(player.position)}` [{'▬'*filled}🔘{'▬'*(20-filled)}] `{format_time(player.current.length)}`"

async def apply_eq(player: wavelink.Player, preset: str):
    if preset == "flat":
        await player.set_filters(wavelink.Filters())
    elif preset == "bass":
        bands = [wavelink.EqualizerBand(i, 0.25) for i in range(5)]
        await player.set_filters(wavelink.Filters(equalizer=bands))
    elif preset == "treble":
        bands = [wavelink.EqualizerBand(i, 0.20) for i in range(10, 15)]
        await player.set_filters(wavelink.Filters(equalizer=bands))
    elif preset == "metal":
        bands = [
            wavelink.EqualizerBand(0, 0.2), wavelink.EqualizerBand(1, 0.2),
            wavelink.EqualizerBand(7, -0.2), wavelink.EqualizerBand(8, -0.2),
            wavelink.EqualizerBand(13, 0.2), wavelink.EqualizerBand(14, 0.2)
        ]
        await player.set_filters(wavelink.Filters(equalizer=bands))