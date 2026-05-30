from datetime import timedelta
from models.membership import ClientMembership

class MembershipService:
    def __init__(self, db_session):
        self.db = db_session

    def assign_to_client(self, client, membership_type, start_date):
        end_date = start_date + timedelta(days=membership_type.duration_days)
        client_membership = ClientMembership(
            client_id=client.id,
            membership_id=membership_type.id,
            start_date=start_date,
            end_date=end_date
        )
        self.db.add(client_membership)
        self.db.commit()
        self.db.refresh(client_membership)
        return client_membership

    def check_active_status(self, client, current_date):
        # We need to check if the client has any active membership at current_date
        active_memberships = [
            m for m in client.memberships 
            if m.start_date <= current_date <= m.end_date
        ]
        return len(active_memberships) > 0
