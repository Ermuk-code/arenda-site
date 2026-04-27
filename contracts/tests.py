import tempfile
from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from bookings.models import Booking
from items.models import Item

from .models import Contract

User = get_user_model()


@override_settings(MEDIA_ROOT=tempfile.gettempdir())
class ContractApiTest(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username='owner_contract',
            password='12345',
            email='owner_contract@test.com',
            profile_completed=True,
        )
        self.renter = User.objects.create_user(
            username='renter_contract',
            password='12345',
            email='renter_contract@test.com',
            profile_completed=True,
        )
        self.item = Item.objects.create(
            title='Camera Contract',
            description='Mirrorless camera',
            price_per_day=1500,
            owner=self.owner,
            status='available',
        )
        self.booking = Booking.objects.create(
            item=self.item,
            renter=self.renter,
            start_date=date(2026, 5, 1),
            end_date=date(2026, 5, 3),
            status='confirmed',
            payment_status='paid',
        )
        self.owner_client = APIClient()
        self.owner_client.force_authenticate(user=self.owner)
        self.renter_client = APIClient()
        self.renter_client.force_authenticate(user=self.renter)

    def test_participant_can_open_contract_by_booking(self):
        response = self.renter_client.get(f'/api/contracts/by-booking/{self.booking.id}/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['booking'], self.booking.id)
        self.assertEqual(response.data['status'], 'draft')
        self.assertTrue(Contract.objects.filter(booking=self.booking).exists())
        self.assertTrue(response.data['file_url'].endswith('.pdf'))

    def test_renter_and_owner_can_sign_contract_with_demo_eds(self):
        contract = Contract.create_for_booking(self.booking)

        renter_response = self.renter_client.post(
            f'/api/contracts/{contract.id}/sign/',
            {'signer_name': 'Ivan Renter', 'certificate_pin': '1234'},
            format='json',
        )
        self.assertEqual(renter_response.status_code, 200)
        contract.refresh_from_db()
        self.assertIsNotNone(contract.renter_signed_at)
        self.assertFalse(contract.is_signed)

        owner_response = self.owner_client.post(
            f'/api/contracts/{contract.id}/sign/',
            {'signer_name': 'Olga Owner', 'certificate_pin': '5678'},
            format='json',
        )
        self.assertEqual(owner_response.status_code, 200)
        contract.refresh_from_db()
        self.assertTrue(contract.is_signed)
        self.assertIsNotNone(contract.signed_at)
        self.assertTrue(contract.renter_signature_code.startswith('EDS-DEMO-RENTER-'))
        self.assertTrue(contract.owner_signature_code.startswith('EDS-DEMO-OWNER-'))
        self.assertTrue(contract.file.name.endswith('.pdf'))

    def test_contract_is_unavailable_for_pending_booking(self):
        pending_booking = Booking.objects.create(
            item=self.item,
            renter=self.renter,
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 4),
            status='pending',
        )

        response = self.renter_client.get(f'/api/contracts/by-booking/{pending_booking.id}/')

        self.assertEqual(response.status_code, 400)
