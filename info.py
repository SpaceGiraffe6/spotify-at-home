from enum import Enum

TICK_DURATION:float = 0.5 # seconds. Best if TICK_DURATION <= 1
TIMER_RESOLUTION:float = 0.2 # seconds

PLACEHOLDER_SONGNAME:str = "*"
LYRIC_PLACEHOLDER_CHARACTER:str = "\u2669" # Used in lyric lines when the song doesn't have any words for that part

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
    underline_red = "\033[4;31m"
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
# Defaults to blue
def color(string:str, color:Colors = Colors.blue) -> str:
    return f"{color.value}{string}\033[0m"
# Removes all color and reset tags from string and returns the processed string
def remove_tags(string:str) -> str:
    for tag in Colors._value2member_map_.keys(): # Iterate through the values of the enums in Colors
        string = string.replace(tag, "")

    return string

STANDARD_SONG_LENGTH:int = 180 # Used to scale the weight of each song by its length
BASE_SONG_WEIGHT:int = 120 # because 120 is divisible by almost everything
RATE_CHANGE:int = 3 # How many times more/less likely it is for a hot/cold song to be chosen
class Modifiers(Enum):
    hot = {"color" : Colors.pink, "description" : "While in shuffle mode, increase the chance of a song being played and disables its cooldown", "weight update" : lambda curr_weight, *_ : round(curr_weight*RATE_CHANGE)}
    cold = {"color" : Colors.cool_blue, "description" : "While in shuffle mode, decrease the chance of a song being played", "weight update" : lambda curr_weight, *_ : round(curr_weight/RATE_CHANGE)}
    synced = {"color" : Colors.aquamarine, "description" : "While in shuffle mode, consider each set of synced songs as one song when choosing the next song", "weight update" : lambda curr_weight, synced_songs_count : round(curr_weight/synced_songs_count)}
MODIFIERS_COLORING_ORDER:"list[Modifiers]" = [Modifiers.hot, Modifiers.cold, Modifiers.synced]

class SongAttributes(Enum):
    playing = Colors.green
    disabled = Colors.faint
    queued = Colors.purple
    sequenced = Colors.yellow
    modifiers = None
ATTRIBUTES_COLORING_ORDER:"list[SongAttributes]" = [SongAttributes.disabled, SongAttributes.playing, SongAttributes.queued, SongAttributes.sequenced, SongAttributes.modifiers]

# Each song can only have up to one of the modifiers in each set at the same time
EXCLUSIVE_MODIFIERS:"list[set[Modifiers]]" = [{Modifiers.hot, Modifiers.cold}]

# class Keybind:
#     all_keybinds:"dict[str, list]" = {}
#     active_keybinds:set = set()
#     def __init__(self, key:str, action:function, description:str = "", active:bool = True):
#         self.key:str = key
#         self.action:function = action
#         self.active:bool = active
#         if self.active:
            

#         if not description:
#             description = f"Keybind for [{key}]"
#         self.description:str = description
    


    # def __str__(self) -> str:
    #     return self.description
    # def __repr__(self) -> str:
    #     return str(self)
    # def __hash__(self) -> int:
    #     return hash(self.key)
