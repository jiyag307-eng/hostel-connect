"""
Comprehensive Test Suite for Hostel Management System
Tests routing, authentication, student actions, and admin actions.
Run: python test_app.py
"""

import unittest
from app import app
from database import init_db, query_db
import seed_data

class HostelAppTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Seed test database
        seed_data.seed()

    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def login(self, username, password):
        return self.client.post('/login', data=dict(
            username=username,
            password=password
        ), follow_redirects=True)

    def logout(self):
        return self.client.get('/logout', follow_redirects=True)

    # 1. Public Routes
    def test_landing_page(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'HostelSphere', response.data)
        self.assertIn(b'Today', response.data)

    def test_notices_page(self):
        response = self.client.get('/notices')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Notice Board', response.data)

    def test_mess_menu_page(self):
        response = self.client.get('/mess-menu?day=Monday')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Menu for Monday', response.data)
        self.assertIn(b'Rajma Masala', response.data)

    # 2. Authentication & RBAC
    def test_student_login_and_dashboard(self):
        rv = self.login('25001003043', 'student123')
        self.assertEqual(rv.status_code, 200)
        self.assertIn(b'Jiyansh Sardana', rv.data)
        self.assertIn(b'My Room', rv.data)

        # Access Student Dashboard
        dash = self.client.get('/student/dashboard')
        self.assertEqual(dash.status_code, 200)
        self.assertIn(b'A-101', dash.data)

        # Student cannot access admin portal
        admin_page = self.client.get('/admin/dashboard', follow_redirects=True)
        self.assertIn(b'Access denied', admin_page.data)

        self.logout()

    def test_admin_login_and_dashboard(self):
        rv = self.login('admin', 'admin123')
        self.assertEqual(rv.status_code, 200)
        self.assertIn(b'Administration Console', rv.data)

        # Access Admin Dashboard
        dash = self.client.get('/admin/dashboard')
        self.assertEqual(dash.status_code, 200)
        self.assertIn(b'Pending Gate Outpasses', dash.data)

        self.logout()

    def test_invalid_login(self):
        rv = self.login('admin', 'wrong_password')
        self.assertIn(b'Invalid credentials', rv.data)

    # 3. Student Workflow: Lodge Complaint & Apply Outpass
    def test_student_lodge_complaint(self):
        self.login('25001003043', 'student123')
        rv = self.client.post('/student/complaints', data=dict(
            category='WiFi',
            room_number='A-101',
            priority='High',
            title='Test Disconnection Issue',
            description='Wi-Fi drops out frequently during lecture hours.'
        ), follow_redirects=True)
        self.assertEqual(rv.status_code, 200)
        self.assertIn(b'Test Disconnection Issue', rv.data)
        self.logout()

    def test_student_apply_outpass_and_view_pass(self):
        self.login('25001003043', 'student123')
        rv = self.client.post('/student/outpass', data=dict(
            departure_time='2026-11-20T10:00',
            expected_return='2026-11-21T18:00',
            destination='Gurugram Sector 29',
            emergency_contact='+91 98765 00001',
            reason='Visiting relatives for family function'
        ), follow_redirects=True)
        self.assertEqual(rv.status_code, 200)
        self.assertIn(b'Gurugram Sector 29', rv.data)
        self.logout()

    # 4. Admin Workflow: Notice CRUD & Outpass Review
    def test_admin_create_notice(self):
        self.login('admin', 'admin123')
        rv = self.client.post('/admin/notices/new', data=dict(
            title='Unit Test Notice Title',
            category='Event',
            content='This is a test announcement content for automated testing.',
            is_pinned='1'
        ), follow_redirects=True)
        self.assertEqual(rv.status_code, 200)
        self.assertIn(b'Unit Test Notice Title', rv.data)
        self.logout()

    def test_admin_review_outpass(self):
        self.login('admin', 'admin123')
        # Review outpass #3 (which is pending in seed)
        rv = self.client.post('/admin/outpass/3/review', data=dict(
            decision='Approved',
            admin_remarks='Verified with parent. Approved by Chief Warden.'
        ), follow_redirects=True)
        self.assertEqual(rv.status_code, 200)
        self.logout()

    # 5. Admin Workflow: Room Allotment
    def test_admin_room_allotment(self):
        self.login('admin', 'admin123')
        # Student 5 (Sneha Kapoor, id 6) into Room A-103
        rv = self.client.post('/admin/rooms/allot', data=dict(
            student_id=6,
            room_id=3,
            bed_number=1
        ), follow_redirects=True)
        self.assertEqual(rv.status_code, 200)
        self.logout()


if __name__ == '__main__':
    unittest.main()
