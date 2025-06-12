from typing import Union

from info import Modifiers
from song import Song

class SongGroup:
    def __init__(self, songs:"Union[list, set][Song]", allow_duplicates:bool = False):
        self.allow_duplicates:bool = allow_duplicates

        if (not allow_duplicates) and (type(songs) == list): # Remove duplicates from songs in-place
            encountered_items:set[Song] = set()
            for i in range(len(songs) - 1, -1, -1):
                if songs[i] in encountered_items:
                    del songs[i]
                else:
                    encountered_items.add(songs[i])

        self.songs:Union[list, set][Song] = songs

    def get_save_list(self) -> "list[str]":
        return [song.song_name for song in self.songs]

class Playlist(SongGroup):
    def __init__(self, name:str, songs:"list[Song]" = []):
        super().__init__(songs, allow_duplicates = False)
        self.name:str = name
        self.song_names:list[str] = [song.song_name for song in songs]

        self.curr_song_index:int = None

    # def add_song(self, song:Song, index:int = None) -> bool:
    #     # If the new item is a duplicate and duplicates are not allowed
    #     if (not self.allow_duplicates) and (song in self.songs):
    #         return False
    #     else:
    #         if index == None:
    #             self.songs.append(song)
    #         else: # Clamp the specified index within the range of the indices of self.items
    #             self.songs.insert(min(max(index, 0), len(self.songs)), song)
            
    #         return True
    
    # def remove_song(self, song:Song = None, index:int = None) -> bool:
    #     if index == None:
    #         if song in self.songs:
    #             self.songs.remove(song)
    #             return True
    #         else:
    #             return False

    #     else: # If an index was provided
    #         if index >= 0 and index < len(self.songs):
    #             del self.songs[index]
    #             return True
    #         else:
    #             return False

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