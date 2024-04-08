from enum import Enum
from time import sleep as wait, time
from os import listdir, get_terminal_size
from winsound import PlaySound, SND_ASYNC
from threading import Thread
from random import randint
from difflib import get_close_matches
from math import floor, ceil

from song import Song
from info import Modifiers, Colors, SEQUENCES, EXCLUSIVE_MODIFIERS

# Converts the number of seconds into a str in mm:ss format
def to_minutes_str(seconds:int) -> str:
    if type(seconds) == int:
        second_str = str(seconds - ((seconds // 60) * 60))
        if len(second_str) < 2:
            second_str = "0" + second_str
            
        return f"{seconds // 60}:{second_str}"
    else:
        return "--"

def clear_console() -> None:
    print("\033c", end = "")

# Defaults to blue
def color(string:str, color:Colors = Colors.blue) -> str:
    return f"{color.value}{string}\033[0m"
# Removes all color and reset tags from string and returns the processed string
def remove_tags(string:str) -> str:
    for tag in Colors._value2member_map_.keys(): # Iterate through the values of the enums in Colors
        string = string.replace(tag, "")

    return string

def hide_cursor() -> None:
    print("\033[?25l", end = "")
def show_cursor() -> None:
    print("\033[?25h", end = "")
# Moves the cursor to the beginning of a previous line
# Set lines to 0 to move cursor to the beginning of the current line
def cursor_up(lines:int = 1) -> None:
    print(f"\033[{lines + 1}F")
# Moves the cursor to the beginning of a subsequent line
def cursor_down(lines:int = 1) -> None:
    print(f"\033[{lines}B", end = "")

def block_until_input(message:str = "Press enter to continue") -> None:
    hide_cursor()
    input(color(message, Colors.faint))
    show_cursor()
def confirmation(message:str = "Are you sure?") -> bool:
    message += " (y/n): "

    user_input:str = input(message).strip() # Will become an empty string if the user only entered spaces
    if user_input == "" or user_input.lower().startswith("y"): # Returns True if user inputs nothing
        print()
        return True
    else:
        print("\nAction cancelled!")
        block_until_input()
        print()
        return False

# Returns [search] if search is an empty string
# Set index_search_list to something that's not a list to disable index search. If it's not specified, then it will automatically try to index search the search_list
# Relative order of items in search_list will be kept the same
def search_for_item(search:str, search_list:"list[str]", index_search_list:"list[str]" = []) -> "list[str]":
    if not search: # If search is an empty string
        return [search]

    try:
        # Errors if the search term is not a number or if index_search_list is None
        index = int(search) - 1
        if index_search_list == []:
            index_search_list = search_list
        
        if index < len(index_search_list):
            return [index_search_list[index]]
    except:
        pass

    search = search.strip().lower()

    search_pairs:list[tuple[str, str]] = [(item[:len(search)].lower(), item) for item in search_list if item not in exact_commands] # Tuples in the format of (name of item cut down to not exceed the length of the search term , original name of the item)
    results:list[str] = [name for short_name, name in search_pairs if short_name == search]
    if search in exact_commands:
        results.insert(0, search) # Put the exact result (if there is one) at the front of the list of results
    
    if len(results) > 0:
        return results

    # If the user made a typo in the search and no matches were found
    shortened_results:list[str] = get_close_matches(search, [short_name for short_name, *overflow_values in search_pairs]) # The higher the cutoff parameter (between 0 and 1), the stricter the search will be
    
    return [name for short_name, name in search_pairs if short_name in shortened_results]
# Removes repeat values from target in-place and returns the new, edited list
def remove_duplicates(target:list) -> list:
    d:dict[any, None] = {}
    for item in target:
        d[item] = None

    return list(d.keys())

# Remove any parenthesized tags in the song name and return the new song name
def get_pure_song_name(song_name:str) -> str:
    try:
        return song_name[:song_name.index("(") - 1] # Minus 1 to exclude the space in front of the parentheses
    except: # If there is no "(" character in the song name
        return song_name
# Converts items into a legible sentence with commas and connectors
# str_color: the color for each item listed in the sentence. Commas and connectors added by fix_grammar won't be colored
def fix_grammar(items:list, str_color:Colors = Colors.reset) -> str:
    if len(items) == 0:
        return "No items were recieved..."
    elif len(items) == 1:
        return color(str(items[0]), str_color)
    elif len(items) == 2:
        return f"{color(str(items[0]), str_color)} and {color(str(items[1]), str_color)}"
    else:
        sentence:str = ""
        for i in range(len(items) - 1):
            sentence += color(str(items[i]), str_color) + ", "

        return (sentence + f"and {color(str(items[len(items) - 1]), str_color)}")


class Modes(Enum):
    Repeat = 0
    Loop = 1
    Shuffle = 2
class ListModes(Enum):
    Songs = 0
    Song = 1
    Queue = 2
    Modifiers = 3


class spotify:
    # Constants
    COOLDOWN_BETWEEN_SONGS:int = 8 # Seconds
    # When the playback mode is shuffle, the minimum number of songs that would have to play between each repeat
    COOLDOWN_BETWEEN_REPEATS:int = 5 # Will be capped at len(playlist) - 1
    RATE_CHANGE:int = 3 # Percent increase/decrease of the chances for a hot/cold song to be chosen, in decimal form. Has to be a whole number
    
    SAVE_FILE_PATH:str = "save.file"

    def __init__(self, songs:dict, song_names:list): # Passes song_names in as an argument to keep the order of the names the same each time the code runs
        file_text:str = open(self.SAVE_FILE_PATH, "r").read()
        save_file:dict[str, any] = {}
        if file_text:
            save_file = eval(file_text)

        self.songs:dict[str, Song] = songs # Keys are the name of the song
        self.song_names:list[Song] = song_names
        self._max_song_name_length:int = 0
        for name, song in self.songs.items(): # Set the parent player of the song objects
            if len(name) > self._max_song_name_length:
                self._max_song_name_length = len(name)
            if song.song_name in SEQUENCES.keys():
                song.attributes["sequenced"] = True

            song.set_player(self)
        # For safe measure
        for command in valid_commands.keys():
            if len(command) > self._max_song_name_length + 15:
                self._max_song_name_length = len(command)

        self.curr_song:Song = None
        self.curr_song_index:int = 0
        self.mode:Modes = save_file.get("mode", Modes.Shuffle)

        self.sequence:list[Song] = [self.songs[song_name] for song_name in save_file.get("sequence", []) if song_name in self.song_names]
        # Play the saved curr_song first, if there is a one
        if save_file.get("curr_song", None) in self.song_names:
            self.sequence.insert(0, self.songs[save_file["curr_song"]])

        self.queue:list[Song] = [self.songs[song_name] for song_name in save_file.get("queue", []) if song_name in self.song_names]
        self.queue_song_names:list[str] = [song.song_name for song in self.queue]

        # Modifiers that are hard-coded to songs here will be added to the saved modifiers
        self.modifiers:dict[Modifiers, list[str]] = {Modifiers.hot : [], Modifiers.cold : [], Modifiers.disabled : []}
        for modifier in save_file.get("modifiers", []):
            if modifier in Modifiers:
                self.modifiers.setdefault(modifier, [])
                for modified_song_name in [self.songs[song].song_name for song in save_file["modifiers"][modifier]]:
                    if modified_song_name in self.song_names and modified_song_name not in self.modifiers[modifier]:
                        self.modifiers[modifier].append(modified_song_name)
        # Fills in any modifiers not covered by the hard-coded modified songs or the modifiers in the save file
        for modifier in Modifiers:
            if modifier not in self.modifiers.keys():
                self.modifiers[modifier] = []
            else:
                # Add this modifier to the songs that are initialized with the modifier
                [song.attributes["modifiers"].add(modifier) for song in [self.songs[song_name] for song_name in self.modifiers[modifier]]]

        self.synced_songs:dict[str, list[str]] = {}
        for song_name in self.modifiers[Modifiers.synced]:
            pure_song_name:str = get_pure_song_name(song_name)
            self.synced_songs.setdefault(pure_song_name, [])
            self.synced_songs[pure_song_name].append(song_name)

        self.remaining_cooldown_indicator:str = "" # Indicates how much time is left for the cooldown period between this song and the next one
        self.COOLDOWN_BETWEEN_REPEATS:int = min(len(self.song_names) - 1, self.COOLDOWN_BETWEEN_REPEATS)
        self.songs_on_cooldown:list[str] = []

        self.encore_activated:bool = False
        self.exit_later:bool = False

        self.playing:bool = True
        self.terminated:bool = False

        self.listing_info:dict[ListModes, dict[str, any]] = {
            ListModes.Songs : {
                "header line" : f"Select a song to queue (or a command to run)",
                "special commands" : {},
                "no results" : {"message" : "No songs found! Please check your spelling", "action" : self.list_songs},
                "disabled color keys" : [],
                "prompt" : f"Enter the index or the name of the song to queue ({color('q')}/{color('quit')} to cancel): "
            },
            ListModes.Queue : {
                "header line" : f"Select a command, or a song to remove from the queue",
                "special commands" : {"clear" : {"confirmation" : confirmation, "action" : self.clear_queue}},
                "no results" : {"message" : "No songs found! Please check your spelling", "action" : self.list_queue},
                "disabled color keys" : ["playing"],
                "prompt" : f"Enter the index or the name of the song to remove ({color('q')}/{color('quit')} to cancel, {color('clear')} to clear queue): "
            },
            ListModes.Modifiers : {
                "header line" : f"Select a modifier to remove it from all songs, or select a song to remove all modifiers from that song",
                "special commands" : {"clear" : {"confirmation" : confirmation, "action" : self.remove_modifier}},
                "no results" : {"message" : "No modifier found! Please check your spelling", "action" : self.list_active_modifiers},
                "disabled color keys" : ["playing", "queued", "sequenced"],
                "prompt" : f"Select a modifier to clear that modifier select a song to clear all of its modifiers ({color('clear')} to clear all modifiers): "
            },
            ListModes.Song : {
                "header line" : "Select a command to run or a modifier to add/remove for {song_name}",
                "special commands" : {"clear" : {"confirmation" : None, "action" : self.remove_modifier},
                                        "enqueue" : {"confirmation" : None, "action" : self.enqueue}},
                "no results" : {"message" : "No results found! Please check your spelling", "action" : self.list_song},
                "disabled color keys" : [],
                "prompt" : f"Select a modifier ({color('clear')} to clear all modifiers from this song, or {color('[space]')} to enqueue): "
            },
            None : {
                "header line" : f"Which one do you mean?",
                "special commands" : {},
                "no results" : {"message" : "No results found! Please check your spelling", "action" : self.update_ui},
                "disabled color keys" : [],
                "prompt" : f"Enter the index or the name of the result ({color('q')}/{color('quit')} to cancel): "
            }}

    # Call this after the thread that plays the songs has been started
    def start(self) -> None:
        if len(self.songs) > 0:
            show_cursor()
            self.update_ui()
        else:
            print("No valid audio files found!")
            block_until_input("Press enter to exit")
            exit()
    # Rewrites the save file
    def save(self) -> None:
        def trim_enum_str(enum):
            return str(enum).split(":")[0]

        curr_save:dict[str, any] = {"mode" : trim_enum_str(self.mode), 
                        "curr_song" : self.curr_song.song_name,
                        "queue" : self.queue_song_names, 
                        "sequence" : [song.song_name for song in self.sequence], 
                        "modifiers" : {trim_enum_str(modifier) : modifier_list for modifier, modifier_list in self.modifiers.items()}}
        curr_save_str:str = "{"
        for key, value in curr_save.items():
            curr_save_str += f"\'{key}\': "
            if key == "mode":
                curr_save_str += curr_save["mode"]
            elif key == "modifiers":
                curr_save_str += "{"
                for modifier, modifier_list in curr_save["modifiers"].items():
                    curr_save_str += modifier + ": " + str(modifier_list) + ", "
                curr_save_str = curr_save_str[:len(curr_save_str) - 2] + "}"
            elif key == "curr_song":
                curr_save_str += f"\'{value}\'"
            else:
                curr_save_str += str(value)
            
            curr_save_str += ", "
        curr_save_str = curr_save_str[:len(curr_save_str) - 2] + "}"

        prev_save:str = open(self.SAVE_FILE_PATH, "r").read()
        file = open(self.SAVE_FILE_PATH, "w")
        try:
            # The save file will be cleared no matter what before the new save file is written or causes an error
            file.write(str(curr_save_str))
        except:
            file.write(prev_save)
            print(color("Save attempt failed due to an unsupported character!", Colors.red))
            wait(3)
            clear_console()

        file.close()
    # Stops execution of the entire program
    def stop(self) -> None:
        clear_console()
        self.save()
        print("Program terminated via command!")
        self.terminated = True
        # exit()
    # Stops the program after the current song ends
    def delayed_exit(self) -> None:
        self.exit_later = not self.exit_later
        self.update_ui()

    def enqueue(self, song_name:str = None) -> None:
        if song_name:
            self.queue.append(self.songs[song_name])
            self.queue_song_names.append(song_name)
            self.songs[song_name].attributes["queued"] = True

            clear_console()
            print(f"{color(song_name, Colors.purple)} added to queue!")
            block_until_input()
        else: # Enqueue a placeholder song
            self.queue.append(None)
            self.queue_song_names.append("*")
            clear_console()

        self.update_ui()

    def clear_queue(self) -> None:
        self.queue.clear()
        self.queue_song_names.clear()
        print("Queue cleared!")

        block_until_input()
        self.update_ui()
    # If only song_name is provided, then remove all occurrences of that song from the queue
    # If song_name and remove_at_occurrence are provided, then remove that occurrence of the song from the queue
    # If only remove_at_index is provided, then only remove the song in the queue at that index
    def remove_queued_item(self, song_name:str = None, remove_at_occurrence:int = None, remove_at_index:int = None) -> None:
        removals:int = 0
        
        if remove_at_index != None:
            song_name = self.remove_queued_item_at_index(remove_at_index)
            removals += 1
        else:
            occurrences:"list[int]" = [index for index in range(len(self.queue_song_names) - 1, -1, -1) if self.queue_song_names[index] == song_name]
                    
            if remove_at_occurrence:
                remove_at_occurrence -= 1
                if remove_at_occurrence < len(occurrences):
                    occurrences.reverse()
                    song_name = self.remove_queued_item_at_index(occurrences[remove_at_occurrence])
                    removals += 1
                # Do nothing here if remove_at_occurrence is invalid
            else:
                for i in occurrences:
                    song_name = self.remove_queued_item_at_index(i)

                removals += len(occurrences)    
        if removals == 0:
            print()
            print(f"\"{color(song_name, Colors.bold)}\" wasn\'t found in the queue!")
        elif removals == 1:
            clear_console()
            print(f"Removed {color(song_name, Colors.purple)} from the queue")
        else:
            clear_console()
            print(f"Removed {color(removals, Colors.bolded_white)} occurrences of {color(song_name, Colors.purple)} from the queue")
        
        block_until_input()

        self.update_ui()
    # Used exclusively by remove_queued_item
    # Returns the name of the song that was removed
    def remove_queued_item_at_index(self, index:int) -> str:
        song_name:str = self.queue_song_names[index]
        try:
            self.queue[index].attributes["queued"] = False # Will error if the song at index is a placeholder ("*")
        finally:
            del self.queue[index]
            del self.queue_song_names[index]

            return song_name
    
    def list_queue(self, *overflow_args) -> None:
        if len(self.queue) > 0 or len(self.sequence) > 0:
            self.list_actions(["q", "quit", "clear"] + self.queue_song_names, list_type = ListModes.Queue) # Clears the console
        else:
            clear_console()
            print("There are no queued or sequenced songs...")
            block_until_input()

            self.update_ui()

    def list_active_modifiers(self, *overflow_args) -> None:
        active_modifier_names:list[str] = [modifier.name for modifier, modifier_list in self.modifiers.items() if len(modifier_list) > 0]
        # Add the songs with modifiers
        for modifier_list in self.modifiers.values():
            for song_name in modifier_list:
                if song_name not in active_modifier_names:
                    active_modifier_names.append(song_name)

        if len(active_modifier_names) > 0:
            self.list_actions(["q", "quit", "clear"] + active_modifier_names, list_type = ListModes.Modifiers)
        else:
            clear_console()
            print("There are no active modifiers...")
            block_until_input()

            self.update_ui()
    def add_modifier(self, song_name:str, modifier:Modifiers) -> bool: # Returns True if modifier was successfully added, False otherwise
        overlaps:set[Modifiers] = set()
        for exclusive_set in EXCLUSIVE_MODIFIERS:
            if modifier in exclusive_set:
                overlaps = overlaps | (self.songs[song_name].attributes["modifiers"] & exclusive_set)

        if len(overlaps) == 0:
            clear_console()
        else:
            modifier_strs:list[str] = []
            for overlap in overlaps:
                modifier_strs.append(color(overlap.name, overlap.value["color"]))
            
            message_argeement:str = "modifier conflicts"
            prompt_agreement:str = "this modifier"
            modifiers_sentence:str = fix_grammar(modifier_strs)
            if len(overlaps) > 1:
                message_argeement = "modifiers conflict"
                prompt_agreement = "these modifiers"

            print(f"The {modifiers_sentence} {message_argeement} with the adding modifier!")
            if confirmation(message = f"Would you like to remove {prompt_agreement} and add the {color(modifier.name, modifier.value['color'])} modifier?"):
                for overlap in overlaps:
                    self.remove_modifier(song_name = song_name, modifier = overlap, show_message = False)

                    clear_console()
                    print(f"Removed the {modifiers_sentence} modifier(s) and")
            else: # If the user cancels the action
                self.update_ui()
                return
        
        if modifier == Modifiers.synced:
            self.sync_songs(song_name)
            return

        self.modifiers[modifier].append(song_name)
        self.songs[song_name].attributes["modifiers"].add(modifier)

        print(f"Added the {color(modifier.name, modifier.value['color'])} modifier to {color(song_name, Colors.bold)}")
        block_until_input()
        self.update_ui()
    def sync_songs(self, song_name:str):
        clear_console()

        pure_name:str = get_pure_song_name(song_name)
        if pure_name not in self.synced_songs:
            syncing_songs:list[str] = []

            for song_name in self.song_names:
                if get_pure_song_name(song_name) == pure_name:
                    syncing_songs.append(song_name)

            if len(syncing_songs) > 1:
                self.synced_songs[pure_name] = syncing_songs
                for syncing_song_name in syncing_songs:
                    self.modifiers[Modifiers.synced].append(syncing_song_name)
                    self.songs[syncing_song_name].attributes["modifiers"].add(Modifiers.synced)

                print(f"{color('Synced', Modifiers.synced.value['color'])} {fix_grammar(syncing_songs, str_color = Colors.bold)}")
            else:
                print(f"No other versions of {color(pure_name, Colors.bold)} were found...")
        elif song_name not in self.synced_songs[pure_name]: # If this song was added to the songs folder after a set of synced songs with its name has already been created
            # Print the message before self.synced_songs[pure_name] is updated
            print(f"{color('Synced', Modifiers.synced.value['color'])} {color(song_name, Colors.bold)} with {fix_grammar(self.synced_songs[pure_name], str_color = Colors.bold)}")
            
            self.synced_songs[pure_name].append(song_name)
            self.songs[song_name].attributes["modifiers"].add(Modifiers.synced)

            # Put this song next to the other songs that are synced with it in self.modifiers[Modifiers.synced]
            for i in range(len(self.modifiers[Modifiers.synced]) - 1, -1, -1):
                if get_pure_song_name(self.modifiers[Modifiers.synced]) == pure_name:
                    self.modifiers[Modifiers.synced].insert(i + 1, song_name)
        else:
            print("This song is already synced!")

        block_until_input()
        self.update_ui()
    def remove_modifier(self, song_name:str = None, modifier:Modifiers = None, show_message:bool = True):
        removals:int = 0
        message:str = ""
        if not modifier:
            if song_name:
                active_modifiers:set[Modifiers] = self.songs[song_name].attributes["modifiers"]
            
                # Format and print the "modifier(s) cleared" message
                if len(active_modifiers) == 0:
                    message = f"{color(song_name, Colors.bold)} doesn't have any modifiers..."
                else:
                    modifier_names:list[str] = [color(modifier.name, modifier.value["color"]) for modifier in active_modifiers]
                    separator:str = " "
                    noun:str = "modifier"
                    if len(modifier_names) >= 2:
                        modifier_names[len(modifier_names) - 1] = "and " + modifier_names[len(modifier_names) - 1]
                        noun += "s"
                    if len(modifier_names) >= 3:
                        separator = ", "

                # Remove modifiers from the set of modifiers after figuring out the sentence to use for the amount fo modifiers
                for active_modifier in active_modifiers.copy():
                    if active_modifier == Modifiers.synced:
                        self.desync_songs(song_name)
                    else:
                        self.modifiers[active_modifier].remove(song_name)

                    message = f"Removed the {separator.join(modifier_names)} {noun} from {color(song_name, Colors.bold)}"

                active_modifiers.clear() # active_modifiers has the same reference to the list of modifiers in the song

            else: # If no song name or modifier is specified
                for modifier_list in self.modifiers.values():
                    removals += len(modifier_list)
                    modifier_list.clear()
                self.synced_songs.clear()
                
                for song in self.songs.values():
                    song.attributes["modifiers"].clear()

                message = f"Cleared {color(removals, Colors.bold)} modifier(s) from all songs"
        else: # If a modifier is specified
            if song_name:
                if modifier == Modifiers.synced:
                    self.desync_songs(song_name) # Will print a message with the songs that were desynced
                else:
                    try:
                        self.modifiers[modifier].remove(song_name)
                        self.songs[song_name].attributes["modifiers"].remove(modifier)
                        message = f"Removed the {color(modifier.name, modifier.value['color'])} modifier from {color(song_name, Colors.bold)}"
                    except:
                        message = f"{color(song_name, Colors.bold)} doesn't have the {color(modifier.name, modifier.value['color'])} modifier..."
            else: # If no song name is specified
                message = f"Cleared {color(len(self.modifiers[modifier]), Colors.bold)} {color(modifier.name, modifier.value['color'])} modifier(s) from all songs"
                
                if modifier == Modifiers.synced:
                    for pure_name in list(self.synced_songs.keys()): # Make a copy of the names of the synced songs so it doesn't error when desync_songs deletes items from synced_songs
                        self.desync_songs(pure_name)
                else:
                    for song_name in self.modifiers[modifier]:
                        self.songs[song_name].attributes["modifiers"].remove(modifier)

                    self.modifiers[modifier].clear() # List of synced songs in self.modifiers will be cleared by desync_songs if the modifier is Modifiers.synced

        if show_message:
            print(message)
            block_until_input()
            self.update_ui()
    def desync_songs(self, song_name:str):
        pure_name:str = get_pure_song_name(song_name)
        if pure_name in self.synced_songs:
            for song_name in self.synced_songs[pure_name]:
                self.songs[song_name].attributes["modifiers"].remove(Modifiers.synced)
                self.modifiers[Modifiers.synced].remove(song_name)

            print(f"{color('Desynced', Modifiers.synced.value['color'])} {fix_grammar(self.synced_songs[pure_name], str_color = Colors.bold)}")
            
            del self.synced_songs[pure_name]
        else:
            print("Something went wrong when desyncing songs!")
            pass

    # Only call these playback functions from the play_next_song function
    # The playback mode functions will only run if the queue is empty
    # These functions will not add songs to the queue and will only set self.curr_song to the next song without playing it
    def repeat(self) -> None:
        if not self.curr_song: # If no other songs have been played
            self.curr_song_index = randint(0, len(self.song_names) - 1)
            self.curr_song = self.songs[self.song_names[self.curr_song_index]]
    def loop(self) -> None:
        index_changed:bool = False
        song_name:str = ""

        while (not index_changed) or (song_name in self.modifiers[Modifiers.disabled]):
            if self.curr_song_index < len(self.song_names) - 1:
                self.curr_song_index += 1
            else:
                self.curr_song_index = 0

            index_changed = True
            song_name = self.song_names[self.curr_song_index]
            
        self.curr_song = self.songs[song_name]
    def shuffle(self) -> None:
        disabled_set:set[str] = set(self.modifiers[Modifiers.disabled])

        available_songs:set[str] = set(self.song_names) - disabled_set - set(self.modifiers[Modifiers.synced])
        if len(available_songs) - len(self.songs_on_cooldown) > 0: # Just in case there are too many songs on cooldown (should be prevented by the cap on cooldown songs set in the constructor)
            available_songs -= set(self.songs_on_cooldown)
        available_songs:list[str] = list(available_songs) + list(self.synced_songs.keys())

        if len(available_songs) > 1: # If there's more than 1 available song
            available_songs += self.modifiers[Modifiers.hot] * self.RATE_CHANGE
            song_name:str = None
            while not song_name:
                # The synced songs in available_songs have been replaced by the keys in self.synced_songs
                song_name:str = available_songs[randint(0, len(available_songs) - 1)]

                if song_name in self.synced_songs.keys():
                    valid_variations:list[str] = list(set(self.synced_songs[song_name]) - disabled_set)
                    if len(valid_variations) > 0: # If this list of synced songs is not empty
                        song_name = valid_variations[randint(0, len(valid_variations) - 1)]
                    else:
                        continue

                if (song_name in self.modifiers[Modifiers.cold]) and randint(1, self.RATE_CHANGE) != 1:
                    song_name = None

            self.curr_song_index = self.song_names.index(song_name) # Adjust for changes in song indexes when the cooldown songs got removed
        else:
            self.curr_song_index = self.song_names.index(available_songs[0])
        
        self.curr_song = self.songs[self.song_names[self.curr_song_index]]

    def pause(self) -> None:
        if self.playing:
            self.playing = False
            PlaySound("1s_silence", SND_ASYNC)

        self.update_ui()
    # Resuming the player will restart the song that was playing before the pause
    def resume(self) -> None:
        if not self.playing:
            self.encore_activated = True # Use the encore feature to restart the song that was paused
            self.playing = True # Will resume the loop in the song-playing thread
            wait(0.75) # Wait for the song-playing thread to set the next song

        self.update_ui()
    def skip(self) -> None:
        self.playing = False
        PlaySound("1s_silence.wav", SND_ASYNC)

        print("Picking the next song...")
        wait(1.5) # Wait for the current song's timer to stop
        self.playing = True # Resume the song-playing thread

        wait(0.75) # Wait for the song-playing thread to set the next song (Must be longer than the waiting time for each loop in play())
        self.update_ui()

    # Repeat the current song an additional time
    # the repeat will not trigger any sequences
    def encore(self) -> None:
        self.encore_activated = not self.encore_activated

        self.update_ui()
        return

    # Only call this function from a separate thread (if playing a song)
    # Adds a song to the queue if requested_song_name is provided
    def play_next_song(self, interlude:bool = True) -> None:
        if self.encore_activated:
            self.encore_activated = False
            # Do nothing to curr_song and curr_song_index so the same song repeats
        else: # Don't update the sequence if the song is an encore
            if len(self.sequence) > 0: # Songs in the active sequence take priority over songs in the queue
                song:Song = self.sequence[0]
                del self.sequence[0]
                self.curr_song = song
                self.curr_song_index = self.song_names.index(song.song_name)
            
            elif len(self.queue) > 0:
                song:Song = self.queue[0]
                del self.queue[0]
                del self.queue_song_names[0]
                if song:
                    if song.song_name not in self.queue_song_names: # In case this song was enqueued multiple times
                        song.attributes["queued"] = False

                    self.curr_song = song
                    self.curr_song_index = self.song_names.index(song.song_name)
                else: # If the queued song is a placeholder
                    mode_actions[self.mode](self)
            else:
                mode_actions[self.mode](self) # Select the next song based on the current playback mode

            # Only activate the sequence if there is not already an active sequence
            if (self.curr_song.song_name in SEQUENCES.keys()) and len(self.sequence) == 0:
                self.sequence = [self.songs[song_name]  for song_name in SEQUENCES[self.curr_song.song_name] if song_name in self.song_names]
        
        self.save()
        if self.exit_later:
            self.stop()
            return

        # Updates the songs on cooldown
        if len(self.songs_on_cooldown) >= self.COOLDOWN_BETWEEN_REPEATS:
            del self.songs_on_cooldown[0]
        # self.curr_song will have already been set to the next song at this point
        if Modifiers.hot not in self.curr_song.attributes["modifiers"]:
            self.songs_on_cooldown.append(self.curr_song.song_name)
        
        if interlude: # Will be set to false when playing the first song so that everything saves BEFORE waiting and then playing each subsequent song
            buffer:float = 0.5 # If the song was paused, wait a little for pause() to set self.playing to false before checking self.playing
            wait(buffer)
            if self.playing: # If this song has ended naturally and not because the user paused the player
                self.remaining_cooldown_indicator = "-" * self.COOLDOWN_BETWEEN_SONGS
                
                padding:float = ceil(buffer) - buffer
                wait(padding)
                self.remaining_cooldown_indicator = self.remaining_cooldown_indicator[:len(self.remaining_cooldown_indicator) - 1]
                for seconds_remaining in range(self.COOLDOWN_BETWEEN_SONGS - 1, -1, -1):
                    wait(1)
                    self.remaining_cooldown_indicator = "-" * seconds_remaining


        self.curr_song.play() # Plays the song in the same thread as this method

    def display_help(self) -> None:
        print("Available commands (in blue)")
        print(f"{color('---------------------------------------------------------------------------------', Colors.faint)}")
        # High-priority warnings
        print(color(f"""Some commands might be disabled in certain screens/lists. See each screen's list of actions for the available commands
Commands listed in [brackets] must be spelled exactly""", Colors.red))
        # Low-priority warnings
        print(color(f"""Songs in the active sequence always take priority over songs in the queue when playing
Songs played as part of a sequence can't initiate sequences themselves""", Colors.orange))
        # Tips
        print(color(f"""Inputs are not case sensitive
Enter the index of a queued song from the menu to remove that song from the queue
Press enter without typing anything to return to the menu from any screen
The currently playing song, queue, sequence, playback mode, and active modifiers will be autosaved
Home screen indicators for some toggle-able commands will be listed in (parentheses) after the command""", Colors.green))

        print()
        # Commands
        print(f"""{color('list')}: list all of the songs in the playlist and optionally select one to queue
{color('queue')}: list the queue and the active sequence (if any), and optionally remove a song from the queue
    {color('*')}: enqueue a placeholder song based on the playback mode    [{color('Warning: will not be saved between sessions', Colors.red)}]
{color('modifiers')}: list the active modifiers and optionally remove one or all modifiers from all songs
{color('q')} or {color('quit')}: return to {color('and update', Colors.bold)} the menu
Playback modes:
    {color('repeat')}: repeat the current song indefinitely
    {color('loop')}: loop through the playlist from the current song
    {color('shuffle')}: randomly select a song from the playlist
{color('karaoke')}(🎤): turn on lyrics for this song    [{color('Warning: karaoke mode can’t be turned off until the song ends', Colors.red)}]
{color('encore')}(🔁): repeat the current song one more time
{color('pause')}: pause the music player
{color('resume')}: resume the music player and restart the current song
{color('skip')} or [{color('>>')}]: stop the current song and play the next song
{color('<song name>')}: list the available actions and modifiers for this song
[{color('exit')}] or [{color('stop')}]: terminate the program
{color('exit later')}(⌛): terminate the program after the current song ends    [{color('Tip: enter this command again to cancel it', Colors.green)}]""")

        print()
        self.input_command(input("Enter a command: "))

    def list_songs(self, *overflow_args) -> None: # Requesting a song while another song is playing will queue the requested song instead
        self.list_actions(["q", "quit"] + self.song_names, list_type = ListModes.Songs)

    # Lists the commands and modifier actions for a song
    def list_song(self, song_name:str, *overflow_args) -> None:
        results:list[str] = ["q", "quit", "enqueue", "clear"]
        results += [modifier.name for modifier in list(self.modifiers.keys())]

        self.list_actions(results, list_type = ListModes.Song, listing_item_name = song_name)

    def karaoke(self) -> None:
        delay:float = -0.45 # Number of seconds to delay the lyrics by to compensate for lag
        max_display_range:int = 5 # Max number of lines before/after the current line of lyrics to display
        lyrics:list[dict[str, any]] = self.curr_song.lyrics # Each line's text includes a newline character at the end

        if not lyrics:
            print("Lyrics aren't available for this song...")
            block_until_input()
            self.update_ui()
        else:
            for i in range(len(lyrics)):
                if i == len(lyrics) - 1 or lyrics[i + 1]["time"] > time() - self.curr_song.start_time:
                    clear_console()
                    hide_cursor()

                    display_range:int = min((get_terminal_size().lines - 1) // 2, max_display_range) # How many lines before/after the current line of lyrics to display
                    display_width:int = get_terminal_size().columns
                    for prev_line_index in range(i - display_range, i):
                        if prev_line_index >= 0:
                            print(color(f'{lyrics[prev_line_index]["text"] : <{display_width}}', Colors.faint), end = "")
                        else:
                            print()

                    curr_line:str = lyrics[i]["text"]
                    print(f'{curr_line : <{display_width}}', end = "")

                    if i < len(lyrics) - 1:
                        for next_line_index in range(i + 1, i + display_range + 1):
                            if next_line_index < len(lyrics):
                                print(color(f'{lyrics[next_line_index]["text"] : <{display_width}}', Colors.faint), end = "")
                            else:
                                print()

                        notes_count:int = curr_line.count("\u2669")
                        segment_time:float = (lyrics[i + 1]["time"] - lyrics[i]["time"]) / (notes_count + 1) # The time between this lyric and the next one is divided into equal segments, with one note lighting up in between each segment
                        notes_shown:int = 0
                        if notes_count:
                            cursor_up(lines = display_range + 1) # Move the cursor to the beginning of the currently playing lyric line

                        # Wait until the time of the next line has been reached
                        # Keeps the offset between the lyrics and the song due to lag to within 0.1s
                        while True:
                            time_elapsed:float = round((time() - self.curr_song.start_time), 2) + delay

                            if notes_shown < notes_count and time_elapsed >= lyrics[i]["time"] + ((notes_shown + 1) * segment_time):
                                notes_shown += 1
                                print(color('\u2669 ' * notes_shown, Colors.bold), end = "")
                                print("\033[F") # Move the cursor to the beginning of the current line

                            elif time_elapsed >= lyrics[i + 1]["time"]:
                                break

                            wait(0.1)
                    else: # If there are no more lyrics
                        wait(self.curr_song.duration - (time() - self.curr_song.start_time))
                        self.update_ui()
    
    def update_ui(self, command:str = "") -> None:
        clear_console() # Clear the console
        self.save()

        if not command: # If the command is an empty string
            indicator_conditions:dict[str, bool] = {"🎤" : bool(self.curr_song.lyrics),
                                                    "🔁" : self.encore_activated,
                                                    "⌛" : self.exit_later}
            indicators:list[str] = []
            for indicator, condition in indicator_conditions.items():
                if condition == True:
                    indicators.append(indicator)

            # Both conditionals will set indicators to a string
            if len(indicators):
                indicators:str = "| " + " ".join(indicators)
            else:
                indicators = ""

            # If the cooldown is active, allot 75% of the terminal width to the cooldown indicator, clamped between 70 and the maximum possible length of the indicator
            currently_playing_line:str = f"{self.remaining_cooldown_indicator : ^{min(max(floor(get_terminal_size().columns * 0.75), self.COOLDOWN_BETWEEN_SONGS), 70)}}"
            if not self.remaining_cooldown_indicator: # If there is no active cooldown between songs
                currently_playing_line = f"Currently playing: {color(f'{self.curr_song.song_name : <{self._max_song_name_length}}', Colors.green)}   {color(f'{to_minutes_str(self.curr_song.curr_duration)}/{to_minutes_str(self.curr_song.duration)}', Colors.cyan) : <11} {indicators}"
            print(f"{currently_playing_line} | Playback mode: {color(f'{self.mode.name : <10}', Colors.orange)}")
            
            if not self.playing:
                print("--Player paused--")
            print()
            # List the queue if it's not empty
            if len(self.queue) > 0:
                print("Queued songs: ")
                max_index_len:int = len(str(len(self.queue) - 1))
                for i in range(len(self.queue)):
                    print(f"{f'{i + 1}. ' : <{max_index_len + 2}}{color(self.queue_song_names[i], Colors.purple)}")

                print()

            command = input(f"Input command (Enter {color('help')} for help, {color('[space]')} to pause/resume, or enter nothing to refresh): ")
            if self.terminated:
                exit()

            if command.isspace():
                if self.playing:
                    valid_commands["pause"](self)
                else:
                    valid_commands["resume"](self)
                
        # Try index searching the queue with the command first
        try:
            index:int = int(command) - 1
            if index >= 0 and index < len(self.queue):
                self.remove_queued_item(remove_at_index = index)
            else: # If the command is a number, but isn't a valid index
                self.input_command(command, index_search_enabled = False)
        except: # If the command can't be cast to a number
            self.input_command(command, index_search_enabled = False)

        return

    # Takes in the user's input and tries to find a corresponding command with list_actions()
    # Won't directly print anything
    def input_command(self, command:str, index_search_enabled:bool = True) -> None:
        if command == "" or command == "q" or command == "quit":
            valid_commands["quit"](self)
        else:
            index_search_list:"list[str]" = None
            if index_search_enabled:
                index_search_list = []

            self.list_actions(search_for_item(command, list(valid_commands.keys()) + self.song_names + ["*"], index_search_list = index_search_list))

        return

    # Returns a string that explains what each song color means in a colored list of songs
    # print_list is the list that the key is for
    # Key will only include the colors that will appear in print_list
    # Commands will always be colored blue
    def get_color_key(self, print_list:"list[str]", enabled_colors:"dict[str, bool]" = {"playing" : {"enabled" : True, "color" : Colors.green}, "queued" : {"enabled" : True, "color" : Colors.purple}, "sequenced" : {"enabled" : True, "color" : Colors.yellow}, "modifiers" : {"enabled" : True, "color" : None}}) -> str:
        print_list:set[str] = set(print_list)
        # List and sets can't be keys in a dictionary
        info:list[dict[str, any]] = [{"enabled" : enabled_colors["playing"]["enabled"], "nameset" : {self.curr_song.song_name}, "color" : enabled_colors["playing"]["color"], "message" : "Currently playing"},
                                    {"enabled" : enabled_colors["queued"]["enabled"], "nameset" : set(self.queue_song_names), "color" : enabled_colors["queued"]["color"], "message" : "Queued"},
                                    {"enabled" : enabled_colors["sequenced"]["enabled"], "nameset" : set(SEQUENCES.keys()), "color" : enabled_colors["sequenced"]["color"], "message" : "Has sequence"}]
        key:str = ""

        for item in info:
            if item["enabled"] and len(item["nameset"] & print_list) > 0:
                if key: # If there is already something in the key
                    key += " | "
                key += f"{color(item['message'], item['color'])}"

        if enabled_colors["modifiers"]["enabled"]:
            for modifier, modifier_list in self.modifiers.items():
                if len(set(modifier_list) & print_list) > 0: # If a song with the modifier is in print_list
                    if key: # If there is already something in the key
                        key += " | "
                    key += f"{color(modifier.name, modifier.value['color'])}"

        if len(key) > 0:
            key = "Key: " + key

        return key
      
    # results must be in the order of [commands, modifiers, songs]
    def list_actions(self, results:"list[str]", list_type:ListModes = None, listing_item_name:str = None) -> None:
        clear_console()
        # KEYS IN enabled_colors MUST MATCH EXISTING KEYS IN EACH SONG'S ATTRIBUTES
        enabled_colors:dict[str, bool] = {"playing" : {"enabled" : True, "color" : Colors.green},
                                        "queued" : {"enabled" : True, "color" : Colors.purple},
                                        "sequenced" : {"enabled" : True, "color" : Colors.yellow},
                                        "modifiers" : {"enabled" : True, "color" : None}}
        special_commands:dict[str, dict[str, function]] = self.listing_info[list_type]["special commands"] # Each key is the name of the command, and the value is a dict where "confirmation" is the function that asks the user to confirm (None if no confirmation needed) that returns True/False, and "action" is the function to run if the user confirms

        list_separators_enabled:bool = False # Whether to show the separators between commands, modifiers, and songs when listing the results. Will interfere with the list of the current sequence

        # Handle cases where there are no valid results or only 1 valid result
        if len(results) == 0:
            print(self.listing_info[list_type]["no results"]["message"])
            block_until_input()
            self.listing_info[list_type]["no results"]["action"](listing_item_name)
            return

        elif len(results) == 1:
            result:str = results[0]

            if result == "*":
                self.enqueue()
                
            elif result in valid_commands.keys():
                valid_commands[result](self)
                return

            elif result in special_commands.keys():
                # The functions in special_commands either have no parameters or a parameter called "song_name"
                # listing_item_name will be None if list_type is Modifiers, so the remove_modifiers method would still clear all modifiers
                if (not special_commands[result]["confirmation"]) or special_commands[result]["confirmation"](): # If there isn't a confirmation step or if the user confirms
                    try:
                        special_commands[result]["action"](song_name = listing_item_name)
                    except:
                        special_commands[result]["action"]()
                else: # If the user doesn't confirm
                    listmode_actions[list_type](self)

                return

            elif result in [modifier.name for modifier in Modifiers]: # Result is name of modifier
                if list_type == ListModes.Modifiers:
                    self.remove_modifier(modifier = Modifiers[result])
                elif list_type == ListModes.Song:
                    if len({Modifiers[result]} & self.songs[listing_item_name].attributes["modifiers"]) == 0:
                        self.add_modifier(listing_item_name, Modifiers[result])
                    else:
                        self.remove_modifier(song_name = listing_item_name, modifier = Modifiers[result])

            elif result in self.song_names:
                if list_type == ListModes.Queue:
                    self.remove_queued_item(song_name = result)
                # Song names won't be included in the results when listing options for a song
                elif list_type == ListModes.Modifiers:
                    self.remove_modifier(song_name = result)
                else: # If list_type is Songs or none
                    self.list_song(result)
                
            else:
                clear_console()
                print(f"{color('Invalid result!', Colors.red)}")
                block_until_input()
                self.update_ui()

            return
        
        # If more than 1 result
        for disabled_key in self.listing_info[list_type]["disabled color keys"]:
            enabled_colors[disabled_key]["enabled"] = False

        color_key = self.get_color_key(results, enabled_colors = enabled_colors)

        header_line:str = self.listing_info[list_type]["header line"]
        # Print the header line and the color key (if applicable to list_type)
        if list_type == ListModes.Queue:
            if len(set(results)) == 1: # If all the results are the same
                self.remove_queued_item(song_name = results[0])
                return
            # The selection prompt and color key for when list_type is Queue will be printed after determining the left margin
        else: # Includes when list_type is Songs
            if list_type == ListModes.Modifiers:
                list_separators_enabled = True
            elif list_type == ListModes.Song:
                header_line = header_line.format(song_name = color(listing_item_name, Colors.bold))

            print(header_line)
            if len(color_key) > 0:
                print(color_key)
    
        max_digits:int = len(str(len(results)))

        # List all the results
        # These 5 variables are only used when the list type is ListModes.Queue
        max_sequence_digits:int = len(str(len(self.sequence)))
        overflow_chars = "---" # Used when more than 1 color applies to the same song. Also used to adjust the left margin
        padding:str = " " * 3
        separator:str = color(f"{padding}|{padding}", Colors.faint)
        left_margin:int = max(len(header_line), (max_digits + 2) + 1 + self._max_song_name_length + len(overflow_chars) * 2 + 1 + 5) # 5 extra spaces for the duration display of each song
        if list_type == ListModes.Queue: # Formats and prints the header lines and the color key
            print(f"{header_line : <{left_margin}}{separator}", end = "")
            if len(self.sequence) > 0:
                print(f"Active sequence (not selectable)")
            else:
                print("No active sequence")

            color_key:str = self.get_color_key(results, enabled_colors = enabled_colors)
            if len(color_key) > 0:
                print(f"{color_key : <{left_margin + (len(color_key) - len(remove_tags(color_key)))}}", end = "")
                
                if len(self.sequence) > 0:
                    print(separator)
                else:
                    print()

        count:int = 1
        def get_sequence_line():
            seq_song:Song = self.sequence[count - 1]
            return (separator + color(f"{str(count) + '. ' : <{max_sequence_digits + 2}}", Colors.faint) + color(seq_song.song_name, Colors.yellow) + f" {color('-' * (self._max_song_name_length - len(seq_song.song_name) + 1), Colors.faint)} {color(to_minutes_str(seq_song.duration), Colors.cyan)}")

        commands_finished:bool = False # Whether all the commands in results have been listed
        modifiers_finished:bool = False
        commands_count:int = 0 # Used for determining the index of the removing song in self.queue_song_names when list_mode is Queue and the user input is a valid index
        for result in results:
            line:str = ""
            if commands_finished == False and (result in valid_commands.keys() or result in special_commands.keys()): # The command results will always be first in the list
                if list_separators_enabled and commands_count == 0:
                    print(f"{color('Commands:', Colors.faint)}")

                line = f"{str(count) + '.' : <{max_digits + 1}} {color(result)}"
                commands_count += 1
            
            elif modifiers_finished == False:
                try:
                    modifier:Modifiers = Modifiers[result] # Will error if the result isn't the name of a modifier
                    if list_separators_enabled and not commands_finished:
                        print(f"{color('Modifiers:', Colors.faint)}")

                    if list_type == ListModes.Modifiers:
                        line = f"{str(count) + '.' : <{max_digits + 1}} {color(result, modifier.value['color'])}{color('  - ' + modifier.value['description'], Colors.faint)}"
                    elif list_type == ListModes.Song:
                        action_type:str = ""
                        if len({modifier} & self.songs[listing_item_name].attributes["modifiers"]) == 1:
                            action_type = "(remove)"
                        else:
                            action_type = "(add)"

                        line = f"{str(count) + '.' : <{max_digits + 1}} {color(result, Modifiers[result].value['color'])} {color(action_type, Colors.faint)}"
                    else:
                        raise NotImplementedError # Manually create an error

                    commands_count += 1
                except:
                    modifiers_finished = True # Move on to listing songs without incrementing the commands count
                    if list_separators_enabled and count < len(results): # If there are songs in results
                        print(f"{color('Songs:', Colors.faint)}")
                
                commands_finished = True

            if commands_finished and modifiers_finished: # If this result isn't a command or modifier, then assume all subsequent results are songs
                if result == "*": # Can only show up in results if list_actions was used (when listing the queue or when there's no listing mode)
                    line = f"{str(count) + '.' : <{max_digits + 1}} {result}"

                else:
                    result_song:Song = self.songs[result]
                    # THIS IS THE PINNACLE OF UI DESIGN
                    name:str = result
                    applied_colors:list[str] = []
                    overflow_dashes = ""
                    # Color the currently playing song green (if listed), color any other queued songs purple, and color songs with sequences light yellow
                    for key, value in result_song.attributes.items():
                        if enabled_colors[key]["enabled"] and enabled_colors[key]["color"] and value:
                            applied_colors.append(enabled_colors[key]["color"])

                    if enabled_colors["modifiers"]["enabled"]:
                        for modifier in result_song.attributes["modifiers"]:
                            if modifier == Modifiers.disabled: # The disabled modifier is always shown first
                                applied_colors.insert(0, modifier.value['color'])
                            else:
                                applied_colors.append(modifier.value['color'])

                    if len(applied_colors) > 0:
                        name = color(name, applied_colors[0])
                        del applied_colors[0]
                    for curr_color in applied_colors:
                        overflow_dashes += color(overflow_chars, curr_color)

                    # I can't explain how this line works even if I tried
                    line = f"{str(count) + '.' : <{max_digits + 1}} {name} {overflow_dashes}{color('-' * (self._max_song_name_length - len(result) - len(applied_colors)*len(overflow_chars) + (len(Modifiers) + len(enabled_colors))*len(overflow_chars)), Colors.faint)} {color(to_minutes_str(self.songs[result].duration), Colors.cyan)}"
                
            if line: # Don't do anything if line is an empty string
                print(f"{line : <{left_margin + (len(line) - len(remove_tags(line)))}}", end = "")
                if list_type == ListModes.Queue and count <= len(self.sequence):
                    # "Attach" the line in the sequence's list onto a line in the list of commands
                    print(get_sequence_line(), end = "")
                elif list_type == ListModes.Modifiers and commands_finished == True and modifiers_finished == False: # If the listing mode is Modifiers and this result is a modifier, list the songs with each modifier in an indented, unnumbered, unselectable list after the modifier
                    for modified_song_name in self.modifiers[Modifiers[result]]:
                        print(f"\n{' ' * (max_digits + 4)}{modified_song_name}", end = "")

                print()
                
                count += 1
        
        # Print any more songs in the sequence that didn't get attached to the end of a "queued song" line
        if list_type == ListModes.Queue:
            while count <= len(self.sequence):
                print(f"{'' : <{left_margin}}{get_sequence_line()}")
                count += 1

        print()

        # After printing all the results
        user_input:str = input(self.listing_info[list_type]["prompt"])
        if user_input == "" or user_input == "q" or user_input == "quit":
            valid_commands["quit"](self)
            return

        elif user_input.isspace() and list_type == ListModes.Song:
                self.enqueue(song_name = listing_item_name)
                return

        elif list_type == ListModes.Queue: # Checks if the user wants to remove a queued item at a specific index
            result:list[str] = search_for_item(user_input, search_list = [], index_search_list = results)
            if len(result) == 1: # Can only be possible if the index search was successful
                index_search_result:str = result[0]
                if index_search_result in special_commands:
                    clear_console()
                    if special_commands[index_search_result]["confirmation"]:
                        special_commands[index_search_result]["confirmation"]()

                    special_commands[index_search_result]["action"]()
                elif index_search_result in valid_commands:
                    valid_commands[index_search_result](self) # Idk why self needs to be passed in here
                else: # If the result is a song
                    index:int = int(user_input) - 1
                    prev_occurrences:int = 0
                    for original_result in results[:index]:
                        if original_result == index_search_result:
                            prev_occurrences += 1

                    self.remove_queued_item(song_name = index_search_result, remove_at_occurrence = prev_occurrences + 1)

                return

        self.list_actions(search_for_item(user_input, results), list_type = list_type, listing_item_name = listing_item_name)

    global mode_actions
    mode_actions = {Modes.Repeat : repeat, Modes.Loop : loop, Modes.Shuffle : shuffle}
    global listmode_actions
    listmode_actions = {ListModes.Songs : list_songs, ListModes.Queue : list_queue, ListModes.Modifiers : list_active_modifiers}

    # Used in the dictionary of valid commands to set the mode and then calls update_ui
    def set_mode_repeat(self):
        self.mode = Modes.Repeat
        self.update_ui()
    def set_mode_loop(self):
        self.mode = Modes.Loop
        self.update_ui()
    def set_mode_shuffle(self):
        self.mode = Modes.Shuffle
        self.update_ui()

    # All functions in this dictionary must be able to be called with only the "self" argument
    global valid_commands
    valid_commands = {"help" : display_help,
                        "pause" : pause,
                        "resume" : resume,
                        "skip" : skip,
                        ">>" : skip,
                        "karaoke": karaoke,
                        "list" : list_songs,
                        "encore" : encore,
                        "queue" : list_queue,
                        "modifiers" : list_active_modifiers,
                        "q" : update_ui,
                        "quit" : update_ui,
                        "repeat" : set_mode_repeat,
                        "loop" : set_mode_loop,
                        "shuffle" : set_mode_shuffle,
                        "stop" : stop,
                        "exit" : stop,
                        "exit later" : delayed_exit
                        }

    global exact_commands
    exact_commands = {"stop", "exit", "exit later", ">>"} # Can only contain commands in valid_commands


clear_console() # Clears any "hide cursor" characters in the console
hide_cursor()

intro_enabled:bool = False # Enable or disable the intro bit
if intro_enabled:
    # Intro bit
    wait(0.9)
    print("\"Mom can we have Spotify?\"")
    wait(1)
    print("Mom: we have Spotify at home")
    wait(2)

    # Will all be cleared once spotify initializes and the console clears when the first song plays
    clear_console()
    wait(0.3)
    print(f"spotify at home {color('<company name> <address> ©2023 All Rights Reserved', Colors.faint)}")
    wait(1.9)

DIRECTORY:str = "songs/" # Every file in this directory must be a playable wav file
songs:"dict[str, Song]" = {}
song_names:"list[str]" = []
alert:bool = False
file_names:"list[str]" = listdir(DIRECTORY)
songs_instructions_file_name:str = "read_this.txt" # This text file must be in the "songs" directory
try:
    file_names.remove(songs_instructions_file_name)
except:
    print(color("Instructions file not found in songs!", Colors.red))
    alert = True

for file_name in file_names:
    if file_name[len(file_name) - 4 : ] != ".wav":
        alert = True
        print(color(f"The file \"{file_name}\"\'s name doesn't end with \".wav\", but it was added to the playlist anyways", Colors.yellow))
    
    song_name:str = file_name.replace(".wav", "")

    if not song_name.isascii(): # TODO Testing needed
        invalid_indexes:"list[int]" = []
        for i in range(len(song_name)):
            if not song_name[i].isascii():
                invalid_indexes.append(i)

        for index in invalid_indexes:
            song_name = song_name[:index] + song_name[index + 1:]

        alert = True
        print(color(f"{file_name} was changed to {song_name} due to invalid character(s)", Colors.red))

    if (song_name in valid_commands.keys()) or song_name == "clear" or song_name == "": # Filter out any songs with the same name as a command
        alert = True
        print(color(f"{file_name} dropped due to name overlap with existing command!", Colors.red))
    else:
        songs[song_name] = Song(song_name, f"{DIRECTORY}{file_name}")

    song_names.append(song_name)

for i in range(len(song_names) - 1, -1, -1):
    try:
        if int(song_names[i]) <= len(valid_commands.keys()) + len(song_names): # Will error if the song name can't be casted to an int
            alert = True
            print(color(f"{song_names[i]} dropped due to name overlap with existing index!", Colors.red))
            del songs[i]
            del song_names[i]
    except:
        continue

if alert: # Prevent the "song dropped" messages from being instantly cleared from the console
    print()
    block_until_input()


player = spotify(songs, song_names)

def play():
    player_thread = Thread(target = player.start, daemon = True)
    player_thread.start()

    player.play_next_song(interlude = False) # Disable the waiting period before the first song

    while True:
        if player.playing:
            player.play_next_song(interlude = True) # Yields within 1.5 seconds after the player is paused
            # TODO If the user uses delayed exit, player.stop() called in play_next_song() will only kill this song-playing thread
        else:
            wait(0.5) # Wait and check whether the user has resumed the player

music_thread = Thread(target = play, daemon = True)
music_thread.start()

while not player.terminated: # Yields once the user exits the player, killing every thread
    wait(1)

# while not player.curr_song: # Wait for the player_thread to set the current song before showing/starting up the ui
#     wait(1)

# # Once most of the setup is done
# player.start()