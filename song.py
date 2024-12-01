from winsound import PlaySound, SND_ASYNC
from math import ceil
from time import sleep as wait, time
from wave import open as open_wav
from typing import Union

from info import LYRIC_PLACEHOLDER_CHARACTER, Modifiers, Colors, SongAttributes, BASE_SONG_WEIGHT, STANDARD_SONG_LENGTH
from info import ATTRIBUTES_COLORING_ORDER, MODIFIERS_COLORING_ORDER
from info import TIMER_RESOLUTION
# time: a string representing a time in mm:ss.ss format
# converts and returns the time in seconds w/ decimals
def to_seconds(time:str) -> float:
    time:list[str] = time.split(":")
    return (int(time[0]) * 60) + float(time[1])

class Song:
    parent_player = None

    # File name includes the path to the file
    def __init__(self, song_name:str, file_name:str):
        self.file_name:str = file_name
        if file_name[len(file_name) - 4:] != ".wav": # Just in case
            self.file_name += ".wav"
        
        self.song_name:str = song_name

        with open_wav(file_name, "r") as file:
            self.duration = ceil(file.getnframes() / file.getframerate())
        self.curr_duration:int = 0
        self.start_time = None

        # KEYS IN attributes MUST MATCH KEYS IN enabled_colors IN spotify.list_actions
        self.attributes:dict[SongAttributes, Union(bool, set)] = {SongAttributes.playing : False, # This attribute is updated from the play function, not from Spotify
                                                        SongAttributes.disabled : False,
                                                        SongAttributes.queued : False,
                                                        SongAttributes.sequenced : False,
                                                        SongAttributes.modifiers : set()}
        self.attributes_changed:bool = True
        self.listing_colors:list[tuple[SongAttributes, list[Colors]]] = []
        self.sequence:list[str] = []

        # Each item in lyrics is a dictionary representing a line in the form of {"time" : start time of this line, "text" : the line's text}
        # lyrics will be None if no lyrics text file 
        self.lyrics:list["dict[str, Union(int, str)]"] = None # Each lyric line will not have a newline character at the end
        try:
            lines:list[str] = open(f"lyrics/{self.song_name}.txt", "r").readlines() # Will error if no lyrics file with the same name as the song is found

            for i in range(len(lines)):
                line:str = lines[i]

                line = line.replace("/u2669", LYRIC_PLACEHOLDER_CHARACTER) # Add in any quarter note symbols
                if i != len(lines) - 1: # The last line of each lyrics file won't have a new line after it
                    line = line[:len(line) - 1] # Remove the newline character at the end of the line

                if not self.lyrics:
                    self.lyrics = []

                self.lyrics.append({"time" : to_seconds(line[:line.index(" ")]), "text" : line[line.index(" ") + 1:]})
        except:
            self.lyrics = None # In case something is wrong with the lyrics' formatting and only some of the lyrics were added
            pass
        
        self.BASE_WEIGHT:int = BASE_SONG_WEIGHT + max(-BASE_SONG_WEIGHT//4, min(BASE_SONG_WEIGHT//4, (STANDARD_SONG_LENGTH - self.duration)//5)) # Slightly increase/decrease the weight of shorter/longer songs up to ±25% of the base song weight
        self.weight:int = self.BASE_WEIGHT

    def __str__(self) -> str:
        return self.song_name

    def get_listing_colors(self) -> "list[Colors]":
        if self.attributes_changed: # Return the colors that were last used for this song if none of the song's attributes have been changed since then
            self.listing_colors.clear()

            for attribute in ATTRIBUTES_COLORING_ORDER:
                if self.attributes[attribute] and attribute.value: # attribute.value == None  when attribute is Modifiers
                    self.listing_colors.append((attribute, [attribute.value]))
            
            modifier_colors:list[Colors] = []
            for modifier in MODIFIERS_COLORING_ORDER:
                if modifier in self.attributes[SongAttributes.modifiers]:
                    modifier_colors.append(modifier.value["color"])
            self.listing_colors.append((SongAttributes.modifiers, modifier_colors))

            self.attributes_changed = False

        return self.listing_colors

    def play(self):
        if not Song.parent_player:
            print("No parent player found!")
            wait(5)
            return
            
        self.attributes[SongAttributes.playing] = True
        self.attributes_changed = True

        PlaySound(self.file_name, SND_ASYNC)
        self.start_timer() # Blocks the song-playing thread until the song is finished or interrupted

        self.attributes[SongAttributes.playing] = False
        self.attributes_changed = True

    # Don't call this function from the main thread
    def start_timer(self) -> None:
        self.curr_duration = 0
        self.start_time = time()

        while self.curr_duration < self.duration: # Outer loop iterates roughly once per second
            if Song.parent_player.playing == True:
                while time() - self.start_time <= self.curr_duration: # curr_duration will be ahead of the actual duration by between 0-1 seconds
                    wait(TIMER_RESOLUTION)
                self.curr_duration += 1

            else: # If the player has been paused
                self.curr_duration -= 1
                break

    def set_enqueued(self) -> None:
        if self.attributes[SongAttributes.queued] == False:
            self.attributes[SongAttributes.queued] = True
            self.attributes_changed = True
    def set_dequeued(self) -> None:
        if self.attributes[SongAttributes.queued] == True:
            self.attributes[SongAttributes.queued] = False
            self.attributes_changed = True

    def disable(self) -> None:
        self.attributes[SongAttributes.disabled] = True
        self.recalculate_weight(synced_songs_count = None) # synced_songs_count won't be used if the song is disabled
        self.attributes_changed = True
    def enable(self) -> None:
        self.attributes[SongAttributes.disabled] = False
        self.recalculate_weight(synced_songs_count = Song.parent_player.get_synced_count(self.song_name))
        self.attributes_changed = True

    def update_sequence(self, sequence:"list[str]"):
        prev_sequence_attribute:bool = self.attributes[SongAttributes.sequenced]

        if sequence:
            self.attributes[SongAttributes.sequenced] = True
            self.sequence = sequence
        else:
            self.attributes[SongAttributes.sequenced] = False
            self.sequence.clear()

        if prev_sequence_attribute != self.attributes[SongAttributes.sequenced]:
            self.attributes_changed = True

    # Pass in nothing to modifiers to only update the weight based on synced_songs_count
    # Adding a modifier that has already been added won't do anything
    # synced_songs_count is always at least 1 because each song is technically always synced with itself
    def add_modifiers(self, synced_songs_count:int = 1, *modifiers:"tuple[Modifiers]") -> None:
        self.attributes[SongAttributes.modifiers] = self.attributes[SongAttributes.modifiers] | set(modifiers)
        self.recalculate_weight(synced_songs_count)

    def remove_modifiers(self, synced_songs_count:int = 1, *modifiers:"tuple[Modifiers]") -> None:
        self.attributes[SongAttributes.modifiers] = self.attributes[SongAttributes.modifiers] - set(modifiers)
        self.recalculate_weight(synced_songs_count)

    def clear_modifiers(self) -> None:
        self.attributes[SongAttributes.modifiers].clear()
        self.recalculate_weight(synced_songs_count = 1)

    # Only called from within this object
    def recalculate_weight(self, synced_songs_count:int) -> None:
        if self.attributes[SongAttributes.disabled]:
            self.weight = 0
        else:
            synced_songs_count = max(synced_songs_count, 1)

            self.weight = self.BASE_WEIGHT
            for modifier in self.attributes[SongAttributes.modifiers]:
                self.weight = modifier.value["weight update"](self.weight, synced_songs_count)
        
        self.attributes_changed = True