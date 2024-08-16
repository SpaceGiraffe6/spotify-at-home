from enum import Enum
from time import sleep as wait, time
from os import listdir, get_terminal_size
from winsound import PlaySound, SND_ASYNC
from threading import Thread
from random import randint
from difflib import get_close_matches
from math import ceil
from typing import Union
import json

from song import Song
from info import LYRIC_PLACEHOLDER_CHARACTER, TICK_DURATION, TIMER_RESOLUTION, Modifiers, Colors, SongAttributes, EXCLUSIVE_MODIFIERS, MODIFIERS_COLORING_ORDER, ATTRIBUTES_COLORING_ORDER
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
    confirmed:bool = False
    if user_input == "" or user_input.lower().startswith("y"): # Returns True if user inputs nothing
        confirmed = True
    else:
        print("\nAction cancelled!")
        block_until_input()
    print()
    return confirmed

# Helper class for search_lists
class SearchResultTypes(Enum):
    Exact = f"*Results are exact matches*"
    Fuzzy = f"*Results are {color('not', Colors.underline)} exact matches*" # Only the message for Fuzzy is used (in list_actions)
# Returns [search] if search is an empty string
# Returns an empty list if nothing in each search list matches the search term
# If include_result_type is True, then search_lists will return a tuple in the form (SearchResultTypes, searched lists)
    # The SearchResultType value tells you whether the returned results for each list were obtained using exact matching or a fuzzy search
def search_lists(search:str, lists:"list[tuple[str, list[str]]]", index_search_list:"list[str]" = None, include_result_type:bool = False) -> "list[tuple[str, list[str]]]":
    if not search: # If search is an empty string
        return [search]

    # Does nothing if the search term is not a number or if index_search_list is not a list
    try:
        index = int(search) - 1
        if index_search_list == []:
            for _, sublist in lists:
                index_search_list += sublist
        
        if index < len(index_search_list): # Errors if index_search_list isn't a list
            return [("", [index_search_list[index]])] # Artificially create a sublist to avoid errors in list_actions()
    except:
        pass
    
    results_lists:dict[SearchResultTypes, list[tuple[str, list[str]]]] = {result_type : [] for result_type in SearchResultTypes}
    for list_name, sublist in lists:
        sublist_results, result_type = search_for_item(search = search, search_list = sublist, index_search_list = None, include_result_type = True)
        if len(sublist_results) > 0:
            results_lists[result_type].append((list_name, sublist_results))

    results, result_type = (results_lists[SearchResultTypes.Exact], SearchResultTypes.Exact) if len(results_lists[SearchResultTypes.Exact]) > 0 else (results_lists[SearchResultTypes.Fuzzy], SearchResultTypes.Fuzzy)
    if include_result_type:
        return (results, result_type)
    return results
# Set index_search_list to something that's not a list to disable index search. If it's not specified, then it will automatically try to index search the search_list
# Relative order of items in search_list will be kept the same
def search_for_item(search:str, search_list:"list[str]", index_search_list:"list[str]" = [], include_result_type:bool = False) -> "list[str]":
    if not search: # If search is an empty string
        return [search]

    try:
        # Errors if the search term is not a number or if index_search_list is not a list
        index = int(search) - 1
        if index_search_list == []:
            index_search_list = search_list
        
        if index < len(index_search_list):
            return [index_search_list[index]]
    except:
        pass

    search = search.strip().lower()

    search_pairs:list[tuple[str, str]] = [(item[:len(search)].lower(), item) for item in search_list if item not in exact_commands] # Tuples in the format of (name of item cut down to not exceed the length of the search term , original name of the item)
    result_type:SearchResultTypes = SearchResultTypes.Exact
    results:list[str] = [name for short_name, name in search_pairs if short_name == search] # Add in the exact matches
    if search in exact_commands:
        results.insert(0, search) # Put the exact command result (if there is one) at the front of the list of results
    
    # If the user made a typo in the search and no matches were found
    if len(results) == 0:
        shortened_results:list[str] = get_close_matches(search, [short_name for short_name, *_ in search_pairs]) # The higher the cutoff parameter (between 0 and 1), the stricter the search will be
        results = [name for short_name, name in search_pairs if short_name in shortened_results]
        result_type = SearchResultTypes.Fuzzy
    
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
def initial_results(*sections:"tuple[tuple[str, list[str]]]") -> "list[tuple[str, list[str]]]":
    return list(sections)
# Only used to create and format individual sublists when passing a list of results to list_actions
def section(header:str, items:"list[str]") -> "tuple[str, list[str]]":
    return (header, items)

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

