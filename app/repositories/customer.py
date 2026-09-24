from app.models.customer import Customer

from .base import BaseRepository


class CustomerRepository(BaseRepository[Customer]):
    pass


customer_repository = CustomerRepository(Customer)
