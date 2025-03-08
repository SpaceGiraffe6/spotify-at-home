from enum import Enum
from time import sleep as wait, time
from os import listdir, get_terminal_size
from winsound import PlaySound, SND_ASYNC
from msvcrt import getch
from threading import Thread
from random import randint
from difflib import get_close_matches
from math import ceil
from typing import Union
from unicodedata import east_asian_width
import json

from song import Song
from info import *
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

# Returns the number of wide Asian characters in the string
def count_wide_characters(string:str) -> int:
    wide_characters:int = 0
    for char in string:
        if east_asian_width(char) == "W": # If this character is a wide one
            # Asian characters are twice as wide as English letters
            wide_characters += 1
    
    return wide_characters

def hide_cursor() -> None:
    print("\033[?25l", end = "")
def show_cursor() -> None:
    print("\033[?25h", end = "")
# Moves the cursor to the beginning of a previous line
# Set lines to 0 to move cursor to the beginning of the current line
def cursor_up(lines:int = 1) -> None:
    print(f"\033[{lines}F", end = "")
# Moves the cursor to the beginning of a subsequent line
def cursor_down(lines:int = 1) -> None:
    # "\033[{lines}B" moves the cursor down without moving it to the left or right
    # "\033[{lines}E" moves the cursor down AND to the beginning of the line
    print(f"\033[{lines}E", end = "")
# Moves the cursor to the left in the current line. Can't go to the previous line
def cursor_left(spaces:int = 1) -> None:
    print(f"\033[{spaces}D", end = "")
# Moves the cursor to the right in the current line. Can go past the last character in this line, but can't go to the next line
def cursor_right(spaces:int = 1) -> None:
    print(f"\033[{spaces}C", end = "")

# Will also hide the cursor
def block_until_input(message:str = "Press any key to continue") -> None:
    hide_cursor()

    if message:
        print(color(message, Colors.faint), end = "")
    getch()
    if message:
        print() # Move the cursor to the line after the prompt message (if applicable)

def confirmation(message:str = "Are you sure?") -> bool:
    message += " (y/n): "

    user_input:str = input(message).strip() # Will become an empty string if the user only entered spaces
    confirmed:bool = False
    if user_input == "" or user_input.lower().startswith("y"): # Returns True if user inputs nothing
        confirmed = True
    else:
        print("\nAction cancelled!")
        block_until_input()
    print()
    return confirmed

class ItemType(Enum):
    Default = 0
    Command = 1
    Song = 2
    Modifier = 3
    Hidden = 4
class Item:
    # Tracks the number of characters in the names of every item that has been listed, so lengths can be reused if the same name is listed again
    # Asian characters are wider than English letters
    console_lengths:"dict[str, int]" = {}

    def __init__(self, id:int = None, name:str = None, item_type:ItemType = ItemType.Default):
        self.id:int = id
        self.name:str = name
        self.item_type:ItemType = item_type

        if name not in Item.console_lengths:
            Item.console_lengths[name] = len(name) + count_wide_characters(name)
        self.display_length = Item.console_lengths[name] # The number of spaces occupied by the name of this item in the console

    def __str__(self) -> str:
        return self.name

# Helper class for search_lists
class SearchResultType(Enum):
    Exact = f"*Results are exact matches*"
    Fuzzy = f"*Results are {color('not', Colors.underline)} exact matches*" # Only the message for Fuzzy is used (in list_actions)
# Returns [search] if search is an empty string
# Returns an empty list if nothing in each search list matches the search term
# If include_result_type is True, then search_lists will return a tuple in the form (SearchResultType, searched lists)
    # The SearchResultType value tells you whether the returned results for each list were obtained using exact matching or a fuzzy search
def search_lists(search:str, lists:"list[tuple[str, list[Item]]]", index_search_enabled:bool = False, include_result_type:bool = False) -> "list[tuple[str, list[Item]]]":
    search = search.strip().lower()
    
    if not search: # If search is an empty string or only consists of spaces
        return []

    if index_search_enabled:
        # Does nothing if the search term is not a number
        try:
            index = int(search) - 1
            for _, items in lists:
                if index > len(items) - 1:
                    index -= len(items)
                else:
                    return [("", [items[index]])]
        except:
            pass
    
    results_lists:dict[SearchResultType, list[tuple[str, list[str]]]] = {result_type : [] for result_type in SearchResultType}
    for list_name, sublist in lists:
        if len(sublist) > 0:
            sublist_results, result_type = search_for_item(search = search, search_list = sublist, include_result_type = True)
            if len(sublist_results) > 0:
                results_lists[result_type].append((list_name, sublist_results))

    results, result_type = (results_lists[SearchResultType.Exact], SearchResultType.Exact) if len(results_lists[SearchResultType.Exact]) > 0 else (results_lists[SearchResultType.Fuzzy], SearchResultType.Fuzzy)
    if include_result_type:
        return (results, result_type)
    return results
# Set index_search_list to something that's not a list to disable index search. If it's not specified, then it will automatically try to index search the search_list
# Relative order of items in search_list will be kept the same
def search_for_item(search:str, search_list:"list[Item]", include_result_type:bool = False) -> "list[Item]":
    if not search: # If search is an empty string
        return [search]

    # If search is a valid index, search_lists would've returned something before calling search_for_item
    result_type:SearchResultType = SearchResultType.Exact
    results:list[Item] = [] # Add in the exact matches

    search_pairs:dict[Item, tuple[set[str]]] = {}
    token_sequence_length:int = search.count(" ") + 1
    precise_match_found:bool = False
    for item in search_list:
        if item.name.lower() == search:
            if not precise_match_found:
                results.clear()
                precise_match_found = True
            results.append(item)

        elif not precise_match_found:
            item_tokens:list[str] = item.name.lower().split(" ")
            token_sequences:set[str] = {" ".join(item_tokens[i : max(i + token_sequence_length, token_sequence_length)])[:len(search)] for i in range(max(1, len(item_tokens) - token_sequence_length + 1))}
            for sequence in token_sequences:
                if sequence == search:
                    results.append(item)
                    break
                    
            search_pairs[item] = token_sequences

    # If the user made a typo in the search and no matches were found
    if len(results) == 0:
        all_tokens:set[str] = set()
        for token_sequence in search_pairs.values():
            all_tokens |= token_sequence

        filtered_tokens:set[str] = set(get_close_matches(search, all_tokens, n = len(all_tokens))) # The higher the cutoff parameter (between 0 and 1), the stricter the search will be (default is 0.6)
        for item, token_sequences in search_pairs.items():
            if not filtered_tokens.isdisjoint(token_sequences):
                results.append(item)
                
        result_type = SearchResultType.Fuzzy
    
    # Return the result (with the result type, if requested)
    if include_result_type:
        return (results, result_type)
    return results

# Removes repeat values from target in-place and returns a new, edited list
def remove_duplicates(target:list) -> list:
    s:set = set(target)

    processed_list:list = []
    for item in target:
        if item in s:
            processed_list.append(item)
            s.discard(item)

    return processed_list

# Remove any parenthesized tags in the song name and return the distilled song name
def get_pure_song_name(song_name:str) -> str:
    try:
        return song_name[:song_name.index("(") - 1] # Minus 1 to exclude the space in front of the parentheses
    except: # If there is no "(" character in the song name
        return song_name
# Converts items in a list into a grammatical sentence with commas and connectors
# str_color: the color for each item listed in the sentence. Commas and connectors added by fix_grammar won't be colored
def fix_grammar(items:"list[any]", str_color:Colors = Colors.reset) -> str:
    items = [str(item) for item in items]
    if len(items) == 0:
        return "No items were recieved..."
    elif len(items) == 1:
        return color(items[0], str_color)
    elif len(items) == 2:
        return f"{color(items[0], str_color)} and {color(items[1], str_color)}"
    else:
        sentence:str = ""
        for i in range(len(items) - 1):
            sentence += color(items[i], str_color) + ", "

        return (sentence + f"and {color(items[-1], str_color)}")

# Only used to create and format the list of results to pass to list_actions
def initial_results(*sections:"tuple[str, list[Item]]") -> "list[tuple[str, list[Item]]]":
    curr_listing_index:int = 1
    for _, items in sections:
        for item in items:
            if item.item_type != ItemType.Hidden:
                item.id = curr_listing_index
                curr_listing_index += 1

    return list(sections)
# Only used to create and format individual sublists when passing a list of results to list_actions
# items_type argument will be ignored if a list of items is passed into "items"
def section(header:str, items:"list[str] | list[Item]", items_type:ItemType = ItemType.Default) -> "tuple[str, list[Item]]":
    return (header, items if (len(items) > 0 and type(items[0]) == Item) else to_items(items, items_type = items_type))

# Creates a new list where each element is an item that positionally corresponds to a string in strs
def to_items(strs:"list[str]", items_type:ItemType = ItemType.Default) -> "list[Item]":
    return [Item(id = None, name = item_name, item_type = items_type) for item_name in strs]

class Modes(Enum):
    Repeat = 0
    Loop = 1
    Shuffle = 2
class ListModes(Enum):
    Songs = 0
    Song = 1
    Queue = 2
    Modifiers = 3
    ListCreation = 4
    Sequences = 5
    Sequence = 6
    Default = 7
class ReturnFlags(Enum):
    UnrecognizedInput = 1 # Currently only used when returning listing results for ListModes.ListCreation


# To be implemented
class Command:
    def __init__(self, keyword:str, action:"function", requires_exact:bool = False, hidden:bool = False):
        self.keyword = keyword
        self.action = action
        self.requires_exact = requires_exact
        self.hidden = hidden

    def run(self):
        self.action()
    
    def __str__(self) -> str:
        return (self.keyword if not self.hidden else "")
    def __repr__(self) -> str:
        return (self.keyword if not self.hidden else color(self.keyword, Colors.faint))
    def __hash__(self) -> int:
        return hash(self.keyword)

