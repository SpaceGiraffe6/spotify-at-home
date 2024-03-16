from enum import Enum

def to_seconds(minutes:int, seconds:int) -> int:
    return (minutes * 60 + seconds)

# ANSI color code format: \033[38;2;<r>;<g>;<b>m
    # or: \033[38;5;<color code>m
    # table of color codes at https://i.stack.imgur.com/KTSQa.png
class Colors(Enum):
    reset = "\033[0m"
    bold = "\033[1m"
    underline = "\033[4m"
    bolded_white = "\033[1;37m"
    faint = "\033[2m"
    blink = "\033[5m"
    pink = "\033[38;2;255;179;180m"
    red = "\033[0;31m"
    underlined_red = "\033[4;31m"
    green = "\033[0;32m"
    light_green = "\033[1;32m"
    mint_green = "\033[38;2;128;255;170m"
    aquamarine = "\033[38;2;102;255;204m"
    blue = "\033[1;34m"
    light_blue = "\033[0;34m"
    cool_blue = "\033[38;2;179;229;255m"
    cyan = "\033[0;36m"
    yellow = "\033[0;33m"
    bolded_yellow = "\033[1;33m"
    light_yellow = "\033[38;5;228m"
    orange = "\033[38;5;214m"
    purple = "\033[0;35m"
    bolded_purple = "\033[1;35"
    light_purple = "\033[1;35m"

class Modifiers(Enum):
    hot = {"color" : Colors.pink, "description" : "While in shuffle mode, increase the chance of a song being played and disables its cooldown"}
    cold = {"color" : Colors.cool_blue, "description" : "While in shuffle mode, lower the chance of a song being played"}
    disabled = {"color" : Colors.faint, "description" : "While in loop or shuffle mode, prevent this song from being played"}
    synced = {"color" : Colors.aquamarine, "description" : "While in shuffle mode, consider each set of synced songs as one song when choosing the next song"}

# Don't put the ".wav" after song names in the sequences and song_lengths dictionaries
SEQUENCES:"dict[str, list[str]]" = {"Sparkle - movie ver" : ["Nandemonaiya (English)"],
            "Snowdin Town" : ["His Theme", "Home"],
            "Brave Song (Piano)" : ["Qingyun Peak"]}

SONG_LENGTHS:"dict[str, int]" = {"Asayake no Starmine" : to_seconds(1, 30),
                "Brave Song (Piano)" : to_seconds(5, 16),
                "Bravely You (Guitar)" : to_seconds(1, 48),
                "Cinderella (Piano)" : to_seconds(3, 31),
                "Courage (Piano)" : to_seconds(2, 16),
                "Dyson Sphere" : to_seconds(6, 16),
                "God Save the Queen" : to_seconds(0, 52),
                "Goodbye Seven Seas (Piano)" : to_seconds(5, 9),
                "Grand Escape - movie ver" : to_seconds(3, 8),
                "Hacking to the Gate (Guitar)" : to_seconds(1, 39),
                "Harvest (Guitar)" : to_seconds(1, 35),
                "His Theme" : to_seconds(2, 5),
                "Home" : to_seconds(2, 3),
                "Ienai (Piano)" : to_seconds(1, 29),
                "Into the Night" : to_seconds(4, 35),
                "Is There Still Anything That Love Can Do" : to_seconds(6, 54),
                "My Dearest (Piano)" : to_seconds(6, 19),
                "Katawaredoki (Piano)" : to_seconds(2, 47),
                "Kimi to iu Shinwa (Piano)" : to_seconds(5, 8),
                "Kiss of Death (Piano)" : to_seconds(4, 10),
                "Kodou (Piano)" : to_seconds(1, 30),
                "Koko de Ikiteru (Piano)" : to_seconds(1, 28),
                "Kyukyoku Unbalance! (Piano)" : to_seconds(1, 36),
                "Kyukyoku Unbalance!" : to_seconds(4, 15),
                "NAME (Piano)" : to_seconds(1, 31),
                "Nandemonaiya (English)" : to_seconds(5, 42),
                "Nandemonaiya" : to_seconds(5, 44),
                "Natsunagi (Piano)" : to_seconds(3, 8),
                "Please Look at Me More" : to_seconds(2, 26),
                "Qingyun Peak" : to_seconds(1, 7),
                "Renai Circulation (English)" : to_seconds(4, 13),
                "Renai Circulation" : to_seconds(4, 14),
                "Sapphire Phantasm (Piano)" : to_seconds(4, 12),
                "Scarborough Fair" : to_seconds(3, 9),
                "Shelter (Guitar)" : to_seconds(3, 38),
                "Shelter (Instrumental)" : to_seconds(3, 18),
                "Shelter (Piano)" : to_seconds(5, 12),
                "Skyhook" : to_seconds(7, 1),
                "Snowdin Town" : to_seconds(1, 16),
                "Sparkle - movie ver" : to_seconds(8, 54),
                "Takaramono ni Natta Hi (Piano)" : to_seconds(2, 29),
                "The Egg" : to_seconds(10, 26),
                "The Tail End" : to_seconds(7, 26),
                "This Game (Piano)" : to_seconds(5, 6),
                "Turing Love" : to_seconds(3, 37),
                "Uchiage Hanabi (Piano)" : to_seconds(4, 38),
                "Undertale Theme" : to_seconds(6, 21),
                "Unravel (Piano)" : to_seconds(4, 8),
                "Your Reality (Guitar)" : to_seconds(3, 7),
                "Your Reality" : to_seconds(3, 1)}

# Each song can only have up to one of the modifiers in each set at the same time
EXCLUSIVE_MODIFIERS:"list[set[Modifiers]]" = [{Modifiers.hot, Modifiers.cold}]