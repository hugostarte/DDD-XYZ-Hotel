from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from ..main import CustomerId, Email, FullName, PhoneNumber


@dataclass
class Customer:
    id: CustomerId
    
    full_name: FullName
    email: Email
    phone_number: PhoneNumber
    
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    is_active: bool = field(default=True)
    
    def update_contact_info(self, email: Optional[Email] = None, 
                           phone_number: Optional[PhoneNumber] = None) -> None:
        if email:
            self.email = email
        
        if phone_number:
            self.phone_number = phone_number
        
        self.updated_at = datetime.now()
    
    def update_name(self, new_name: FullName) -> None:
        self.full_name = new_name
        self.updated_at = datetime.now()
    
    def suspend(self) -> None:
        self.is_active = False
        self.updated_at = datetime.now()
    
    def reactivate(self) -> None:
        self.is_active = True
        self.updated_at = datetime.now()
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, Customer):
            return False
        return self.id == other.id
    
    def __hash__(self) -> int:
        return hash(self.id.value)