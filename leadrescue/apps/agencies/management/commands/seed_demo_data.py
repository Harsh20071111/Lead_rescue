import random
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from apps.agencies.models import Agency
from apps.accounts.models import AgentProfile
from apps.properties.models import Property
from apps.leads.models import Lead

User = get_user_model()

class Command(BaseCommand):
    help = "Seeds demo data for a Mumbai agency, including agents, properties, and leads."

    def handle(self, *args, **options):
        self.stdout.write("Starting data seeding...")

        with transaction.atomic():
            # Cleanup existing demo data to keep it repeatable
            self.stdout.write("Cleaning up existing demo data...")
            Agency.objects.filter(name="Mumbai Elite Realty").delete()
            User.objects.filter(email__in=["demo@owner.com", "agent@demo.com"]).delete()

            # 1. Create Agency
            agency = Agency.objects.create(
                name="Mumbai Elite Realty",
                owner_phone="9876543210",
                owner_email="demo@owner.com",
                city="Mumbai",
                subscription_status="active"
            )
            self.stdout.write(f"Created Agency: {agency.name}")

            # 2. Create Owner User & Profile
            owner_user = User.objects.create_user(
                username="demo@owner.com",
                email="demo@owner.com",
                password="password123",
                first_name="Rohan",
                last_name="Sharma"
            )
            owner_profile = AgentProfile.objects.create(
                user=owner_user,
                agency=agency,
                role="owner",
                phone="9876543210"
            )
            self.stdout.write(f"Created Owner Agent: {owner_user.get_full_name()}")

            # 3. Create Agent User & Profile
            agent_user = User.objects.create_user(
                username="agent@demo.com",
                email="agent@demo.com",
                password="password123",
                first_name="Amit",
                last_name="Patel"
            )
            agent_profile = AgentProfile.objects.create(
                user=agent_user,
                agency=agency,
                role="agent",
                phone="9876543211"
            )
            self.stdout.write(f"Created Agent: {agent_user.get_full_name()}")

            # 4. Create 10 Properties
            mumbai_locations = [
                ("Bandra West", "Sea Breeze Apartments", "2 BHK", 32000000),
                ("Andheri West", "Shanti Heights", "3 BHK", 18500000),
                ("Worli", "Skyline Towers", "4 BHK", 85000000),
                ("Juhu", "Palm Beach Residency", "3 BHK", 42000000),
                ("Khar West", "Woodland Meadows", "2 BHK", 28000000),
                ("Goregaon East", "Greenwood Estate", "1 BHK", 9500000),
                ("Colaba", "Heritage View", "2 BHK", 35000000),
                ("Powai", "Lakeside Crest", "2 BHK", 16000000),
                ("Chembur", "Aura Grandeur", "3 BHK", 21000000),
                ("Malad West", "Marina Bay", "1 BHK", 8800000),
            ]

            agents = [owner_profile, agent_profile]
            property_objs = []

            for i, (loc, title, bhk, price) in enumerate(mumbai_locations):
                status = "available"
                if i in [2, 5]:
                    status = "sold"
                elif i == 8:
                    status = "on_hold"
                
                prop = Property.objects.create(
                    agency=agency,
                    title=title,
                    bhk=bhk,
                    price=price,
                    location=loc,
                    city="Mumbai",
                    status=status,
                    description=f"Premium {bhk} home in {loc}. Excellent connectivity and modern amenities."
                )
                property_objs.append(prop)
            self.stdout.write("Created 10 Demo Properties.")

            # 5. Create 20 Leads
            first_names = ["Arjun", "Aditya", "Neha", "Priya", "Rahul", "Siddharth", "Karan", "Anjali", "Vikram", "Sneha"]
            last_names = ["Mehta", "Joshi", "Verma", "Kapoor", "Nair", "Rao", "Gupta", "Singh", "Shah", "Desai"]
            sources = ["WhatsApp Intake", "MagicBricks", "Housing.com", "Referral", "Direct Call"]
            lead_statuses = ["New", "Contacted", "Site Visit", "Negotiation", "Closed Won", "Closed Lost"]

            for idx in range(1, 21):
                name = f"{random.choice(first_names)} {random.choice(last_names)}"
                phone = f"98200{idx:05d}"
                assigned_agent = random.choice(agents)
                status = random.choice(lead_statuses)
                
                Lead.objects.create(
                    agency=agency,
                    agent=assigned_agent,
                    name=name,
                    phone=phone,
                    source=random.choice(sources),
                    status=status,
                    budget=f"₹{random.choice([80, 120, 200, 350])} Lakhs",
                    bhk_preference=random.choice(["1 BHK", "2 BHK", "3 BHK", "4 BHK"]),
                    area_preference=random.choice(["Bandra", "Andheri", "Worli", "Powai"]),
                    notes=f"Interested in buying a premium apartment. Preferred location: Mumbai. Assigned to {assigned_agent.user.first_name}."
                )
            self.stdout.write("Created 20 Demo Leads.")

        self.stdout.write(self.style.SUCCESS("Successfully seeded all demo data!"))