class Keybind:
    directory:"dict[str, Keybind]" = {}
    active_keys:"set[str]" = set()

    # Calls the Keybind instance tied to the key
    # returns True if the specified keybind exists and is active, False otherwise
    @staticmethod
    def run_keybind(key:str) -> bool:
        if key in Keybind.active_keys:
            Keybind.directory[key]()
            return True
        else:
            return False

    # Print a comma-separated list of the active keys' descriptions
    @staticmethod
    def list_active_keybinds() -> str:
        return ", ".join([Keybind.directory[key].description for key in Keybind.active_keys])

    def __init__(self, key:str, action:"function", description:str = "do something", is_active:bool = True):
        self.key:str = key
        self.action:function = action
        self.is_active:bool = is_active

        Keybind.directory[key] = self
        if self.is_active:
            Keybind.active_keys.add(key)      

        self.description:str = f"[{color(('space' if key == ' ' else key))}]: {description}"

    # Updates both the instance data and Keybind.active_keys
    def activate(self) -> None:
        self.active = True
        Keybind.active_keys.add(self.key)
    def deactivate(self) -> None:
        self.active = False
        Keybind.active_keys.discard(self.key)

    # Run the action binded to the key
    def __call__(self) -> None:
        self.action()
    def __str__(self) -> str:
        return self.description


