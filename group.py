from typing import Union

from info import Modifiers
from song import Song

class SongGroup:
    def __init__(self, songs:"Union[list[Song], set[Song]]", allow_duplicates:bool = False):
        self.songs:Union[list, set][Song]
        self.song_names:list[str]
        self.set_songs(songs)
        
        self.allow_duplicates:bool = allow_duplicates
        
    # Makes a copy of songs before filtering the list and updating self.songs and self.song_names
    def set_songs(self, songs:"Union[list[Song], set[Song]]") -> None:
        songs = songs.copy()
        
        if type(songs) == list: # Remove duplicates from songs in-place
            encountered_items:set[Song] = set()
            for i in range(len(songs) - 1, -1, -1):
                if songs[i] in encountered_items:
                    del songs[i]
                else:
                    encountered_items.add(songs[i])

        self.songs = songs
        self.song_names = [song.song_name for song in self.songs]

    def get_save_list(self) -> "list[str]":
        return [song.song_name for song in self.songs]

class Playlist(SongGroup):
    def __init__(self, name:str, songs:"list[Song]" = []):
        super().__init__(songs, allow_duplicates = False)
        self.name:str = name

        self.curr_song_index:int = None

    def update_songs(self, songs:"list[Song]") -> None:
        if self.curr_song_index != None:
            match_found:bool = False
            # If the song name at self.curr_song_index also exists in the new song list, move the index
            for i, song in enumerate(songs):
                if song.song_name == self.song_names[self.curr_song_index]:
                    self.curr_song_index = i
                    match_found = True
                    break
            # Otherwise, reset self.curr_song_index to 0
            if not match_found:
                self.curr_song_index = 0
        
        # Update self.songs and self.song_names
        self.set_songs(songs) # Superclass method

    def __str__(self) -> str:
        return self.name
    
    def __repr__(self) -> str:
        return f"Playlist {self.name}: {str(self.songs)}"

class SyncedList(SongGroup):
    def __init__(self, songs:"set[Song]"):
        super().__init__(songs, allow_duplicates = False)

        # Update the weights of each song in this synced list
        for song in songs:
            song.add_modifiers(len(songs), Modifiers.synced)

    def add_songs(self, new_songs:"list[Song]") -> None:
        self.songs += new_songs
        self.update_modifiers()

    def remove_song(self, removing_song:Song) -> bool:
        if removing_song in self.songs:
            if len(self.songs) <= 2: # If there will be only 1 song left after removal
                self.disband()

            removing_song.remove_modifiers(None, Modifiers.synced)
            self.songs.discard(removing_song)

            self.update_modifiers()
            return True
        else:
            return False
    
    # Update the synced modifier statuses and synced counts of songs
    def update_modifiers(self) -> None:
        for song in self.songs:
            song.add_modifiers(len(self.songs), Modifiers.synced)
    
    def disband(self) -> None:
        for song in self.songs:
            song.remove_modifiers(None, Modifiers.synced)
            self.songs.clear()
    
    def __str__(self) -> str:
        return f"SyncedList: {str(self.songs)}"