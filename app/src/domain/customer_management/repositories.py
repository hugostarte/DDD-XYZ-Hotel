

from abc import ABC, abstractmethod
from typing import Optional, List
from .customer import Customer
from ..main import CustomerId, Email


class CustomerRepository(ABC):
    
    @abstractmethod
    async def save(self, customer: Customer) -> None:
        pass
    
    @abstractmethod
    async def find_by_id(self, customer_id: CustomerId) -> Optional[Customer]:
        pass
    
    @abstractmethod
    async def find_by_email(self, email: Email) -> Optional[Customer]:
        pass
    
    @abstractmethod
    async def find_all(self) -> List[Customer]:
        pass
    
    @abstractmethod
    async def exists_with_email(self, email: Email) -> bool:
        pass