from models.client import Client

class ClientRepository:
    def __init__(self, db_session):
        self.db = db_session

    def add_client(self, client_obj: Client):
        self.db.add(client_obj)
        self.db.commit()
        self.db.refresh(client_obj)
        return client_obj

    def get_all_clients(self):
        return self.db.query(Client).all()

    def find_client_by_phone(self, phone: str):
        return self.db.query(Client).filter(Client.phone == phone).first()

    def get_client_by_id(self, client_id: int):
        return self.db.query(Client).filter(Client.id == client_id).first()