class spotify:
    # Constants
    COOLDOWN_BETWEEN_SONGS:int = 8 # Seconds
    # When the playback mode is shuffle, the minimum number of songs that would have to play between each repeat
    COOLDOWN_BETWEEN_REPEATS:int = 5 # Will be capped at len(playlist) - 1 by the constructor
    
    SAVE_FILE_PATH:str = "save_file.json"

    def __init__(self, songs:dict, song_names:list): # Passes song_names in as an argument to keep the order of the names the same each time the code runs
        save_file:dict[str, any] = {}
        try:
            with open(self.SAVE_FILE_PATH, "r") as file:
                save_file = json.load(file)
        except:
            pass

        self.songs:dict[str, Song] = songs # Keys are the name of the song
        self.song_names:list[Song] = song_names
        self._max_song_name_length:int = 0
        for name, song in self.songs.items(): # Set the parent player of the song objects
            if len(name) > self._max_song_name_length:
                self._max_song_name_length = len(name)
            if name in save_file.get("sequences", {}):
                song.update_sequence(save_file["sequences"][name])

            song.set_player(self)
        # For safe measure
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
            if song_name == "*":
                self.queue.append(None)
                self.queue_song_names.append("*")

            elif song_name in self.song_names:
                self.queue.append(self.songs[song_name])
                self.queue_song_names.append(song_name)

        # Modifiers that are hard-coded to songs here will be added to the saved modifiers
        self.modifiers:dict[Modifiers, list[str]] = {Modifiers.hot : [], Modifiers.cold : []}
        # Fills in any modifiers not covered by the hard-coded modified songs or the modifiers in the save file
        for modifier in Modifiers:
            self.modifiers.setdefault(modifier, [])
            if "modifiers" in save_file:
                self.modifiers[modifier].extend(save_file["modifiers"][modifier.name])

            # Add this modifier to the songs that are initialized with the modifier
            # Temporarily set the synced count of all songs to 1
            for song in [self.songs[song_name] for song_name in self.modifiers[modifier]]:
                song.attributes[SongAttributes.modifiers].add(modifier)
        for song in self.songs.values():
            song.recalculate_weight(1)

        self.synced_songs:dict[str, list[str]] = {}
        for song_name in self.modifiers[Modifiers.synced]:
            pure_song_name:str = get_pure_song_name(song_name)
            self.synced_songs.setdefault(pure_song_name, [])
            self.synced_songs[pure_song_name].append(song_name)

        # Update the synced count of all synced songs
        for synced_list in self.synced_songs.values():
            for song_name in synced_list:
                self.songs[song_name].add_modifiers(synced_songs_count = len(synced_list))

        self.sequences:dict[str, list[str]] = save_file.get("sequences", {})

        self.remaining_interlude_indicator:str = "" # Indicates how much time is left for the cooldown period between this song and the next one
        self.COOLDOWN_BETWEEN_REPEATS:int = min(len(self.song_names) - 1, self.COOLDOWN_BETWEEN_REPEATS)
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
                "prompt" : f"Enter the index or the name of the song to view ({color('q')}/{color('quit')} to cancel): "
            },
            ListModes.Queue : {
                "header line" : f"Select a command, or a song to remove from the queue",
                "special commands" : {"clear" : {"confirmation" : confirmation, "action" : self.clear_queue}},
                "no results" : {"message" : "No songs found! Please check your spelling", "action" : self.list_queue},
                "disabled color keys" : [SongAttributes.playing, SongAttributes.disabled, SongAttributes.sequenced, SongAttributes.modifiers],
                "prompt" : f"Enter the index or the name of the song to remove ({color('q')}/{color('quit')} to cancel, {color('clear')} to clear queue): "
            },
            ListModes.Modifiers : {
                "header line" : f"Select a modifier to remove it from all songs, or select a song to remove all modifiers from that song",
                "special commands" : {"clear" : {"confirmation" : confirmation, "action" : self.remove_modifier}},
                "no results" : {"message" : "No modifier found! Please check your spelling", "action" : self.list_active_modifiers},
                "disabled color keys" : [SongAttributes.playing, SongAttributes.disabled, SongAttributes.queued, SongAttributes.sequenced],
                "prompt" : f"Select a modifier to clear that modifier select a song to clear all of its modifiers ({color('clear')} to clear all modifiers): "
            },
            ListModes.Song : {
                "header line" : "Select a command to run or a modifier to add/remove for {song_name}",
                "special commands" : {"clear" : {"confirmation" : None, "action" : self.remove_modifier},
                                        "enqueue" : {"confirmation" : None, "action" : self.enqueue},
                                        "disable" : {"confirmation" : None, "action" : self.disable_song},
                                        "enable" : {"confirmation" : None, "action" : self.enable_song}},
                "no results" : {"message" : "No results found! Please check your spelling", "action" : self.list_song},
                "disabled color keys" : [],
                "prompt" : f"Select a modifier ({color('clear')} to clear all modifiers from this song, or {color('[space]')} to enqueue): "
            },
            ListModes.ListCreation : {
                "header line" : f"Add an item to the list",
                "special commands" : {"change" : {"confirmation" : None, "action" : lambda:-1}, "finish" : {"confirmation" : None, "action" : lambda:True}},
                "no results" : {"message" : "No results found! Please check your spelling", "action" : lambda:None},
                "disabled color keys" : [],
                "prompt" : f"Enter the index(es) of the item(s) to add, separated by commas ({color('q')}/{color('quit')} to cancel and return to home screen): "
            },
            ListModes.Sequences : {
                "header line" : f"Select a numbered song to view its sequence",
                "special commands" : {"new" : {"confirmation" : None, "action" : self.create_sequence}, "clear" : {"confirmation" : confirmation, "action" : lambda:[self.clear_sequence(lead_song_name) for lead_song_name in self.sequences.keys()]}},
                "no results" : {"message" : "No results found! Please check your spelling", "action" : self.list_sequences},
                "disabled color keys" : [SongAttributes.sequenced],
                "prompt" : f"Enter the index or name of a song ({color('new')} to create a new sequence, {color('clear')} to clear all sequences): "
            },
            ListModes.Sequence : {
                "header line" : f"Select any existing song to add/remove it to/from the sequence",
                "special commands" : {"clear" : {"confirmation" : confirmation, "action" : self.clear_sequence}},
                "no results" : {"message" : "No results found! Please check your spelling", "action" : self.update_ui},
                "disabled color keys" : [],
                "prompt" : f"Enter the index or name of a song ({color('clear')} to remove the whole sequence): "
            },
            None : {
                "header line" : f"Which one do you mean?",
                "special commands" : {},
                "no results" : {"message" : "No results found! Please check your spelling", "action" : self.update_ui},
                "disabled color keys" : [],
                "prompt" : f"Enter the index or the name of the result ({color('q')}/{color('quit')} to cancel): "
            }}
        self.listing_colors:dict[str, bool] = {SongAttributes.playing : {"enabled" : True, "color" : SongAttributes.playing.value, "nameset" : None, "message" : "Currently playing"},
                                                SongAttributes.disabled : {"enabled" : True, "color" : SongAttributes.disabled.value, "nameset" : self.disabled_song_names, "message" : "Disabled"},
                                                SongAttributes.queued : {"enabled" : True, "color" : SongAttributes.queued.value, "nameset" : set(self.queue_song_names), "message" : "Queued"},
                                                SongAttributes.sequenced : {"enabled" : True, "color" : SongAttributes.sequenced.value, "nameset" : set(self.sequences.keys()), "message" : "Has sequence"},
                                                SongAttributes.modifiers : {"enabled" : True, "color" : None}}

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
            block_until_input(message = "Press enter to exit")
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

        with open(self.SAVE_FILE_PATH, "w") as save_file:
            json.dump(data, save_file, indent = 4)
    
    # Stops execution of the player's thread
    def stop(self) -> None:
        clear_console()
        self.save()
        print("Program terminated via command!")
        self.terminated = True # Will break the loop propping up the main thread (at the end of the script)
        exit() # Kill this thread so the rest of the code won't keep running if stop() was called from list_actions()
    # Stops the program after the current song ends
    def delayed_exit(self) -> None:
        self.exit_later = not self.exit_later
        self.update_ui()

    def create_list(self, selection_pool:"list[any]", header_line:str = "") -> Union[list, None]:
        # selection_pool:list[any] = selection_pool.copy()
        # created_list:list[any] = []
        # while selection_pool:
        #     clear_console()
        #     if not header_line:
        #         header_line = self.listing_info[ListModes.ListCreation]["header line"]
        #     print(header_line)
        #     print(f"Selected items: {str(created_list)}")

        #     result:str = self.list_actions(["q", "quit", "change", "finish"] + selection_pool, list_type = ListModes.ListCreation, autoclear_console = False)
        #     if result == None: # If the user cancels the list creation
        #         return None
        #     elif result == True: # If the user uses the special command "finish"
        #         return created_list
        #     elif result == -1: # If the user goes back to change the last value in the created list
        #         if len(created_list) > 0:
        #             selection_pool.append(created_list[-1])
        #             del created_list[-1]
        #         else:
        #             print("\nThere are no previous items!")
        #             block_until_input()
        #     else: # If the user chooses something from the selection pool (all command inputs will be handled by list_actions)
        #         created_list.append(result)
        #         selection_pool.remove(result)

        # if len(selection_pool) == 0:
        #     return created_list

        if not header_line:
            header_line = self.listing_info[ListModes.ListCreation]["header line"]

        enabled_commands:list[str] = ["q", "quit"]
        while True:
            clear_console()
            print(header_line)
            result_string:str = self.list_actions(initial_results(section("Commands:", enabled_commands), section("Available selection:", selection_pool)), list_type = ListModes.ListCreation, autoclear_console = False)

            if result_string:
                created_list:list[str] = []
                try: # Errors if one of the results can't be casted to an int
                    results:list[int] = [int(result) - len(enabled_commands) - 1 for result in result_string.replace(" ", "").split(",")]
                    for index in results:
                        if index >= 0 and index < len(selection_pool):
                            created_list.append(selection_pool[index])
                        else:
                            raise NotImplementedError

                    return created_list # The function calling this create_list will handle cases where length of created_list is 0
                finally:    
                    print("\nInvalid list item!")                      
                    block_until_input()

    def create_sequence(self) -> None:
        valid_song_names:list[str] = [song_name for song_name in self.song_names if song_name not in self.sequences]
        lead_song_name:str = self.list_actions(initial_results(section("Commands:", ["q", "quit"]), section("Songs:", valid_song_names)), ListModes.Songs)
        if lead_song_name:
            if lead_song_name in valid_song_names:
                valid_song_names.remove(lead_song_name)
                sequence:list[str] = self.create_list(valid_song_names, header_line = f"Creating a sequence for {color(lead_song_name, Colors.bold)}")
                if sequence != None: # If the user didn't cancel
                    clear_console()
                    if len(sequence) > 0:
                        self.songs[lead_song_name].update_sequence(sequence)
                        self.sequences[lead_song_name] = sequence
                        
                        print(f"Added {fix_grammar(sequence, Colors.bold)} to the sequence of {color(lead_song_name, SongAttributes.sequenced.value)}")
                        block_until_input()
                        self.update_ui()
                    else:
                        print(color("No songs were added to the new sequence!", Colors.red))
                        block_until_input()
                        self.list_sequences()

            else:
                self.handle_invalid_result()
        # Do nothing if list_actions returns None

    def list_sequences(self, *_) -> None:
        result:str = self.list_actions(initial_results(section("Commands:", ["q", "quit", "new"]), section("Sequences", list(self.sequences.keys()))), list_type = ListModes.Sequences)
        if result in self.sequences.keys(): # If result isn't None
            self.list_sequence(result)

    def list_sequence(self, song_name:str, *_) -> None:
        sequence:list[str] = self.sequences[song_name]
        result:str = self.list_actions(initial_results(section("Commands:", ["q", "quit", "clear"]), section("Sequence:", sequence)), list_type = ListModes.Sequence, listing_item_name = song_name)
        if result == None:
            return

        clear_console()
        if result in sequence:
            if len(sequence) == 1:
                self.clear_sequence(result)
            else:
                sequence.remove(result)
            print(f"Removed {color(result, Colors.bold)} from the sequence of {color(song_name, SongAttributes.sequenced.value)}")

        elif result in self.song_names:
            sequence.append(result)
            print(f"Added {color(result, Colors.bold)} to the sequence of {color(song_name, SongAttributes.sequenced.value)}")

        block_until_input()
        self.update_ui()

    def clear_sequence(self, song_name:str, silent:bool = False) -> None:
        del self.sequences[song_name]
        self.songs[song_name].attributes[SongAttributes.sequenced] = False

        if not silent:
            clear_console()
            print(f"Cleared the sequence of {color(song_name, Colors.bold)}")
            block_until_input()
            self.update_ui()

    def enqueue(self, song_name:str = None) -> None:
        if song_name:
            self.queue.append(self.songs[song_name])
            self.queue_song_names.append(song_name)
            self.songs[song_name].attributes[SongAttributes.queued] = True

            clear_console()
            print(f"{color(song_name, Colors.purple)} added to queue!")
            block_until_input()
        else: # Enqueue a placeholder song
            self.queue.append(None)
            self.queue_song_names.append("*")
            clear_console()

        self.update_ui()

    def clear_queue(self) -> None:
        for item in self.queue:
            if item: # item will be None if the song is a placeholder
                item.attributes[SongAttributes.queued] = False
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
        if song_name != "*" and (song_name not in self.queue_song_names): # Only set the queued attribute to False if no more occurrences of this song remain in the queue after this removal
            self.songs[song_name].attributes[SongAttributes.queued] = False

        return song_name
    
    def list_queue(self, *_) -> None:
        if len(self.queue) > 0 or len(self.sequence) > 0:
            list_type:ListModes = ListModes.Queue
            result:str = self.list_actions(initial_results(section("", ["q", "quit", "clear"]), section("", self.queue_song_names)), list_type = list_type) # Don't include headers for each section in case they mess up the formatting of the active sequence
            if result and (result in self.queue_song_names):
                self.remove_queued_item(song_name = result)
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
            result:str = self.list_actions(initial_results(section("Commands:", ["q", "quit", "clear"]), section("Modifiers", active_modifier_names), section("Modified songs:", modified_song_names)), list_type = list_type)
            if result:
                if (result in active_modifier_names):
                    self.remove_modifier(modifier = Modifiers[result])
                elif result in modified_song_names_set:
                    self.remove_modifier(song_name = result)
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
        removals:int = 0
        message:str = ""
        if not modifier:
            if song_name:
                active_modifiers:set[Modifiers] = self.songs[song_name].attributes[SongAttributes.modifiers]
            
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

                active_modifiers.clear() # active_modifiers has the same reference to the list of modifiers in the song

            else: # If no song name or modifier is specified
                for modifier_list in self.modifiers.values():
                    removals += len(modifier_list)
                    for song_name in modifier_list:
                        self.songs[song_name].clear_modifiers()
                    modifier_list.clear()

                self.synced_songs.clear()

                message = f"Cleared {color(removals, Colors.bold)} modifier(s) from all songs"
        else: # If a modifier is specified
            if song_name:
                if modifier == Modifiers.synced:
                    self.desync_songs(song_name) # Will print a message with the songs that were desynced
                else:
                    try:
                        self.modifiers[modifier].remove(song_name)
                        self.songs[song_name].remove_modifiers(self.get_synced_count(song_name), modifier)
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
            print(f"{color(song_name, Colors.bold)} will be automatically chosen no more...")
            block_until_input()

            self.update_ui()
    def enable_song(self, song_name:str, silent:bool = False) -> None:
        self.disabled_song_names.discard(song_name)
        self.songs[song_name].enable()
        if not silent:
            clear_console()
            print(f"{color(song_name, Colors.bold)} can now be automatically chosen")
            block_until_input()

            self.update_ui()

    # Only call these playback functions from the play_next_song function
    # The playback mode functions will only run if the queue is empty
    # These functions will not add songs to the queue and will only set self.curr_song to the next song without playing it
    def repeat(self) -> None:
        if not self.curr_song: # If no other songs have been played
            self.curr_song_index = randint(0, len(self.song_names) - 1)
            self.curr_song = self.songs[self.song_names[self.curr_song_index]]
            self.save()
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

        self.save()
    def shuffle(self) -> None:
        available_songs:list[Song] = list(set(self.songs.values()) - {song for cooldown_group in self.songs_on_cooldown for song in cooldown_group} - {self.songs[song_name] for song_name in self.disabled_song_names}) # Relative order of songs will be scrambled
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

        self.save()
    # Helper function
    # Automatically makes curr_song_index wrap around when it equals/exceeds the length of song_names
    def increment_song_index(self, increment:int = 1) -> str: # Returns the name of the song at the new index
        self.curr_song_index += increment % len(self.song_names)
        if self.curr_song_index >= len(self.song_names): # Wrap around
            self.curr_song_index -= len(self.song_names)
        
        return self.song_names[self.curr_song_index]

    def pause(self) -> None:
        if self.playing:
            self.playing = False
            PlaySound("1s_silence", SND_ASYNC)

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
            wait(TICK_DURATION + 0.5) # Wait for the song-playing thread to prepare the next song

        self.update_ui()
    def skip(self) -> None:
        self.playing = False
        PlaySound("1s_silence.wav", SND_ASYNC)

        print("Picking the next song...")
        wait(1.5) # Wait for the current song's timer to stop. Song timers update every second independent of TICK_DURATION

        self.interlude_flag = False
        self.playing = True # Resume the song-playing thread

        wait(TICK_DURATION + 0.5) # Wait for the song-playing thread to set the next song (Must be longer than the waiting time in each iteration in the loop in play())
        self.update_ui()

    # Repeat the current song an additional time
    # the repeat will not trigger any sequences
    def encore(self) -> None:
        self.encore_activated = not self.encore_activated
        self.update_ui()
        return

    # Call this function from the song-playing thread
    def play_next_song(self) -> None:
        if self.encore_activated:
            self.encore_activated = False
            # Do nothing to curr_song and curr_song_index so the same song repeats
        else: # Don't update the sequence if the song is an encore
            if len(self.sequence) > 0: # Songs in the active sequence take priority over songs in the queue
                song:Song = self.songs[self.sequence[0]]
                del self.sequence[0]
                self.curr_song = song
                self.curr_song_index = self.song_names.index(song.song_name)
            
            elif len(self.queue) > 0:
                song:Song = self.queue[0]
                if song:
                    self.curr_song = song
                    self.curr_song_index = self.song_names.index(song.song_name)
                else: # If the queued song is a placeholder
                    mode_actions[self.mode](self)
                
                self.remove_queued_item_at_index(0) # Silently remove the item
            else:
                mode_actions[self.mode](self) # Select the next song based on the current playback mode

            # Only activate the sequence if there is not already an active sequence
            if len(self.sequence) == 0:
                self.sequence = [song_name for song_name in self.sequences.get(self.curr_song.song_name, []) if song_name in self.song_names]
        
        # Delay on updating the save file if delayed exit is not toggled because there is a gap between when curr_song is set to the queued item and when the item is removed from the queue
        if self.exit_later:
            self.save()
            self.stop()
            return

        # TODO If the user exits the program during the cooldown between songs without using delayed exit when a queued song is about to play, the new song would have been set as curr_song but wouldn't've been removed from the queue yet
        # Updates the songs on cooldown
        if len(self.songs_on_cooldown) >= self.COOLDOWN_BETWEEN_REPEATS:
            del self.songs_on_cooldown[0]
        self.songs_on_cooldown.append([self.songs[song_name] for song_name in self.synced_songs.get(self.curr_song.song_name, [self.curr_song.song_name]) if Modifiers.hot not in self.songs[song_name].attributes[SongAttributes.modifiers]])

        wait(TICK_DURATION)
        if self.playing: # If this song has ended naturally and not because the user paused the player
            if not self.interlude_flag: # Interlude flag will be set to false when playing the first song so that everything saves BEFORE waiting and then playing each subsequent song
                self.interlude_flag = True
            else:
                self.remaining_interlude_indicator = "-" * self.COOLDOWN_BETWEEN_SONGS
                
                wait(ceil(TICK_DURATION) - TICK_DURATION) # A TICK_DURATION of time has already been waited before self.playing was checked, so a TICK_DURATION has to be taken off the first second of wait time here
                self.remaining_interlude_indicator = self.remaining_interlude_indicator[1:] # Remove a character from the cooldown indicator after the first second
                for seconds_remaining in range(self.COOLDOWN_BETWEEN_SONGS - 1, -1, -1):
                    wait(1)
                    if not self.playing: # If the player was paused during the interlude
                        return # Jump back to the loop in play()
                    self.remaining_interlude_indicator = "-" * seconds_remaining

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
    {color('*')}: enqueue a placeholder song chosen by the current playback mode
{color('modifiers')}: list the active modifiers and optionally remove one more more modifiers
{color('q')} or {color('quit')}: return to {color('and update', Colors.bold)} the menu
Playback modes:
    {color('repeat')}: repeat the current song indefinitely
    {color('loop')}: loop through the playlist from the current song
    {color('shuffle')}: randomly select a song from the playlist
{color('disable')}: stop this song from being automatically chosen by loop or shuffle mode   [{color('Only available when displaying song options', Colors.orange)}]
{color('enable')}: undo the 'disable' command for the selected song   [{color('Only available when displaying song options', Colors.orange)}]
{color('karaoke')}(🎤): turn on lyrics for this song   [{color('Karaoke mode can’t be turned off until the song ends', Colors.red)}]
{color('encore')}(🔁): repeat the current song one more time
{color('pause')}: pause the music player
{color('resume')}: resume the music player {color("and restart the current song", Colors.underline)}
{color('skip')} or [{color('>>')}]: stop the current song and play the next song
{color('<song name>')}: list the available actions and modifiers for this song
[{color('exit')}] or [{color('stop')}]: terminate the program
{color('exit later')}(⌛): terminate the program after the current song ends   [{color('Enter this command again to cancel it', Colors.green)}]""")

        print()
        self.input_command(input("Enter a command: "))

    def list_songs(self, *_) -> None: # Requesting a song while another song is playing will queue the requested song instead
        result:str = self.list_actions(initial_results(section("Commands:", ["q", "quit", "*"]), section("Songs:", self.song_names)), list_type = ListModes.Songs)
        if result: # Do nothing if result is None
            if result == "*":
                self.enqueue()
            elif result in self.song_names:
                self.list_song(result)
            else:
                self.handle_invalid_result()

    # Lists the commands and modifier actions for a song
    def list_song(self, song_name:str, *_) -> None:
        results:list[str] = ["q", "quit", "enqueue"]
        if song_name in self.disabled_song_names:
            results.insert(2, "enable")
        else:
            results.insert(2, "disable")

        if len(self.songs[song_name].attributes[SongAttributes.modifiers]) > 0: # If the song has at least 1 modifier applied to it
            results.append("clear")
        results += [modifier.name for modifier in list(self.modifiers.keys())]

        result:str = self.list_actions(initial_results(section("", results)), list_type = ListModes.Song, listing_item_name = song_name)
        if result: # Do nothing if result is None
            if result in {modifier.name for modifier in Modifiers}:
                result:Modifiers = Modifiers[result]
                if result in self.songs[song_name].attributes[SongAttributes.modifiers]: # If the listing song already has this modifier
                    self.remove_modifier(song_name = song_name, modifier = result)
                else:
                    self.add_modifier(song_name = song_name, modifier = result)
            else:
                self.handle_invalid_result()

            self.update_ui()
    
    def karaoke(self) -> None:
        delay:float = 0.3 # Number of seconds to delay the lyrics by to compensate for lag
        max_display_range:int = 10 # Max number of lines before/after the current line of lyrics to display
        lyrics:list[dict[str, any]] = self.curr_song.lyrics # Each line's text includes a newline character at the end

        if not lyrics:
            print("Lyrics aren't available for this song...")
            block_until_input()
            self.update_ui()
        else:
            clear_console()
            hide_cursor()
            display_width:int = get_terminal_size().columns
            display_height:int = get_terminal_size().lines
            for i in range(len(lyrics)):
                if i == len(lyrics) - 1 or lyrics[i + 1]["time"] >= time() - self.curr_song.start_time - delay:
                    if display_height != get_terminal_size().lines:
                        clear_console()
                        hide_cursor()
                        display_height = get_terminal_size().lines
                    else:
                        cursor_up(lines = display_height)
                    display_range:int = min((display_height - 1) // 2, max_display_range) # How many lines before/after the current line of lyrics to display
                    empty_line:str = " " * display_width

                    # Print the lines before the current line
                    print(empty_line * max((display_height - 1)//2 - display_range, 0)) # Vertically center the lyrics by adding newline paddings before printing the lyric lines
                    for prev_line_index in range(i - display_range + 1, i):
                        if prev_line_index >= 0:
                            print(color(f"{lyrics[prev_line_index]['text'] : ^{display_width}}", Colors.faint))
                        else:
                            print(empty_line)

                    curr_line:str = lyrics[i]["text"]
                    print(f'{curr_line : ^{display_width}}')

                    # If there are more lyrics
                    if i < len(lyrics) - 1:
                        for next_line_index in range(i + 1, i + display_range + 1):
                            if next_line_index < len(lyrics):
                                print(color(f'{lyrics[next_line_index]["text"] : ^{display_width}}', Colors.faint), end = "")
                            else:
                                print(empty_line)

                        notes_count:int = curr_line.count(LYRIC_PLACEHOLDER_CHARACTER)
                        segment_time:float = (lyrics[i + 1]["time"] - lyrics[i]["time"]) / (notes_count + 1) # The time between this lyric and the next one is divided into equal segments, with one note lighting up in between each segment
                        notes_shown:int = 0
                        if notes_count:
                            cursor_up(lines = display_range) # Move the cursor to the beginning of the currently playing lyric line
                            print(" " * ((display_width - len(curr_line)) // 2), end = "")

                        # Wait until the time of the next line has been reached
                        # Keeps the offset between the lyrics and the song due to lag to within TIMER_RESOLUTION seconds
                        while True:
                            time_elapsed:float = time() - self.curr_song.start_time - delay

                            if notes_shown < notes_count and time_elapsed >= lyrics[i]["time"] + ((notes_shown + 1) * segment_time):
                                notes_shown += 1
                                print(color(LYRIC_PLACEHOLDER_CHARACTER + ' ', Colors.bold), end = "")

                            elif time_elapsed >= lyrics[i + 1]["time"] or time_elapsed < 0: # time_elapsed will be negative if karaoke mode was somehow activates before the song updates its start time when song.play() is called
                                break

                            wait(TIMER_RESOLUTION)

                    else: # If there are no more lyrics
                        wait(self.curr_song.duration - (time() - self.curr_song.start_time)) # Wait until the current song ends
                        self.update_ui()
    
    def update_ui(self, command:str = "") -> None: # The command parameter is used when update_ui() is called via self.listing_info
        clear_console() # Clear the console
        self.save()

        if not command:
            indicator_conditions:dict[str, bool] = {"🎤" : bool(self.curr_song.lyrics),
                                                    "🔁" : self.encore_activated,
                                                    "⌛" : self.exit_later}
            indicators:list[str] = []
            for indicator, condition in indicator_conditions.items():
                if condition == True:
                    indicators.append(indicator)

            # indicators will become a string either way
            indicators:str = "| " + " ".join(indicators) if len(indicators) else ""

            currently_playing_line = f"Currently playing: {color(f'{self.curr_song.song_name : <{self._max_song_name_length}}', Colors.green)}   {color(f'{to_minutes_str(self.curr_song.curr_duration)}/{to_minutes_str(self.curr_song.duration)}', Colors.cyan) : <11} {indicators}"
            if self.remaining_interlude_indicator: # If the cooldown is active, ensure that there is enough sapce for the maximum size of the indicator while also adding spaces to match the length of the line with its length when a song is playing
                currently_playing_line:str = f"{self.remaining_interlude_indicator : ^{max(len(remove_tags(currently_playing_line)) - len(indicators) - 1 - self.COOLDOWN_BETWEEN_SONGS, self.COOLDOWN_BETWEEN_SONGS)}}"
            print(f"{currently_playing_line} | Playback mode: {color(f'{self.mode.name : <10}', Colors.orange)}")
            
            if self.remaining_interlude_indicator:
                print(f"Next song: {color(self.curr_song.song_name, Colors.bold)}")

            if not self.playing:
                print("--Player paused--")
            print()
            # List the queue if it's not empty
            if len(self.queue) > 0 or len(self.sequence) > 0:
                print("Up next:")
                max_index_len:int = len(str(len(self.queue)))
                for song_name in self.sequence:
                    print(f"{'-  ' : <{max_index_len + 2}}{color(song_name, SongAttributes.sequenced.value)}")
                
                # Print the queue
                for i in range(len(self.queue)):
                    print(f"{f'{i + 1}. ' : <{max_index_len + 2}}{color(self.queue_song_names[i], Colors.purple)}")

                print()

            command = input(f"Input command (Enter {color('help')} for help, {color('[space]')} to pause/resume, or enter nothing to refresh): ")
        
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
    def input_command(self, user_input:str, index_search_enabled:bool = True) -> None:
        if user_input == "" or user_input == "q" or user_input == "quit":
            valid_commands["quit"](self)
        else:
            index_search_list:"list[str]" = None
            if index_search_enabled:
                index_search_list = []

            result:str = self.list_actions(search_lists(search = user_input, lists = initial_results(section("Commands:", list(valid_commands.keys())), section("Songs:", self.song_names), section("", ["*"])), index_search_list = index_search_list, include_result_type = True))
            if result == "*":
                self.enqueue()
            elif result in self.song_names:
                self.list_song(result)
            else:
                self.handle_invalid_result()
        return

    # Returns a string that explains what each song color means in a colored list of songs
    # print_list is the list that the key is for
    # Key will only include the colors that will appear in print_list
    # Commands will always be colored blue
    def get_color_key(self, print_list:"list[str]") -> str:
        print_list:set[str] = set(print_list)
        # List and sets can't be keys in a dictionary
        self.listing_colors[SongAttributes.playing]["nameset"] = {self.curr_song.song_name}
        info:list[dict[str, any]] = [self.listing_colors[SongAttributes.playing],
                                    self.listing_colors[SongAttributes.disabled],
                                    self.listing_colors[SongAttributes.queued],
                                    self.listing_colors[SongAttributes.sequenced]]
        key:str = ""

        for attribute in info:
            if attribute["enabled"] and len(attribute["nameset"] & print_list) > 0:
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
      
    # results must be in the order of [commands, modifiers, songs]
    # results_lists can also be a tuple in the form (list of sublists' tuples, SearchResultTypes)
    def list_actions(self, results_lists:"list[tuple[str, list[str]]]", list_type:ListModes = None, listing_item_name:str = None, autoclear_console:bool = True) -> None:
        if autoclear_console:
            clear_console()
        special_commands:dict[str, dict[str, function]] = self.listing_info[list_type]["special commands"] # Each key is the name of the command, and the value is a dict where "confirmation" is the function that asks the user to confirm (None if no confirmation needed) that returns True/False, and "action" is the function to run if the user confirms

        # result_type defaults to SearchResultTypes.Exact
        results_lists, results_type = results_lists if type(results_lists) == tuple else (results_lists, SearchResultTypes.Exact) # results_lists will automatically unpack if it's a tuple

        results:list = []
        separators_directory:dict[int, str] = {}
        curr_index:int = 0
        for separator, separated_list in results_lists:
            results += separated_list
            separators_directory[curr_index] = separator
            curr_index += len(separated_list)
        if len(separators_directory) == 1:
            separators_directory.clear() # No need to use separators between each section if there is only 1 section
                
        # Handle cases where there are no valid results (Guaranteed to return)
        if len(results) == 0:
            print(self.listing_info[list_type]["no results"]["message"])
            block_until_input()
            self.listing_info[list_type]["no results"]["action"](listing_item_name)
            return

        elif len(results) == 1: # Something is guaranteed to be returned here if there is only 1 item in results
            result = results[0]
            if results_type == SearchResultTypes.Fuzzy:
                clear_console()
                print(f"- {color(result, Colors.bold)}", end = "\n\n")
                if not confirmation(message = "Is this the one you want?"): # Skip past this block of code if the user confirms
                    self.listing_info[list_type]["no results"]["action"](listing_item_name)
                    return

            if result in valid_commands.keys():
                valid_commands[result](self)
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
            else:
                return result

        # If more than 1 result
        for color_key in self.listing_colors.keys():
            if color_key in self.listing_info[list_type]["disabled color keys"]:
                self.listing_colors[color_key]["enabled"] = False
            else:
                self.listing_colors[color_key]["enabled"] = True

        color_key = self.get_color_key(results)

        header_line:str = self.listing_info[list_type]["header line"]
        # Print the header line and the color key (if applicable for list_type)
        if list_type == ListModes.Queue:
            if len(set(results)) == 1: # If all the results are the same
                self.remove_queued_item(song_name = results[0])
                return
            # The selection prompt and color key for when list_type is Queue will be printed after determining the left margin
        else: # Includes when list_type is Songs
            if list_type == ListModes.Song:
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

            color_key:str = self.get_color_key(results)
            if len(color_key) > 0:
                print(f"{color_key : <{left_margin + (len(color_key) - len(remove_tags(color_key)))}}", end = "")
                
                if len(self.sequence) > 0:
                    print(separator)
                else:
                    print()

        count:int = 1
        def get_sequence_line():
            seq_song:Song = self.songs[self.sequence[count - 1]]
            return (separator + color(f"{str(count) + '. ' : <{max_sequence_digits + 2}}", Colors.faint) + color(seq_song.song_name, Colors.yellow) + f" {color('-' * (self._max_song_name_length - len(seq_song.song_name) + 1), Colors.faint)} {color(to_minutes_str(seq_song.duration), Colors.cyan)}")

        if results_type == SearchResultTypes.Fuzzy:
            print(SearchResultTypes.Fuzzy.value)

        # Print all the results
        commands_finished:bool = False # Whether all the commands in results have been listed
        modifiers_finished:bool = False
        commands_count:int = 0 # Used for determining the index of the removing song in self.queue_song_names when list_mode is Queue and the user input is a valid index
        for index in range(len(results)):
            separator:str = separators_directory.get(index, "")
            if separator: # False if separator was set to an empty string
                print(color(separator, Colors.faint))

            result = results[index]
            line:str = ""
            if commands_finished == False and (result in valid_commands.keys() or result in special_commands.keys()): # The command results will always be first in the list
                line = f"{str(count) + '.' : <{max_digits + 1}} {color(result)}"
                commands_count += 1
            
            elif modifiers_finished == False:
                try:
                    modifier:Modifiers = Modifiers[result] # Will error if the result isn't the name of a modifier
                    if list_type == ListModes.Modifiers:
                        line = f"{str(count) + '.' : <{max_digits + 1}} {color(result, modifier.value['color'])}{color('  - ' + modifier.value['description'], Colors.faint)}"
                    elif list_type == ListModes.Song:
                        action_type:str = ""
                        if len({modifier} & self.songs[listing_item_name].attributes[SongAttributes.modifiers]) == 1:
                            action_type = "(remove)"
                        else:
                            action_type = "(add)"

                        line = f"{str(count) + '.' : <{max_digits + 1}} {color(result, Modifiers[result].value['color'])} {color(action_type, Colors.faint)}"
                    else:
                        raise NotImplementedError # Manually create an error

                    commands_count += 1
                except:
                    modifiers_finished = True # Move on to listing songs without incrementing the commands count
                
                commands_finished = True

            if commands_finished and modifiers_finished: # If this result isn't a command or modifier, then assume all subsequent results are songs
                if result == "*": # Can only show up in results if list_actions was used (when listing the queue or when there's no listing mode)
                    line = f"{str(count) + '.' : <{max_digits + 1}} {result}"

                else:
                    result_song:Song = self.songs[result]
                    # THIS IS THE PINNACLE OF UI DESIGN
                    name:str = result
                    applied_colors:list[Colors] = []
                    overflow_dashes = ""

                    prev_listing_colors:list[Colors] = result_song.get_prev_listing_colors()
                    if prev_listing_colors != None:
                        applied_colors = prev_listing_colors.copy()
                    else:
                        # Color the currently playing song green (if listed), color any other queued songs purple, and color songs with sequences yellow
                        for key in ATTRIBUTES_COLORING_ORDER:
                            if self.listing_colors[key]["enabled"] and self.listing_colors[key]["color"] and result_song.attributes[key]:
                                applied_colors.append(self.listing_colors[key]["color"])

                        if self.listing_colors[SongAttributes.modifiers]["enabled"]:
                            for modifier in MODIFIERS_COLORING_ORDER:
                                if modifier in result_song.attributes[SongAttributes.modifiers]:
                                    applied_colors.append(modifier.value['color'])

                        result_song.prev_listing_colors = applied_colors.copy()

                    if len(applied_colors) > 0:
                        name = color(name, applied_colors[0])
                        del applied_colors[0]
                    for curr_color in applied_colors:
                        overflow_dashes += color(overflow_chars, curr_color)

                    # I can't explain how this line works even if I tried
                    line = f"{str(count) + '.' : <{max_digits + 1}} {name} {overflow_dashes}{color('-' * (self._max_song_name_length - len(result) - len(applied_colors)*len(overflow_chars) + (len(Modifiers) + len(self.listing_colors) - 1)*len(overflow_chars)), Colors.faint)} {color(to_minutes_str(self.songs[result].duration), Colors.cyan)}"
                
            if line: # Don't do anything if line is an empty string
                print(f"{line : <{left_margin + (len(line) - len(remove_tags(line)))}}", end = "")
                if list_type == ListModes.Queue and count <= len(self.sequence):
                    # "Attach" the line in the sequence's list onto a line in the list of commands
                    print(get_sequence_line(), end = "")
                elif list_type == ListModes.Modifiers and commands_finished == True and modifiers_finished == False: # If the listing mode is Modifiers and this result is a modifier, list the songs with each modifier in an indented, unnumbered, unselectable list after the modifier
                    for modified_song_name in self.modifiers[Modifiers[result]]:
                        print(f"\n{' ' * max(max_digits + 2, 4)}{color('|', Colors.faint)}{modified_song_name}", end = "")
                elif list_type == ListModes.Sequences and commands_finished and modifiers_finished:
                    for song_name in self.sequences[result]:
                        print(f"\n{' ' * max(max_digits + 2, 4)}{color('|', Colors.faint)}{song_name}", end = "")

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

        # Search recursively until the user quits or narrows the search down to 1 or 0 possible result(s)
        return self.list_actions(search_lists(search = user_input, lists = results_lists, index_search_list = results, include_result_type = True), list_type = list_type, listing_item_name = listing_item_name)
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
                        "q" : update_ui,
                        "quit" : update_ui,
                        "repeat" : set_mode_repeat,
                        "loop" : set_mode_loop,
                        "shuffle" : set_mode_shuffle,
                        "stop" : stop,
                        "exit" : stop,
                        "exit later" : delayed_exit,

                        "sequences" : list_sequences
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
    print("Mom: we have Spotify at home")
    wait(2)

    clear_console()
    # Will all be cleared once spotify initializes and the console clears when the first song plays
    wait(0.3)
    print(f"spotify at home {color('<company name> <address> ©2023 No Rights Reserved', Colors.faint)}")
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
        if int(song_name) <= len(valid_commands.keys()) + len(song_names) + 1: # Additionally, only raise an alert if the index is a valid one
            alert = True
            print(color(f"{song_name} dropped due to name overlap with existing index!", Colors.red))
            continue # Avoid the "finally" block of code
        # If the number converted from the song name is not a valid index, the song will be added in the "finally" block
    except:
        if (song_name in valid_commands.keys()) or song_name == "clear" or song_name == "*" or song_name == "": # Filter out any songs with the same name as a command
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
    player_thread = Thread(target = player.start, daemon = True)
    player_thread.start()

    player.interlude_flag = False # Disable the waiting period before the first song
    while True:
        if player.playing:
            player.play_next_song() # Yields within 1.5 seconds after the player is paused
        else:
            wait(TICK_DURATION) # Wait and check whether the user has resumed the player

music_thread = Thread(target = play, daemon = True)
music_thread.start()

while not player.terminated: # Yields once the user exits the player, killing every thread
    wait(TICK_DURATION)
