

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Dict, List
from ..main import Money
from .room_types import RoomId, RoomNumber, RoomType, RoomTypeEnum


@dataclass
class Room:
    id: RoomId
    
    number: RoomNumber
    room_type: RoomType
    floor: int
    
    is_available: bool = field(default=True)
    is_maintenance: bool = field(default=False)
 
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def reserve(self) -> None:
        if not self.is_available:
            raise ValueError("La chambre n'est pas disponible")
        
        if self.is_maintenance:
            raise ValueError("La chambre est en maintenance")
        
        self.is_available = False
        self.updated_at = datetime.now()
    
    def release(self) -> None:
        self.is_available = True
        self.updated_at = datetime.now()
    
    def set_maintenance(self, in_maintenance: bool) -> None:
        self.is_maintenance = in_maintenance
        if in_maintenance:
            self.is_available = False
        self.updated_at = datetime.now()
    
    def get_price_per_night(self) -> Money:
        return self.room_type.price_per_night
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, Room):
            return False
        return self.id == other.id
    
    def __hash__(self) -> int:
        return hash(self.id.value)


@dataclass
class RoomInventory:
    
    rooms_by_type: Dict[RoomTypeEnum, List[Room]] = field(default_factory=dict)
    

    last_updated: datetime = field(default_factory=datetime.now)
    
    def add_room(self, room: Room) -> None:
        room_type = room.room_type.type
        
        if room_type not in self.rooms_by_type:
            self.rooms_by_type[room_type] = []
        
        if room in self.rooms_by_type[room_type]:
            raise ValueError(f"La chambre {room.number.value} existe déjà")
        
        self.rooms_by_type[room_type].append(room)
        self.last_updated = datetime.now()
    
    def get_available_rooms(self, room_type: RoomTypeEnum, 
                          check_date: date = None) -> List[Room]:
        if room_type not in self.rooms_by_type:
            return []
        
        return [
            room for room in self.rooms_by_type[room_type]
            if room.is_available and not room.is_maintenance
        ]
    
    def count_available_rooms(self, room_type: RoomTypeEnum) -> int:
        return len(self.get_available_rooms(room_type))
    
    def count_occupied_rooms(self, room_type: RoomTypeEnum) -> int:
        if room_type not in self.rooms_by_type:
            return 0
        
        return len([
            room for room in self.rooms_by_type[room_type]
            if not room.is_available and not room.is_maintenance
        ])
    
    def count_total_rooms(self, room_type: RoomTypeEnum) -> int:
        if room_type not in self.rooms_by_type:
            return 0
        
        return len(self.rooms_by_type[room_type])
    
    def reserve_room(self, room_type: RoomTypeEnum, quantity: int = 1) -> List[Room]:
        available_rooms = self.get_available_rooms(room_type)
        
        if len(available_rooms) < quantity:
            raise ValueError(
                f"Pas assez de chambres disponibles. "
                f"Demandé: {quantity}, Disponible: {len(available_rooms)}"
            )
        
        reserved_rooms = available_rooms[:quantity]
        for room in reserved_rooms:
            room.reserve()
        
        self.last_updated = datetime.now()
        return reserved_rooms
    
    def release_room(self, room_id: RoomId) -> None:
        room = self.find_room_by_id(room_id)
        if room:
            room.release()
            self.last_updated = datetime.now()
        else:
            raise ValueError(f"Chambre {room_id.value} non trouvée")
    
    def find_room_by_id(self, room_id: RoomId) -> Room:
        for rooms_list in self.rooms_by_type.values():
            for room in rooms_list:
                if room.id == room_id:
                    return room
        return None
    
    def get_occupancy_summary(self) -> Dict[RoomTypeEnum, Dict[str, int]]:
        summary = {}
        
        for room_type in RoomTypeEnum:
            summary[room_type] = {
                "total": self.count_total_rooms(room_type),
                "available": self.count_available_rooms(room_type),
                "occupied": self.count_occupied_rooms(room_type)
            }
        
        return summary