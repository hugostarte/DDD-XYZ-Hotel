

from abc import ABC, abstractmethod
from typing import Optional, List
from .booking import Booking, BookingId
from ..main import CustomerId
from ..room_management.room_types import RoomTypeEnum, RoomId


class BookingRepository(ABC):
    
    @abstractmethod
    async def save(self, booking: Booking) -> None:
        pass
    
    @abstractmethod
    async def find_by_id(self, booking_id: BookingId) -> Optional[Booking]:
        pass
    
    @abstractmethod
    async def find_by_customer(self, customer_id: CustomerId) -> List[Booking]:
        pass
    
    @abstractmethod
    async def find_by_room(self, room_id: RoomId) -> List[Booking]:
        pass
    
    @abstractmethod
    async def find_all(self) -> List[Booking]:
        pass