class spotify:
    # Constant + static variables
    COOLDOWN_BETWEEN_SONGS:int = 8 # Seconds
    # When the playback mode is shuffle, the minimum number of songs that would have to play between each repeat
    COOLDOWN_BETWEEN_REPEATS:int = 5 # Will be capped at len(playlist) - 1 in the constructor
    
    SAVE_FILE_PATH:str = "save_file.json"

    def __init__(self, songs:dict, song_names:list): # Passes song_names in as an argument to keep the order of the names the same each time the code runs
        save_file:dict[str, any] = {}
        try:
            with open(self.SAVE_FILE_PATH, "r", encoding = "utf-8") as file:
                save_file = json.load(file)
        except:
            pass


        # Initialize the songs
        Song.parent_player = self # Set the parent player of the songs before anything else

        self.songs:dict[str, Song] = songs # Keys are the name of the song
        self.song_names:list[Song] = song_names
        self._max_song_name_length:int = 0
        for name, song in self.songs.items(): # Set the parent player of the song objects
            if len(name) > self._max_song_name_length:
                self._max_song_name_length = len(name)
            if name in save_file.get("sequences", {}):
                song.update_sequence(save_file["sequences"][name])

        # For safe measure, in case a command name is longer than the longest song name
        for command in valid_commands.keys():
            if len(command) > self._max_song_name_length + 15:
                self._max_song_name_length = len(command)

        self.curr_song:Song = None
        self.curr_song_index:int = 0
        self.bookmark_index:int = None # Only used to prevent the index increments from being disrupted by sequences while in loop mode. Stores the index of the song that activated the sequence and resets to None after each sequence ends
        self.mode:Modes = Modes[save_file.get("mode", "Shuffle")] # Default to shuffle mode

        self.sequence:list[str] = [song_name for song_name in save_file.get("active_sequence", []) if song_name in self.song_names]
        # Play the saved curr_song first, if there is a one
        if save_file.get("curr_song", None) in self.song_names:
            self.sequence.insert(0, save_file["curr_song"]) # Don't call play_next_song() here as it will be called from another thread

        self.disabled_song_names:set[str] = set(save_file.get("disabled", set())) # self.save() converts sets to lists before saving as json
        for song_name in self.disabled_song_names:
            self.songs[song_name].disable() # Avoid using self.disable_song() because it will print confirmation messages

        self.queue:list[Song] = []
        self.queue_song_names:list[str] = []
        for song_name in save_file.get("queue", []):
            if song_name == PLACEHOLDER_SONGNAME:
                self.queue.append(None)
                self.queue_song_names.append(PLACEHOLDER_SONGNAME)

            elif song_name in self.song_names:
                # Don't use self.enqueue since it will print things for every song that's enqueued
                self.queue.append(self.songs[song_name])
                self.queue_song_names.append(song_name)

                self.songs[song_name].set_enqueued() # Update the enqueued status in the song

        # Modifiers that are hard-coded to songs here will be added to the saved modifiers
        self.modifiers:dict[Modifiers, list[str]] = {Modifiers.hot : [], Modifiers.cold : []}
        # Fills in any modifiers not covered by the hard-coded modified songs or the modifiers in the save file
        for modifier in Modifiers:
            self.modifiers.setdefault(modifier, [])
            if "modifiers" in save_file:
                self.modifiers[modifier].extend([song_name for song_name in save_file["modifiers"][modifier.name] if song_name in self.songs])

            # Add this modifier to the songs that are initialized with the modifier
            # Temporarily set the synced_list_count of all songs to 1
            for song in [self.songs[song_name] for song_name in self.modifiers[modifier]]:
                song.attributes[SongAttributes.modifiers].add(modifier)
        for song in self.songs.values():
            song.recalculate_weight(1)

        self.synced_songs:dict[str, list[str]] = {}
        for song_name in self.modifiers[Modifiers.synced]:
            pure_song_name:str = get_pure_song_name(song_name)
            self.synced_songs.setdefault(pure_song_name, [])
            self.synced_songs[pure_song_name].append(song_name)

        # Update the synced list_count of all synced songs
        for synced_list in self.synced_songs.values():
            for song_name in synced_list:
                self.songs[song_name].add_modifiers(synced_songs_count = len(synced_list))

        self.sequences:dict[str, list[str]] = save_file.get("sequences", {})
        # Filter out any lead songs or sequence songs that don't exist
        for lead_name, sequenced_names in self.sequences.items():
            if lead_name not in self.song_names:
                del self.sequences[lead_name]

            else:
                for sequenced_index in range(len(sequenced_names) - 1, -1, -1):
                    if sequenced_names[sequenced_index] not in self.song_names:
                        del sequenced_names[sequenced_index]

        self.COOLDOWN_BETWEEN_SONGS = max(0, self.COOLDOWN_BETWEEN_SONGS)
        self.remaining_interlude_indicator:str = None # Indicates how much time is left for the cooldown period between this song and the next one
        self.COOLDOWN_BETWEEN_REPEATS = min(len(self.song_names) - 1, self.COOLDOWN_BETWEEN_REPEATS)
        self.songs_on_cooldown:list[list[Song]] = []

        self.encore_activated:bool = False
        self.exit_later:bool = False

        self.playing:bool = True
        self.terminated:bool = False
        self.interlude_flag:bool = True # Whether there will be a cooldown period before the next song plays. Will be (re)set to True when the next song starts playing

        self.listing_info:dict[ListModes, dict[str, any]] = {
            ListModes.Songs : {
                "header line" : f"Select a song to view (or a command to run)",
                "special commands" : {},
                "no results" : {"message" : "No songs found! Please check your spelling", "action" : self.list_songs},
                "disabled color keys" : [],
                "prompt" : f"Enter the index or the name of the song to view ({color('q')}/{color('quit')} to cancel): ",
                "no input" : valid_commands["quit"]
            },
            ListModes.Queue : {
                "header line" : f"Select a command, or a song to remove from the queue",
                "special commands" : {"clear" : {"confirmation" : confirmation, "action" : self.clear_queue}},
                "no results" : {"message" : "No songs found! Please check your spelling", "action" : self.list_queue},
                "disabled color keys" : [SongAttributes.playing, SongAttributes.disabled, SongAttributes.sequenced, SongAttributes.modifiers],
                "prompt" : f"Enter the index or the name of the song to remove ({color('q')}/{color('quit')} to cancel, {color('clear')} to clear queue): ",
                "no input" : valid_commands["quit"]
            },
            ListModes.Modifiers : {
                "header line" : f"Select a modifier to remove it from all songs, or select a song to remove all modifiers from that song",
                "special commands" : {"clear" : {"confirmation" : confirmation, "action" : self.remove_modifier}},
                "no results" : {"message" : "No modifier found! Please check your spelling", "action" : self.list_active_modifiers},
                "disabled color keys" : [SongAttributes.playing, SongAttributes.disabled, SongAttributes.queued, SongAttributes.sequenced],
                "prompt" : f"Select a modifier to clear that modifier select a song to clear all of its modifiers ({color('clear')} to clear all modifiers): ",
                "no input" : valid_commands["quit"]
            },
            ListModes.Song : {
                "header line" : "Select a command to run or a modifier to add/remove for {song_name}",
                "special commands" : {"clear" : {"confirmation" : None, "action" : self.remove_modifier},
                                        "enqueue" : {"confirmation" : None, "action" : self.enqueue},
                                        "disable" : {"confirmation" : None, "action" : self.disable_song},
                                        "enable" : {"confirmation" : None, "action" : self.enable_song},
                                        "sequence" : {"confirmation" : None, "action" : lambda song_name:self.edit_sequence(song_name)}},
                "no results" : {"message" : "No results found! Please check your spelling", "action" : self.list_song},
                "disabled color keys" : [],
                "prompt" : f"Select a modifier ({color('clear')} to clear all modifiers from this song, or {color('[space]')} to enqueue): ",
                "no input" : valid_commands["quit"]
            },
            ListModes.ListCreation : {
                "header line" : None,
                "special commands" : {},
                "no results" : {"message" : "No results found! Please check your spelling", "action" : lambda *_:ReturnFlags.UnrecognizedInput},
                "disabled color keys" : [SongAttributes.playing, SongAttributes.sequenced],
                "prompt" : f"Enter an item to add/remove it from the list ({color('q')}/{color('quit')} to return to home screen): ",
                "no input" : lambda *_:self.save()
            },
            ListModes.Sequences : {
                "header line" : f"Select a numbered song to edit its sequence",
                "special commands" : {"clear" : {"confirmation" : confirmation, "action" : self.clear_all_sequences}},
                "no results" : {"message" : "No results found! Please check your spelling", "action" : self.list_sequences},
                "disabled color keys" : [SongAttributes.playing, SongAttributes.sequenced],
                "prompt" : f"Enter the index or name of a standalone song ({color('new')} to create a new sequence, {color('clear')} to clear all sequences): ",
                "no input" : valid_commands["quit"]
            },
            ListModes.Default : {
                "header line" : f"Which one do you mean?",
                "special commands" : {},
                "no results" : {"message" : "No results found! Please check your spelling", "action" : lambda *_:ReturnFlags.UnrecognizedInput},
                "disabled color keys" : [],
                "prompt" : f"Enter the index or the name of the result ({color('q')}/{color('quit')} to cancel): ",
                "no input" : valid_commands["quit"]
            }}
        self.listing_colors:dict[SongAttributes, dict[str, any]] = {SongAttributes.playing : {"enabled" : True, "color" : SongAttributes.playing.value, "nameset" : None, "message" : "Currently playing"},
                                                SongAttributes.disabled : {"enabled" : True, "color" : SongAttributes.disabled.value, "nameset" : self.disabled_song_names, "message" : "Disabled"},
                                                SongAttributes.queued : {"enabled" : True, "color" : SongAttributes.queued.value, "nameset" : self.queue_song_names, "message" : "Queued"},
                                                SongAttributes.sequenced : {"enabled" : True, "color" : SongAttributes.sequenced.value, "nameset" : self.sequences.keys(), "message" : "Has sequence"},
                                                SongAttributes.modifiers : {"enabled" : True, "color" : SongAttributes.modifiers.value}}

        # Stores the songs that have been played during this session
        self.song_log:list[str] = [] # Currently only used by self.autoupdate_ui()

        self.key_command_buffer:str = None
        # Add the key commands
        Keybind(" ", self.pause_or_resume, description = "pause/resume")
        Keybind("r", self.encore, description = "repeat the current song")
        Keybind("l", self.list_songs, description = "list songs")
        Keybind("e", self.stop, description = "terminate the program")
        Keybind("h", self.display_keybinds, description = "list all keybinds")

    # Returns the number of songs synced with this song, including this song
    def get_synced_count(self, song_name:str) -> int:
        pure_name:str = get_pure_song_name(song_name)
        if pure_name in self.synced_songs:
            return len(self.synced_songs[pure_name])
        else:
            return 1 # Becuase each song is technically always synced with itself

    # Call this after the thread that plays the songs has been started
    def start(self) -> None:
        if len(self.songs) > 0:
            show_cursor()
            self.update_ui()
        else:
            print("No valid audio files found!")
            block_until_input(message = "Press any key to exit")
            exit()
    # Rewrites the save file
    def save(self) -> None:
        data:dict = {
            "mode" : self.mode.name,
            "curr_song" : self.curr_song.song_name,
            "disabled" : list(self.disabled_song_names),
            "queue" : self.queue_song_names,
            "active_sequence" : self.sequence,
            "modifiers" : {modifier.name : modifier_list for modifier, modifier_list in self.modifiers.items()},
            "sequences" : self.sequences
        }

        with open(self.SAVE_FILE_PATH, "w", encoding = "utf-8") as save_file:
            json.dump(data, save_file, indent = 4)
    
    # Stops execution of the player's thread
    def stop(self) -> None:
        clear_console()
        # If the current song will be over in 5 seconds or less, set curr_song to the next song and save that before exitting
        # The remaining time for the current song will be 0 if a delayed exit was used, unless the last song before the exit was skipped midway through
        if (self.exit_later) or (self.curr_song.duration - self.curr_song.curr_duration <= 5):
            self.set_next_song()

        self.save()
        print("Program terminated via command!")
        self.terminated = True # Will break the loop propping up the main thread (at the end of the script)
        exit() # Kill this thread so the rest of the code won't keep running if stop() was called from list_actions()
    # Stops the program after the current song ends
    def delayed_exit(self) -> None:
        self.exit_later = not self.exit_later
        self.update_ui()

    # Uses self.list_actions to edit selected_names using the items in selection_pool
        # Will directly edit selected_names and selection_pool
    # header_line: custom header line, defaults to the default header line for ListModes.ListCreation in self.listing_info
    # lead_item_name: the string to pass into the listing_item_name parameter of self.list_actions
    # allow_duplicates: whether multiple copies of an item from selection_pool can be added into selected_names
    def create_list(self, selection_pool:"list[str]", selected_names:"list[str]", items_type:ItemType = ItemType.Default, header_line:str = "", lead_item_name:str = None, allow_duplicates:bool = False) -> Union[list, None]:
        if not header_line:
            header_line = f"Add an item to the list"
        self.listing_info[ListModes.ListCreation]["header line"] = header_line

        result:Union(Item, ReturnFlags) = True # Initialize to True to start the first iteration of the loop
        while result:
            selected_section:tuple[str, list[Item]] = section("Current items: (select one to remove)", selected_names, items_type = items_type)
            selection_pool_section:tuple[str, list[Item]] = section("Available selection: (select one to add)", selection_pool, items_type = items_type)
            result = self.list_actions(initial_results(section("Commands:", ["q", "quit"], items_type = ItemType.Command), selected_section, selection_pool_section), list_type = ListModes.ListCreation, listing_item_name = lead_item_name)
        
            if result: # Continue to the next iteration of the loop if the user entered something wrong
                if result in selected_section[1]: # Remove an item from selected_items
                    selected_names.remove(result.name)

                    if not allow_duplicates:
                        selection_pool.append(result.name)

                elif result in selection_pool_section[1]: # Add an item to selected_items
                    selected_names.append(result.name)

                    if not allow_duplicates:
                        selection_pool.remove(result.name)

                else: # If invalid result
                    print(color('Invalid item selected!', Colors.red))
                    block_until_input()
            # If result is None, the program has ended

    def list_sequences(self, *_) -> None:
        unsequenced_song_names:list[str] = [song_name for song_name in self.song_names if song_name not in self.sequences]
        result:Item = self.list_actions(initial_results(section("Commands:", ["q", "quit", "clear"], items_type = ItemType.Command), section("Sequences", list(self.sequences.keys()), items_type = ItemType.Song), section("Standalone songs: ", unsequenced_song_names, items_type = ItemType.Song)), list_type = ListModes.Sequences)
        if type(result) == Item: # Any returned Item is guaranteed to represent a song name
            self.edit_sequence(result.name)

    def clear_all_sequences(self, silent:bool = False) -> None:
        for song_name in self.sequences:
            self.songs[song_name].update_sequence([])
        self.sequences.clear()
        self.save()

        if not silent:
            clear_console()
            print("Cleared all sequences!")
            block_until_input()
            self.update_ui()
    # 
    def edit_sequence(self, lead_song_name:str) -> None:
        self.sequences.setdefault(lead_song_name, [])
        self.create_list(selection_pool = self.song_names.copy(), selected_names = self.sequences[lead_song_name], items_type = ItemType.Song, header_line = f"Editing the sequence of {color(lead_song_name, Colors.bold)}", lead_item_name = lead_song_name, allow_duplicates = True)
        
        new_sequence = self.sequences[lead_song_name]
        # self.create_list() should edit the passed-in lists in-place
        if len(new_sequence) > 0:
            self.sequences[lead_song_name] = new_sequence
        else:
            del self.sequences[lead_song_name]

        self.songs[lead_song_name].update_sequence(new_sequence)
        self.save()
        
        clear_console()
        print(f"Sequence updated for {color(lead_song_name, Colors.bold)}")
        block_until_input()
        self.update_ui()

    # Add a song to the queue and return to the home screens
    def enqueue(self, song_name:str = None) -> None:
        if song_name:
            self.queue.append(self.songs[song_name])
            self.queue_song_names.append(song_name)
            self.songs[song_name].set_enqueued()

            clear_console()
            print(f"{color(song_name, Colors.purple)} added to queue!")
            block_until_input()
        else: # Enqueue a placeholder song
            self.queue.append(None)
            self.queue_song_names.append(PLACEHOLDER_SONGNAME)

        self.update_ui()

    # Clear the queue, print a message, and return to the home screen
    def clear_queue(self) -> None:
        for item in self.queue:
            if item: # item will be None if the song is a placeholder
                item.set_dequeued()
        self.queue.clear()
        self.queue_song_names.clear()
        print("Queue cleared!")

        block_until_input()
        self.update_ui()
    # If only remove_at_index is provided, then only remove the song in the queue at that index
    # If only song_name is provided, then remove all occurrences of that song from the queue
    # If song_name and remove_at_occurrence are provided, then remove that occurrence of the song from the queue
    def remove_queued_item(self, song_name:str = None, remove_at_occurrence:int = None, remove_at_index:int = None) -> None:
        removals:int = 0
        
        if remove_at_index != None:
            song_name = self.remove_queued_item_at_index(remove_at_index)
            removals += 1
        else:
            occurrences:"list[int]" = [index for index in range(len(self.queue_song_names) - 1, -1, -1) if self.queue_song_names[index] == song_name]
            
            if remove_at_occurrence and (remove_at_occurrence <= len(occurrences)):
                remove_at_occurrence -= 1
                if remove_at_occurrence < len(occurrences):
                    occurrences.reverse()
                    song_name = self.remove_queued_item_at_index(occurrences[remove_at_occurrence])
                    removals += 1
                # Do nothing here if remove_at_occurrence is an invalid number
            elif len(occurrences) > 0:
                song_name = self.queue_song_names[occurrences[0]]
                for i in occurrences:
                    self.remove_queued_item_at_index(i)

                removals += len(occurrences)
        
        # Print the information about the removals
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
    # Helper function for remove_queued_item()
    # Removes an item without printing anything
    # Returns the name of the song that was removed
    def remove_queued_item_at_index(self, index:int) -> str:
        song_name:str = self.queue_song_names[index]
        del self.queue_song_names[index]
        del self.queue[index]
        if song_name != PLACEHOLDER_SONGNAME and (song_name not in self.queue_song_names): # Only set the queued attribute to False if no more occurrences of this song remain in the queue after this removal
            self.songs[song_name].set_dequeued()

        return song_name
    
    def list_queue(self, *_) -> None:
        if len(self.queue) > 0 or len(self.sequence) > 0:
            list_type:ListModes = ListModes.Queue
            # Don't include headers for each section in case they mess up the formatting of the active sequence
            listing_commands:list[str] = ["q", "quit", "clear"]
            result:Item = self.list_actions(initial_results(section("", listing_commands, items_type = ItemType.Command), section("", self.queue_song_names, items_type = ItemType.Song)), list_type = list_type)
            
            if result and (result.name in self.queue_song_names):
                self.remove_queued_item(remove_at_index = result.id - len(listing_commands) - 1)
            else:
                self.handle_invalid_result()

        else:
            clear_console()
            print("There are no songs in the queue or an active sequence...")
            block_until_input()

            self.update_ui()

    def list_active_modifiers(self, *_) -> None:
        active_modifier_names:list[str] = []
        # Add the songs with modifiers
        modified_song_names:list[str] = []
        modified_song_names_set:set[str] = set()
        for modifier in MODIFIERS_COLORING_ORDER:
            modifier_list:list[str] = self.modifiers[modifier]

            if len(modifier_list) > 0:
                active_modifier_names.append(modifier.name)
                for song_name in modifier_list:
                    if song_name not in modified_song_names_set:
                        modified_song_names.append(song_name)
                modified_song_names_set = modified_song_names_set | set(modifier_list)

        if len(active_modifier_names) > 0:
            list_type:ListModes = ListModes.Modifiers
            result:Item = self.list_actions(initial_results(section("Commands:", ["q", "quit", "clear"], items_type = ItemType.Command), section("Modifiers", active_modifier_names, items_type = ItemType.Modifier), section("Modified songs:", modified_song_names, items_type = ItemType.Song)), list_type = list_type)
            if result:
                result_name:str = result.name

                if (result_name in active_modifier_names):
                    self.remove_modifier(modifier = Modifiers[result_name])
                elif result_name in modified_song_names_set:
                    self.remove_modifier(song_name = result_name)
                else:
                    self.handle_invalid_result()
            # Do nothing if result is None
        else:
            clear_console()
            print("There are no active modifiers...")
            block_until_input()

            self.update_ui()
    def add_modifier(self, song_name:str, modifier:Modifiers, silent:bool = False) -> bool: # Returns True if modifier was successfully added, False otherwise
        overlaps:set[Modifiers] = set()
        for exclusive_set in EXCLUSIVE_MODIFIERS:
            if modifier in exclusive_set:
                overlaps = overlaps | (self.songs[song_name].attributes[SongAttributes.modifiers] & exclusive_set)

        if len(overlaps) == 0:
            if not silent:
                clear_console()
        else:
            if silent: # Remove conflicting modifiers by default
                for overlap in overlaps:
                    self.remove_modifier(song_name = song_name, modifier = overlap, silent = True)
            else:
                modifier_strs:list[str] = []
                for overlap in overlaps:
                    modifier_strs.append(color(overlap.name, overlap.value["color"]))
                
                message_agreement:str = "modifier conflicts"
                prompt_agreement:str = "this modifier"
                modifiers_sentence:str = fix_grammar(modifier_strs)
                if len(overlaps) > 1:
                    message_agreement = "modifiers conflict"
                    prompt_agreement = "these modifiers"

                print(f"The {modifiers_sentence} {message_agreement} with the adding modifier!")
                if confirmation(message = f"Would you like to remove {prompt_agreement} and add the {color(modifier.name, modifier.value['color'])} modifier?"):
                    for overlap in overlaps:
                        self.remove_modifier(song_name = song_name, modifier = overlap, silent = True)

                    clear_console()
                    print(f"Removed the {modifiers_sentence} modifier(s) and")
                else: # If the user cancels the action
                    self.update_ui()
                    return
        
        if modifier == Modifiers.synced:
            self.sync_songs(song_name)
            return

        self.modifiers[modifier].append(song_name)
        self.songs[song_name].add_modifiers(self.get_synced_count(song_name), modifier)

        if not silent:
            print(f"Added the {color(modifier.name, modifier.value['color'])} modifier to {color(song_name, Colors.bold)}")
            block_until_input()
            self.update_ui()
    def sync_songs(self, song_name:str, silent:bool = False):
        if not silent:
            clear_console()
        message:str = ""

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
                    self.songs[syncing_song_name].add_modifiers(len(syncing_songs), Modifiers.synced)

                    message = f"{color('Synced', Modifiers.synced.value['color'])} {fix_grammar(syncing_songs, str_color = Colors.bold)}"
            else:
                message = f"No other versions of {color(pure_name, Colors.bold)} were found..."
        elif song_name not in self.synced_songs[pure_name]: # If this song was added to the songs folder after a set of synced songs with its name has already been created
            # Print the message before self.synced_songs[pure_name] is updated
            message = f"{color('Synced', Modifiers.synced.value['color'])} {color(song_name, Colors.bold)} with {fix_grammar(self.synced_songs[pure_name], str_color = Colors.bold)}"
            
            synced_list:list = self.synced_songs[pure_name]
            synced_list.append(song_name)
            for synced_song_name in synced_list:
                self.songs[synced_song_name].add_modifiers(len(synced_list), Modifiers.synced)

            # Put this song next to the other songs that are synced with it in self.modifiers[Modifiers.synced]
            for i in range(len(self.modifiers[Modifiers.synced]) - 1, -1, -1):
                if get_pure_song_name(self.modifiers[Modifiers.synced]) == pure_name:
                    self.modifiers[Modifiers.synced].insert(i + 1, song_name)
        else:
            message = "This song is already synced!"

        if not silent:
            print(message)
            block_until_input()
            self.update_ui()
    def remove_modifier(self, song_name:str = None, modifier:Modifiers = None, silent:bool = False):
        song:Song = self.songs[song_name] if song_name else None

        removals:int = 0
        message:str = ""
        if not modifier:
            if song:
                active_modifiers:set[Modifiers] = song.attributes[SongAttributes.modifiers]
            
                # Format and print the "modifier(s) cleared" message
                if len(active_modifiers) == 0:
                    message = f"{color(song_name, Colors.bold)} doesn't have any modifiers..."
                else:
                    modifier_names:list[str] = [color(modifier.name, modifier.value["color"]) for modifier in active_modifiers]
                    separator:str = " "
                    noun:str = "modifier"
                    if len(modifier_names) >= 2:
                        modifier_names[-1] = "and " + modifier_names[-1]
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

                song.clear_modifiers()
            else: # If no song name or modifier is specified, clear all modifiers
                for modifier_list in self.modifiers.values():
                    removals += len(modifier_list)
                    for song_name in modifier_list:
                        self.songs[song_name].clear_modifiers()
                    modifier_list.clear()

                self.synced_songs.clear()

                message = f"Cleared {color(removals, Colors.bold)} modifier(s) from all songs"
        else: # If a modifier is specified
            if song:
                if modifier == Modifiers.synced:
                    self.desync_songs(song_name) # Will print a message with the songs that were desynced
                else:
                    try:
                        self.modifiers[modifier].remove(song_name)
                        song.remove_modifiers(self.get_synced_count(song_name), modifier)
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
                        self.songs[song_name].remove_modifiers(self.get_synced_count(song_name), modifier)

                    self.modifiers[modifier].clear() # List of synced songs in self.modifiers will be cleared by desync_songs if the modifier is Modifiers.synced

        if not silent:
            print(message)
            block_until_input()
            self.update_ui()
    def desync_songs(self, song_name:str, silent:bool = False):
        message:str = ""
        pure_name:str = get_pure_song_name(song_name)
        if pure_name in self.synced_songs:
            synced_songs_list:list = self.synced_songs[pure_name]
            for song_name in synced_songs_list:
                self.songs[song_name].remove_modifiers(1, Modifiers.synced)
                self.modifiers[Modifiers.synced].remove(song_name)

            message = f"{color('Desynced', Modifiers.synced.value['color'])} {fix_grammar(self.synced_songs[pure_name], str_color = Colors.bold)}"
            
            del self.synced_songs[pure_name]
        else:
            message = "Pure name not found in synced songs when desyncing songs!"

        if not silent:
            print(message)

    def disable_song(self, song_name:str, silent:bool = False) -> None:
        self.disabled_song_names.add(song_name)
        self.songs[song_name].disable()
        if not silent:
            clear_console()
            print(f"{color(song_name, Colors.bold)} can be automatically chosen no more...")
            block_until_input()

            self.update_ui()
    def enable_song(self, song_name:str, silent:bool = False) -> None:
        self.disabled_song_names.discard(song_name)
        self.songs[song_name].enable()
        if not silent:
            clear_console()
            print(f"Enabled {color(song_name, Colors.bold)} for automatic selection")
            block_until_input()

            self.update_ui()

    # Only call these playback functions from the play_next_song function
    # The playback mode functions will only run if the queue is empty
    # These functions will not add songs to the queue and will only set self.curr_song to the next song without playing it
    def repeat(self) -> None:
        if not self.curr_song: # If no other songs have been played
            self.curr_song_index = randint(0, len(self.song_names) - 1)
            self.curr_song = self.songs[self.song_names[self.curr_song_index]]
    def loop(self) -> None:
        if self.bookmark_index != None:
            self.curr_song_index = self.bookmark_index
            self.bookmark_index = None
        song_name:str = self.increment_song_index()

        first_check:bool = False # Becomes True after the first time the loop checks the song at next_index so I can know if the loop has cycled through everything
        stop_index:int = self.curr_song_index
        while song_name in self.disabled_song_names:
            if self.curr_song_index == stop_index:
                if not first_check:
                    first_check = True
                else: # If this loop has looped back to where it started, meaning that every song is disabled
                    print(color("No available songs found!", Colors.red))
                    print("Playing next existing song...")
                    break
            song_name = self.increment_song_index()

        self.curr_song = self.songs[song_name]
        if song_name in self.sequences:
            self.bookmark_index = self.curr_song_index
    def shuffle(self) -> None:
        # Relative order of songs in available_songs will be scrambled
        available_songs:list[Song] = list(set(self.songs.values()) - {song_name for song_name in self.queue_song_names if (song_name != PLACEHOLDER_SONGNAME) and (Modifiers.hot not in self.songs[song_name].attributes[SongAttributes.modifiers])} - {song for cooldown_group in self.songs_on_cooldown for song in cooldown_group} - {self.songs[song_name] for song_name in self.disabled_song_names}) # Filter out queued, cooldown, and disabled songs
        # No need to recalculate the weight of synced songs here since it was already calculated when the song was synced
        if len(available_songs) > 1:
            total_weight:int = 0
            for song in available_songs:
                total_weight += song.weight
            
            target_weight:int = randint(0, total_weight)
            for song in available_songs:
                target_weight -= song.weight
                if target_weight <= 0:
                    self.curr_song = song
                    self.curr_song_index = self.song_names.index(song.song_name)
                    break
        
        # If there are no available songs
        else: # The constructor would've caught/corrected the error if self.cooldown_between_repeats was too high
            if len(self.disabled_song_names) > 0:
                print("No available songs were found, so a song will be chosen randomly")
                block_until_input()

                self.curr_song_index = randint(0, len(self.song_names) - 1)
                self.curr_song = self.songs[self.song_names[self.curr_song_index]]

    # Helper function
    # Automatically makes curr_song_index wrap around when it equals/exceeds the length of song_names
    def increment_song_index(self, increment:int = 1) -> str: # Returns the name of the song at the new index
        self.curr_song_index += increment % len(self.song_names)
        if self.curr_song_index >= len(self.song_names): # Wrap around
            self.curr_song_index -= len(self.song_names)
        
        return self.song_names[self.curr_song_index]

    # Pauses or resumes the player based on whether self.playing is True
    # Only used in keybinds
    def pause_or_resume(self) -> None:
        if self.playing:
            self.pause()
        else:
            self.resume()
    def pause(self) -> None:
        if self.playing:
            self.playing = False
            PlaySound("1s_silence", SND_ASYNC)

        self.remaining_interlude_indicator = None
        hide_cursor()
        print(color("Pausing...", Colors.faint))
        wait(1 + TIMER_RESOLUTION + 0.25)
        self.update_ui()
    # Resuming the player will restart the song that was playing before the pause
    def resume(self) -> None:
        if not self.playing:
            if self.remaining_interlude_indicator: # If the player was paused in the middle of an interlude
                self.remaining_interlude_indicator = ""
            else: # The new song would've already been set during the interlude but wouldn't've started to play yet
                self.encore_activated = True # Use the encore feature to prevent play_next_song() from picking a new song
            
            self.interlude_flag = False # Temporarily disable the cooldown between songs
            self.playing = True # Resume the loop in the song-playing thread
            hide_cursor()
            print(color("Song restarting...", Colors.faint))
            wait(TICK_DURATION + 0.5) # Wait for the song-playing thread to prepare the next song before self.update_ui() displays it

        self.update_ui()
    def skip(self) -> None:
        self.playing = False
        PlaySound("1s_silence.wav", SND_ASYNC)

        print("Picking the next song...")
        wait(1 + TIMER_RESOLUTION + 0.25) # Wait for the current song's timer to stop before setting self.playing to True. Song timers update every second independent of TICK_DURATION

        self.remaining_interlude_indicator = "" # If this function was called during an interlude, clear its indication from the display
        self.interlude_flag = False # Don't wait before playing the next song
        self.playing = True # Resume the song-playing thread

        wait(TICK_DURATION + 0.5) # Wait for the song-playing thread to set the next song (Must be longer than the waiting time in each iteration in the loop in play())
        self.update_ui()
    
    # Repeat the current song an additional time
    # the repeat will not trigger any sequences
    def encore(self) -> None:
        self.encore_activated = not self.encore_activated
        self.update_ui()
        return

    def set_next_song(self) -> None:
        if self.encore_activated:
            self.encore_activated = False
            # Do nothing to curr_song and curr_song_index so the same song repeats
        else: # Don't update the sequence if the song is an encore
            if len(self.sequence) > 0: # Songs in the active sequence take priority over songs in the queue
                song:Song = self.songs[self.sequence[0]]
                del self.sequence[0]
                self.curr_song = song
                self.curr_song_index = self.song_names.index(song.song_name)
            
            else:
                if len(self.queue) > 0:
                    song:Song = self.queue[0]
                    if song:
                        self.curr_song = song
                        self.curr_song_index = self.song_names.index(song.song_name)
                    else: # If the queued song is a placeholder
                        mode_actions[self.mode](self)
                    
                    self.remove_queued_item_at_index(0) # Silently remove the item
                else:
                    mode_actions[self.mode](self) # Select the next song based on the current playback mode
                # Only activate the sequence if there wasn't already an active sequence
                if (self.curr_song.song_name in self.sequences) and (len(self.sequence) == 0):
                    # Make a copy of the song's sequence so song names can be removed
                    self.sequence = self.sequences[self.curr_song.song_name].copy()

        self.song_log.append(self.curr_song.song_name)

    # Call this function from the song-playing thread
    def play_next_song(self) -> None:
        # Delay on updating the save file if delayed exit is not toggled because there is a gap between when curr_song is set to the queued item and when the item is removed from the queue
        if self.exit_later: # Guaranteed to return
            self.stop() # stop() will update the save file and set the next song
            return

        self.set_next_song()
        # Update the songs on cooldown
        if len(self.songs_on_cooldown) >= self.COOLDOWN_BETWEEN_REPEATS:
            del self.songs_on_cooldown[0]
        self.songs_on_cooldown.append([self.songs[song_name] for song_name in self.synced_songs.get(self.curr_song.song_name, [self.curr_song.song_name]) if Modifiers.hot not in self.songs[song_name].attributes[SongAttributes.modifiers]])

        wait(TICK_DURATION)
        if self.playing: # If this song has ended naturally and not because the user paused the player
            if self.interlude_flag: # Interlude flag will be set to false when playing the first song so that everything saves BEFORE waiting and then playing each subsequent song
                self.remaining_interlude_indicator = "-" * self.COOLDOWN_BETWEEN_SONGS
                
                wait(ceil(TICK_DURATION) - TICK_DURATION) # A TICK_DURATION of time has already been waited before self.playing was checked, so a TICK_DURATION has to be taken off the first second of wait time here
                self.remaining_interlude_indicator = self.remaining_interlude_indicator[1:] # Remove a character from the cooldown indicator after the first second
                for seconds_remaining in range(self.COOLDOWN_BETWEEN_SONGS - 1, -1, -1):
                    wait(1)
                    if not self.playing: # If the player was paused during the interlude
                        return # Jump back to the loop in play() in the main thread
                    self.remaining_interlude_indicator = "-" * seconds_remaining
            else:
                self.interlude_flag = True

        self.remaining_interlude_indicator = None

        self.save()
        self.curr_song.play() # Plays the song in the same thread as this method

    def list_songs(self, *_) -> None: # Requesting a song while another song is playing will queue the requested song instead
        result:Item = self.list_actions(initial_results(section("Commands:", ["q", "quit", PLACEHOLDER_SONGNAME], items_type = ItemType.Command), section("Songs:", self.song_names, items_type = ItemType.Song)), list_type = ListModes.Songs)
        if result: # Do nothing if result is None
            if result.name == PLACEHOLDER_SONGNAME:
                self.enqueue()
            elif result.name in self.song_names:
                self.list_song(result.name)
            else:
                self.handle_invalid_result()

    # Lists the commands and modifier actions for a song
    def list_song(self, song_name:str, *_) -> None:
        listing_commands:list[str] = ["q", "quit", "disable", "enqueue", "sequence"]
        if song_name in self.disabled_song_names:
            listing_commands[2] = "enable"
        if len(self.songs[song_name].attributes[SongAttributes.modifiers]) > 0: # If the song has at least 1 modifier applied to it
            listing_commands.append("clear")

        listing_modifiers:list[str] = [modifier.name for modifier in self.modifiers.keys()]

        result:Item = self.list_actions(initial_results(section("Commands: ", listing_commands, items_type = ItemType.Command), section("Modifiers: ", listing_modifiers, items_type = ItemType.Modifier)), list_type = ListModes.Song, listing_item_name = song_name)
        if result: # Do nothing if result is None
            if result.name in listing_modifiers:
                result:Modifiers = Modifiers[result.name]
                if result in self.songs[song_name].attributes[SongAttributes.modifiers]: # If the listing song already has this modifier
                    self.remove_modifier(song_name = song_name, modifier = result)
                else:
                    self.add_modifier(song_name = song_name, modifier = result)
            else:
                self.handle_invalid_result()

            self.update_ui()
    
    def karaoke(self) -> None:
        # Constant variables
        delay:float = 0.3 # Number of seconds to delay the lyrics by to compensate for lag
        max_display_range:int = 10 # Max number of lines before/after the current line of lyrics to display
        lyrics:list[dict[str, any]] = self.curr_song.lyrics # Each line's text includes a newline character at the end

        if not lyrics:
            print("Lyrics aren't available for this song...")
            block_until_input()
            self.update_ui()
            return

        # If lyrics were found
        clear_console()
        hide_cursor()
        display_width:int = get_terminal_size().columns
        display_height:int = get_terminal_size().lines
        empty_line:str = " " * display_width
        display_range:int = max(min((display_height - 1) // 2, max_display_range), 0) # How many lines before/after the current line of lyrics to display
        
        # Listen for user input while lyric display updates
        input_thread:Thread = Thread(target = lambda : block_until_input(message = ""), name = "Karaoke input listener", daemon = True) # Automatically terminates once input is detected
        input_thread.start()

        # If the user started karaoke mode during an interlude period, before the starting time for the next song has been set
        if not self.curr_song.attributes[SongAttributes.playing]:
            print(color(f"{'Waiting for the song to start...' : ^{display_width}}", Colors.faint))

            # Wait for the interlude period to pass
            while not self.curr_song.attributes[SongAttributes.playing]:
                if not input_thread.is_alive():
                    self.update_ui()
                    return
                wait(TIMER_RESOLUTION)

            clear_console()
            hide_cursor()
            wait(TICK_DURATION) # Wait a bit longer for the song to set its start time

        for i in range(len(lyrics)):
            if i == len(lyrics) - 1 or lyrics[i + 1]["time"] >= time() - self.curr_song.start_time - delay:
                if (display_height != get_terminal_size().lines) or (display_width != get_terminal_size().columns):
                    clear_console()
                    hide_cursor()
                    display_height, display_width = get_terminal_size().lines, get_terminal_size().columns
                    empty_line = " " * display_width
                    display_range = max(min((display_height - 1) // 2, max_display_range), 0) # How many lines before/after the current line of lyrics to display

                cursor_up(lines = display_height - 1)

                # Print the lines before the current line
                print(empty_line * ((display_height - 1) // 2 - min(i, display_range)), end = "") # Vertically center the lyrics by adding padding before printing the lyric lines
                for prev_line_index in range(max(i - display_range, 0), i):
                    print(color(f"{lyrics[prev_line_index]['text'] : ^{display_width}}", Colors.faint))

                # Print the current line
                curr_line:str = lyrics[i]["text"]
                print(f'{curr_line : ^{display_width}}')

                # If there are more lyrics after the current line
                if i < len(lyrics) - 1:
                    for next_line_index in range(i + 1, min(i + 1 + display_range, len(lyrics))):
                        print(color(f'{lyrics[next_line_index]["text"] : ^{display_width}}', Colors.faint), end = "")
                    print(empty_line * (i + 1 + display_range - len(lyrics)), end = "")

                    # Animate the quarter note symbols of curr_line is an interlude without lyrics
                    notes_count:int = curr_line.count(LYRIC_PLACEHOLDER_CHARACTER)
                    segment_time:float = (lyrics[i + 1]["time"] - lyrics[i]["time"]) / (notes_count + 1) # The time between this lyric and the next one is divided into equal segments, with one note lighting up in between each segment
                    notes_shown:int = 0
                    if notes_count:
                        cursor_up(lines = display_range) # Move the cursor to the beginning of the currently playing lyric line
                        print(" " * ((display_width - len(curr_line)) // 2), end = "")

                    # Wait until the time of the next line has been reached
                    # Keeps the offset between the lyrics and the song due to lag to within TIMER_RESOLUTION seconds
                    while True:
                        if not input_thread.is_alive(): # If the user has entered something and wants to return to the home screen
                            self.update_ui()
                            return

                        time_elapsed:float = time() - self.curr_song.start_time - delay

                        if notes_shown < notes_count and time_elapsed >= lyrics[i]["time"] + ((notes_shown + 1) * segment_time):
                            notes_shown += 1
                            print(color(LYRIC_PLACEHOLDER_CHARACTER + ' ', Colors.bold), end = "")

                        elif time_elapsed >= lyrics[i + 1]["time"] or time_elapsed < 0: # time_elapsed will be negative if karaoke mode was somehow activated before the song updates its start time when song.play() is called
                            break

                        wait(TIMER_RESOLUTION)

                else: # If there are no more lyrics
                    print(empty_line) # Clear the last line from the previously shown group of lyrics
                    wait(self.curr_song.duration - (time() - self.curr_song.start_time)) # Wait until the current song ends
                    
                    if not self.exit_later: # Give way for the "program terminated" message
                        # Prompt the user to clear the current input() call by input_thread before the next input() call from update_ui()
                        clear_console()
                        hide_cursor()
                        # Format the prompt and horizontally center it
                        print(f"{' ' * ((display_width - len('Song finished - press any key to return')) // 2)}{color('Song finished - press any key to return', Colors.faint)}", end = "")
                        while input_thread.is_alive():
                            wait(TIMER_RESOLUTION)

                        self.update_ui()

    def update_ui(self, command:str = "") -> None: # The command parameter is used when update_ui() is called via self.listing_info
        clear_console() # Clear the console
        self.save()

        if not command:
            self.print_ui_header()
            print()
            # # List the queue if it's not empty
            # if len(self.queue) > 0 or len(self.sequence) > 0:
            #     print("Up next:")
            #     max_index_len:int = len(str(len(self.queue)))
            #     for song_name in self.sequence:
            #         print(f"{'-  ' : <{max_index_len + 2}}{color(song_name, SongAttributes.sequenced.value)}")
                
            #     # Print the queue
            #     for i in range(len(self.queue)):
            #         print(f"{f'{i + 1}. ' : <{max_index_len + 2}}{color(self.queue_song_names[i], Colors.purple)}")

            queue_lines_count:int = self.print_next_songs()
            if queue_lines_count > 0:
                print()

            command = input(f"Input command (Enter {color('help')} for help, {color('[space]')} to {'pause' if self.playing else 'resume'}, or enter nothing to refresh): ")
        
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
                return
            # If the command is a number but isn't a valid index, go to the "finally" block
        finally: # If the command can't be cast to a number
            self.input_command(command, index_search_enabled = False)
    def autoupdate_ui(self) -> None:
        input_thread:Thread = Thread(target = self.get_key_command, name = "Standby mode input listener", daemon = True)
        input_thread.start()

        while True: # Loops once per song and once more per interlude
            clear_console()
            hide_cursor()

            header_lines_count:int = self.print_ui_header() + 1 # +1 for the following empty line
            print()
            queue_lines_count:int = self.print_next_songs(max_lines = get_terminal_size().lines - header_lines_count - 2) # -2 for the "Standby mode" lines
            if queue_lines_count > 0:
                print() # Separate the sequence/queue from the next line
            print(f"{color('Standby mode - ', Colors.faint)}{Keybind.directory['h']}, press any other key to return", end = "")
            # If there's space, add an extra empty line to clear anything that might've ended up there
            if (header_lines_count + queue_lines_count + 2) < get_terminal_size().lines:
                print(f"\n{' ' * get_terminal_size().columns}", end = "")

            cursor_up(lines = get_terminal_size().lines)

            # If an interlude is ongoing
            if self.remaining_interlude_indicator != None:
                while self.remaining_interlude_indicator != None:
                    print(f"{self.remaining_interlude_indicator : ^{max(len('Currently playing: ') + self._max_song_name_length + 13, self.COOLDOWN_BETWEEN_SONGS)}}", end = "") # +13 for the spaces reserved for the song duration display and the spaces between each segment
                    cursor_up(lines = 0)

                    curr_interlude_indicator:str = self.remaining_interlude_indicator
                    # Wait for curr_interlude_indicator to update
                    while curr_interlude_indicator == self.remaining_interlude_indicator:
                        wait(TIMER_RESOLUTION)

                        if not input_thread.is_alive():
                            if not self.run_key_command():
                                # If a valid key input has not been entered
                                self.update_ui()
                            return

            # If a song is currently playing
            else:
                # Prepare the cursor position for updating the song duration display
                # The cursor would've already been moved to the first line
                cursor_right(spaces = len("Currently playing: ") + self._max_song_name_length + 4)# + count_wide_characters(self.curr_song.song_name)) # Move the cursor past fewer characters if some of the characters are extra wide
                wait(TICK_DURATION) # Wait for the next song to start playing

                # While the current song hasn't ended
                while (self.curr_song.attributes[SongAttributes.playing]) and (self.remaining_interlude_indicator == None) and (input_thread.isAlive()):
                    curr_duration_seconds:str = self.curr_song.curr_duration
                    curr_duration_string:str = to_minutes_str(curr_duration_seconds)
                    # Move the cursor back and forth to update the duration display
                    print(color(f"{curr_duration_string : >5}", Colors.light_blue), end = "")
                    cursor_left(5)
                    
                    while curr_duration_seconds == self.curr_song.curr_duration:
                        wait(TIMER_RESOLUTION)

                        if not input_thread.is_alive():
                            if not self.run_key_command():
                                # If a valid key input has not been entered
                                self.update_ui()
                            return

                wait(1 + TICK_DURATION * 2) # Wait for self.remaining_interlude_indicator to update
    # Helper functions for self.update_ui() and self.autoupdate_ui()
    # Both self.print_ui_header() and self.print_next_songs() return the number of lines they printed
    def print_ui_header(self) -> int:
        lines_printed:int = 0

        indicator_conditions:dict[str, bool] = {"🎤" : bool(self.curr_song.lyrics),
                                                "🔁" : self.encore_activated,
                                                "⌛" : self.exit_later}
        indicators:list[str] = []
        for indicator, condition in indicator_conditions.items():
            if condition == True:
                indicators.append(indicator)

        # indicators will become a string either way
        indicators:str = "| " + " ".join(indicators) if len(indicators) else ""
        duration_display = color(f"{f'{to_minutes_str(self.curr_song.curr_duration)}/{to_minutes_str(self.curr_song.duration)}' : >11}", Colors.light_blue)

        currently_playing_line = f"Currently playing: {color(f'{self.curr_song.song_name : <{self._max_song_name_length - count_wide_characters(self.curr_song.song_name)}}', Colors.green)}   {duration_display} {indicators}"
        if self.remaining_interlude_indicator: # If the cooldown is active, ensure that there is enough sapce for the maximum size of the indicator while also adding spaces to match the length of the line with its length when a song is playing
            currently_playing_line:str = f"{self.remaining_interlude_indicator : ^{max(len(remove_tags(currently_playing_line)) - len(indicators) - 1, self.COOLDOWN_BETWEEN_SONGS)}}"
        print(f"{currently_playing_line} | Playback mode: {color(f'{self.mode.name : <10}', Colors.orange)}")
        lines_printed += 1
        
        if self.remaining_interlude_indicator:
            print(f"Next song: {color(self.curr_song.song_name, Colors.bold)}")
            lines_printed += 1

        if not self.playing:
            print("--Music player paused--")
            lines_printed += 1
        
        return lines_printed
    def print_next_songs(self, max_lines:int = 999) -> int:
        # Printing items requires at least 2 lines (more lines if there are more items)
        if max_lines < 2 or (len(self.sequence) + len(self.queue_song_names) == 0):
            return 0
        else: # If there are songs in the queue/sequence
            lines_printed:int = 1
            print("Up next:")
            max_index_len:int = len(str(len(self.queue_song_names)))

            # Print the sequence
            # At this point, there is guaranteed to be at least one available line
            for i in range(len(self.sequence)):
                lines_printed += 1 # Prematurely add one, since each branch in the following "for" is guaranteed to print 1 line
                
                # If this is the last available line and there are more songs in the sequence
                if lines_printed == max_lines and i < len(self.sequence) - 1:
                    print("...")
                    break
                else:
                    print(f"{'-  ' : <{max_index_len + 2}}{color(self.sequence[i], SongAttributes.sequenced.value)}")
            
            if lines_printed < max_lines:
                # Print the queue
                for i in range(len(self.queue_song_names)):
                    lines_printed += 1 # Prematurely add one, since each branch in the following "for" is guaranteed to print 1 line
                    
                    # If this is the last available line and there are more songs in the queue
                    if lines_printed == max_lines and i < len(self.queue_song_names) - 1:
                        print("...")
                        break
                    else:
                        print(f"{f'{i + 1}. ' : <{max_index_len + 2}}{color(self.queue_song_names[i], SongAttributes.queued.value)}")

            return lines_printed # lines_printed will not exceed max_lines
    
    def display_help(self) -> None:
        print("Available commands (in blue)")
        print(f"{color('-' * (get_terminal_size().columns - 8), Colors.faint)}")
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
    {color('*')}: enqueue a placeholder song based on the current playback mode
{color('modifiers')}: list the active modifiers and optionally remove one more more modifiers
{color('sequence')}: add a new sequence to a song or edit an existing one
{color('q')} or {color('quit')}: return to {color('and update', Colors.bold)} the menu
{color('autoupdate')} or {color('standby')}: enables automatic updating of song info in the menu
Playback modes:
    {color('repeat')}: repeat the current song indefinitely
    {color('loop')}: loop through the playlist from the current song
    {color('shuffle')}: randomly select a song from the playlist
{color('disable')}: stop this song from being automatically chosen by loop or shuffle mode   [{color('Only available when displaying song options', Colors.orange)}]
{color('enable')}: undo the 'disable' command for the selected song   [{color('Only available when displaying song options', Colors.orange)}]
{color('karaoke')}(🎤): turn on lyrics for this song   [{color('Press any key to exit karaoke mode', Colors.green)}]
{color('encore')}(🔁): repeat the current song one more time
{color('pause')}: pause the music player
{color('resume')}: resume the music player {color("and restart the current song", Colors.underline)}
{color('skip')} or [{color('>>')}]: skip the current song and play another one
{color('<song name>')}: list the available actions and modifiers for this song
[{color('exit')}] or [{color('stop')}]: terminate the program
{color('exit later')}(⌛): terminate the program after the current song ends   [{color('Enter this command again to cancel it', Colors.green)}]""")

        print()
        self.input_command(input("Enter a command: "))
    def display_keybinds(self) -> None:
        clear_console()
        hide_cursor()

        # List the active keybinds
        print("Available key inputs:", end = "\n\n")
        for key in Keybind.active_keys:
            print(Keybind.directory[key])
        print("Press any unmapped key to return", end = "\n\n")

        print("Press a key to continue: ")
        self.get_key_command()
        if not self.run_key_command(): # If the entered key is not a keybind, return to the standby mode
            self.autoupdate_ui()

    # Takes in the user's input and tries to find a corresponding command with list_actions()
    # Won't directly print anything
    def input_command(self, user_input:str, index_search_enabled:bool = True) -> None:
        if user_input == "" or user_input == "q" or user_input == "quit":
            valid_commands["quit"](self)
        else:
            result:Item = self.list_actions(search_lists(search = user_input, lists = initial_results(section("Commands:", list(valid_commands.keys()), items_type = ItemType.Command), section("Songs:", self.song_names, items_type = ItemType.Song), section("", [PLACEHOLDER_SONGNAME], items_type = ItemType.Hidden)), index_search_enabled = index_search_enabled, include_result_type = True))
            if result == ReturnFlags.UnrecognizedInput:
                # The "no results" message would've already been printed by self.list_actions()
                self.update_ui()
            elif result.name == PLACEHOLDER_SONGNAME:
                self.enqueue()
            elif result.name in self.song_names:
                self.list_song(result.name)
            else:
                self.handle_invalid_result()

    # Intended to be called from an input listener thread
    # Uses getch() to wait for a character input. If a valid key command is entered, store it in self.key_command_buffer
    def get_key_command(self) -> None:
        key:str = str(getch(), encoding = "utf-8")
        self.key_command_buffer = key
        # Since self.get_key_command() is intended to be called in a listener thread, don't run the binded function from here
    # Intended to be called from the console thread
    # Clears self.key_command_buffer and runs the function that was binded to the key
    # returns True if a keybind binded ot the key in self.key_command_buffer exists and is active, False otherwise
    def run_key_command(self) -> bool:
        key = self.key_command_buffer
        self.key_command_buffer = None # Reset the buffer in case the binded function also needs to use it
        return Keybind.run_keybind(key)
    
    # Returns a string that explains what each song color means in a colored list of songs
    # print_list is the list that the key is for
    # Key will only include the colors that will appear in print_list
    # Commands will always be colored blue
    def get_color_key(self, print_list:"list[Item]") -> str:
        print_list:set[str] = {item.name for item in print_list}
        # List and sets can't be keys in a dictionary
        self.listing_colors[SongAttributes.playing]["nameset"] = {self.curr_song.song_name} # Since song_name is a primitive and doesn't have a reference, it needs to be updated before printing
        # Create a new list of coloring attributes to keep the relative order of each attribute the same every time
        # Also excludes SongAttributes.modifiers to be handled individually
        info:list[dict[str, any]] = [self.listing_colors[SongAttributes.playing],
                                    self.listing_colors[SongAttributes.disabled],
                                    self.listing_colors[SongAttributes.queued],
                                    self.listing_colors[SongAttributes.sequenced]]
        key:str = ""

        for attribute in info:
            if attribute["enabled"] and len(set(attribute["nameset"]) & print_list) > 0:
                if key: # If there is already something in the key
                    key += " | "
                key += f"{color(attribute['message'], attribute['color'])}"

        if self.listing_colors[SongAttributes.modifiers]["enabled"]:
            for modifier, modifier_list in self.modifiers.items():
                if len(set(modifier_list) & print_list) > 0: # If a song with the modifier is in print_list
                    if key: # If there is already something in the key
                        key += " | "
                    key += f"{color(modifier.name, modifier.value['color'])}"

        if len(key) > 0:
            key = "Key: " + key

        return key
    
    # Wrapper function for list_actions_recursive()
    # results must be in the order of [commands, modifiers, songs]
    # results_lists can also be a tuple in the form (list of sublists' tuples, SearchResultType)
    # Header lines from self.listing_info will not print if autoclear_console == False
    def list_actions(self, results_lists:"list[tuple[str, list[Item]]]", list_type:ListModes = ListModes.Default, listing_item_name:str = None, autoclear_console:bool = True) -> "Union(Item, bool)":
        return self.list_actions_recursive(results_lists, list_type = list_type, listing_item_name = listing_item_name, autoclear_console = autoclear_console, special_commands = None)
    def list_actions_recursive(self, results_lists:"list[tuple[str, list[Item]]]", list_type:ListModes = ListModes.Default, listing_item_name:str = None, autoclear_console:bool = True, special_commands:"dict[str, dict[str, function]]" = None) -> "Union(Item, bool)":
        if autoclear_console:
            clear_console()
        if not special_commands:
            special_commands = self.listing_info[list_type]["special commands"] # Each key is the name of the command, and the value is a dict where "confirmation" is the function that asks the user to confirm (None if no confirmation needed) that returns True/False, and "action" is the function to run if the user confirms

        # result_type defaults to SearchResultType.Exact
        results_lists, results_type = results_lists if type(results_lists) == tuple else (results_lists, SearchResultType.Exact) # results_lists will automatically unpack if it's a tuple
        # Mark the listed numbers before which separators should be placed
        results:list[Item] = []
        separators_directory:dict[int, str] = {}
        curr_index:int = 0
        for separator, separated_list in results_lists:
            results += separated_list
            separators_directory[curr_index] = separator if separator else "----------"
            curr_index += len(separated_list)
        if len(separators_directory) == 1:
            separators_directory.clear() # No need to use separators between each section if there is only 1 section
        
        # Handle cases where there are no valid results
        # Returns None when program ends
        if len(results) == 0:
            print(self.listing_info[list_type]["no results"]["message"])
            block_until_input()
            no_results_return:any = self.listing_info[list_type]["no results"]["action"](listing_item_name)
            # Return any UnrecognizedInput flags to the previous recursive call to re-prompt the user for input
            return (no_results_return if no_results_return == ReturnFlags.UnrecognizedInput else None)

        elif len(results) == 1: # Something is guaranteed to be returned here if there is only 1 item in results
            result:Item = results[0]
            if results_type == SearchResultType.Fuzzy:
                clear_console()
                print(f"- {color(result.name, Colors.bold)}", end = "\n\n")
                if not confirmation(message = "Is this what you meant?"): # Skip past this block of code if the user confirms
                    self.listing_info[list_type]["no results"]["action"](listing_item_name)
                    return

            if result.name in special_commands:
                # The functions in special_commands either have no parameters or a parameter called "song_name"
                # listing_item_name will be None if list_type is Modifiers, so the remove_modifiers method would still clear all modifiers
                if (not special_commands[result.name]["confirmation"]) or special_commands[result.name]["confirmation"](): # If there isn't a confirmation step or if the user confirms
                    # Uncomment after testing
                    #try:
                    return special_commands[result.name]["action"](song_name = listing_item_name)
                    # except:
                    #     # Remove after testing
                    #     print(f"Error on call to command: {result.name}")
                    #     block_until_input()
                    #     return special_commands[result.name]["action"]()
                else: # If the user doesn't confirm
                    return listmode_actions[list_type](self)

            elif result.name in valid_commands:
                return valid_commands[result.name](self)

            else:
                return result

        # If more than 1 result
        for color_key in self.listing_colors:
            if color_key in self.listing_info[list_type]["disabled color keys"]:
                self.listing_colors[color_key]["enabled"] = False
            else:
                self.listing_colors[color_key]["enabled"] = True

        color_key:str = self.get_color_key(results)

        header_line:str = self.listing_info[list_type]["header line"]
        if not autoclear_console:
            header_line = ""

        max_digits:int = len(str(results[-1].id))

        # List all the results
        # These 5 variables are only used when the list type is ListModes.Queue
        max_sequence_digits:int = len(str(len(self.sequence)))
        overflow_chars = "---" # Used when more than 1 color applies to the same song. Also used to adjust the left margin
        padding:str = " " * 3
        sequence_separator:str = color(f"{padding}|{padding}", Colors.faint)
        left_margin:int = max(len(header_line), (max_digits + 2) + 1 + self._max_song_name_length + (len(overflow_chars) * 2) + 1 + 5) # 5 extra spaces for the duration display of each song
        
        sequence_count:int = 1
        def get_sequence_line(sequence_count:int) -> str:
            if sequence_count <= len(self.sequence):
                seq_song:Song = self.songs[self.sequence[sequence_count - 1]]
                return (sequence_separator + color(f"{str(sequence_count) + '. ' : <{max_sequence_digits + 2}}", Colors.faint) + color(seq_song.song_name, Colors.yellow) + f" {color('-' * (self._max_song_name_length - len(seq_song.song_name) + 1), Colors.faint)} {color(to_minutes_str(seq_song.duration), Colors.cyan)}")
            else:
                return ""

        while True: # Broken by the "return" at the bottom of this function once a valid input is detected
            sequence_count = 1

            if list_type == ListModes.Queue: # Formats and prints the header lines and the color key
                print(f"{header_line : <{left_margin}}{sequence_separator}", end = "")
                if len(self.sequence) > 0:
                    print(f"Active sequence (not selectable)")
                else:
                    print("No active sequence")

                if len(color_key) > 0:
                    print(f"{color_key : <{left_margin + (len(color_key) - len(remove_tags(color_key)))}}", end = "")
                    
                    if len(self.sequence) > 0:
                        print(sequence_separator)
                    else:
                        print()
            else:
                if list_type == ListModes.Song:
                    header_line = header_line.format(song_name = color(listing_item_name, Colors.bold))

                if header_line:
                    print(header_line)
                if len(color_key) > 0:
                    print(color_key)

            if results_type == SearchResultType.Fuzzy:
                print(SearchResultType.Fuzzy.value)

            # Print all the results
            commands_count:int = 0 # Used for determining the index of the removing song in self.queue_song_names when list_mode is Queue and the user input is a valid index
            for index in range(len(results)):
                # Print the separator (if there is one at this index)
                if index in separators_directory:
                    separator:str = separators_directory[index] # The uncolored separator string
                    print(f"{color(separator, Colors.faint) + (' ' * (left_margin - len(separator)))}", end = "")
                    if list_type == ListModes.Queue:
                        print(get_sequence_line(sequence_count), end = "")
                        sequence_count += 1
                    print()

                result = results[index]
                line:str = f"{str(index + 1) + '.' : <{max_digits + 1}} "
                if result.item_type == ItemType.Command: # The command results will always be first in the list
                    line += f"{color(result.name)}"
                    commands_count += 1
                
                elif result.item_type == ItemType.Modifier:
                    try:
                        modifier:Modifiers = Modifiers[result.name] # Will error if the result isn't the name of a modifier
                        if list_type == ListModes.Modifiers:
                            line += f"{color(result.name, modifier.value['color'])}{color('  - ' + modifier.value['description'], Colors.faint)}"
                            for modified_song_name in self.modifiers[modifier]:
                                line += f"\n{' ' * max(max_digits + 2, 4)}{color('|', Colors.faint)}{modified_song_name}"
                        elif list_type == ListModes.Song:
                            action_type:str = "(remove)" if len({modifier} & self.songs[listing_item_name].attributes[SongAttributes.modifiers]) == 1 else "(add)"
                            line += f"{color(result.name, modifier.value['color'])} {color(action_type, Colors.faint)}"
                        else:
                            continue

                        commands_count += 1
                    except:
                        pass

                elif result.item_type != ItemType.Hidden: # If this result isn't a command or modifier, then assume all subsequent results are songs
                    if result.name == PLACEHOLDER_SONGNAME: # Can only show up in results if list_actions was used (when listing the queue or when there's no listing mode)
                        line += result.name

                    else:
                        result_song:Song = self.songs[result.name]
                        # THIS IS THE PINNACLE OF UI DESIGN
                        applied_colors:list[Colors] = []
                        for attribute, attribute_colors in result_song.get_listing_colors():
                            if self.listing_colors[attribute]["enabled"]:
                                applied_colors += attribute_colors
                        
                        overflow_dashes = ""
                        colored_name:str = result.name
                        if len(applied_colors) > 0:
                            colored_name = color(colored_name, applied_colors[0])
                            del applied_colors[0]
                        for curr_color in applied_colors:
                            overflow_dashes += color(overflow_chars, curr_color)

                        # I can't explain how this line works even if I try
                        line += f"{colored_name} {overflow_dashes}{color('-' * (self._max_song_name_length - result.display_length - len(applied_colors)*len(overflow_chars) + (len(Modifiers) + len(self.listing_colors) - 1)*len(overflow_chars)), Colors.faint)} {color(to_minutes_str(self.songs[result.name].duration), Colors.cyan)}"
                        if list_type == ListModes.Sequences:
                            for song_name in self.sequences.get(result.name, []):
                                line += f"\n{' ' * max(max_digits + 2, 4)}{color('|', Colors.faint)}{song_name}"

                if line: # Don't do anything if line is an empty string
                    print(f"{line : <{left_margin + (len(line) - len(remove_tags(line)))}}", end = "")
                    if list_type == ListModes.Queue:
                        # "Attach" the line in the sequence's list onto a line in the list of commands
                        print(get_sequence_line(sequence_count), end = "")
                        sequence_count += 1

                    print()

            # Print any more songs in the sequence that didn't get attached to the end of a "queued song" line
            if list_type == ListModes.Queue:
                sequence_line:str = get_sequence_line(sequence_count)
                while sequence_line:
                    print(f"{' ' * left_margin}{sequence_line}")
                    sequence_count += 1
            print()

            # After printing all the results
            user_input:str = input(self.listing_info[list_type]["prompt"])
            if user_input == "": # Return to home screen unless list_type is ListMode.ListCreation
                return self.listing_info[list_type]["no input"](self) # Guaranteed to return None (or False if in ListMode.ListCreation)
            elif user_input == "q" or user_input == "quit": # Return to home screen
                return valid_commands["quit"](self) # Guaranteed to return None

            elif list_type == ListModes.Song and user_input.isspace():
                return self.enqueue(song_name = listing_item_name) # Guaranteed to return None

            # Search recursively until the user quits or narrows the search down to 1 or 0 possible result(s)
            selected_value:any = self.list_actions_recursive(search_lists(search = user_input, lists = results_lists, index_search_enabled = True, include_result_type = True), list_type = ListModes.Default, listing_item_name = listing_item_name, special_commands = special_commands)
            if selected_value != ReturnFlags.UnrecognizedInput:
                return selected_value
            else:
                # The "no results" message would've been printed by the next recursive call
                # Re-list everything listed by this current function call on the next iteration of the loop
                if autoclear_console:
                    clear_console()

    def handle_invalid_result(self):
        clear_console()
        print(f"{color('Invalid result!', Colors.red)}\nPlease check your spelling and/or capitalization")
        block_until_input()
        self.update_ui()

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
                        "sequences" : list_sequences,
                        "q" : update_ui,
                        "quit" : update_ui,
                        "repeat" : set_mode_repeat,
                        "loop" : set_mode_loop,
                        "standby" : autoupdate_ui,
                        "autoupdate" : autoupdate_ui,
                        "shuffle" : set_mode_shuffle,
                        "stop" : stop,
                        "exit" : stop,
                        "exit later" : delayed_exit
                        }

    global exact_commands
    exact_commands = {"stop", "exit", "exit later", ">>"} # Can only contain commands in valid_commands


clear_console() # Clears any "hide cursor" characters in the console
hide_cursor()

# For the funnies
intro_enabled:bool = False # Enable or disable the intro bit
if intro_enabled:
    wait(0.9)
    print("\"Mom can we have Spotify?\"")
    wait(1)
    print("Mom: no, we have Spotify at home")
    wait(2)

    clear_console()
    # Will all be cleared once spotify initializes and the console clears when the first song plays
    wait(0.3)
    print(f"spotify at home {color('Sqotify Inc., At home, ©2023 No Rights Reserved', Colors.faint)}")
    wait(1.9)

DIRECTORY:str = "songs/" # Every file in this directory must be a playable wav file except the file with song_instructions_file_name
songs:"dict[str, Song]" = {}
song_names:"list[str]" = []
alert:bool = False
file_names:"list[str]" = listdir(DIRECTORY)
SONGS_INSTRUCTIONS_FILE_NAME:str = "read_this.txt" # This text file must be in the "songs" directory
try:
    file_names.remove(SONGS_INSTRUCTIONS_FILE_NAME)
except:
    print(color("Instructions file not found in songs!", Colors.red))
    alert = True

for file_name in file_names:
    if file_name[len(file_name) - 4 : ] != ".wav":
        alert = True
        print(color(f"The file \"{file_name}\"\'s name doesn't end with \".wav\", but it was added to the playlist anyway", Colors.yellow))
    
    song_name:str = file_name.replace(".wav", "")
    try: # Will error if the song name can't be casted to an int
        if int(song_name) <= len(valid_commands.keys()) + len(song_names) + 1: # Additionally, only raise an alert if the casted index is valid
            alert = True
            print(color(f"{song_name} dropped due to name overlap with existing index!", Colors.red))
            continue # Avoid the "finally" block of code
        # If the number converted from the song name is not a valid index, the song will be added in the "finally" block
    except:
        if (song_name in valid_commands.keys()) or song_name == "clear" or song_name == PLACEHOLDER_SONGNAME or song_name == "": # Filter out any songs with the same name as a command
            alert = True
            print(color(f"{file_name} dropped due to name overlap with existing command!", Colors.red))
        else:
            songs[song_name] = Song(song_name, f"{DIRECTORY}{file_name}")
    finally:
        song_names.append(song_name)    

if alert: # Prevent the "song dropped" messages from being instantly cleared from the console
    print()
    block_until_input()


player = spotify(songs, song_names)

def play():
    player_thread:Thread = Thread(target = player.start, name = "Console", daemon = True)
    player_thread.start()

    player.interlude_flag = False # Disable the waiting period before the first song
    while True:
        if player.playing:
            player.play_next_song() # Yields within 1.5 seconds after the player is paused
        else:
            wait(TICK_DURATION) # Wait and check whether the user has resumed the player

music_thread:Thread = Thread(target = play, name = "Audio player", daemon = True)
music_thread.start()

while not player.terminated: # Yields once the user exits the music player, killing every thread
    wait(TICK_DURATION)
