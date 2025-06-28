#!/usr/bin/env python
"""
Create test data for manual testing of dashboard approve/reject functionality
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pfa.settings')
django.setup()

from app.models import HostApplication, User, UserProfile
from django.contrib.auth.models import User

def create_test_data():
    """Create test admin user and application for manual testing"""
    print("=== Creating Test Data for Manual Testing ===\n")
    
    # Create test user (applicant)
    test_user, created = User.objects.get_or_create(
        username='testuser',
        defaults={
            'email': 'testuser@example.com',
            'first_name': 'Test',
            'last_name': 'User'
        }
    )
    
    if created:
        test_user.set_password('testpass123')
        test_user.save()
        print(f"✅ Created test user: testuser (password: testpass123)")
    else:
        print(f"✅ Test user already exists: testuser (password: testpass123)")
    
    # Ensure user has a profile
    profile, created = UserProfile.objects.get_or_create(
        user=test_user,
        defaults={'role': 'user'}
    )
    
    # Create test application
    application, created = HostApplication.objects.get_or_create(
        user=test_user,
        defaults={
            'business_name': 'Test Business',
            'business_address': '123 Test Street',
            'business_phone': '+1234567890',
            'description': 'Test application for manual testing',
            'status': 'pending'
        }
    )
    
    if created:
        print(f"✅ Created test application: {application}")
    else:
        print(f"✅ Test application already exists: {application}")
    
    # Create admin user
    admin_user, created = User.objects.get_or_create(
        username='admin',
        defaults={
            'email': 'admin@example.com',
            'first_name': 'Admin',
            'last_name': 'User',
            'is_staff': True,
            'is_superuser': True
        }
    )
    
    if created:
        admin_user.set_password('adminpass123')
        admin_user.save()
        print(f"✅ Created admin user: admin (password: adminpass123)")
    else:
        print(f"✅ Admin user already exists: admin (password: adminpass123)")
    
    # Ensure admin has profile
    admin_profile, created = UserProfile.objects.get_or_create(
        user=admin_user,
        defaults={'role': 'admin'}
    )
    admin_profile.role = 'admin'
    admin_profile.save()
    
    print(f"\n=== Test Data Ready ===")
    print(f"Admin Login:")
    print(f"  Username: admin")
    print(f"  Password: adminpass123")
    print(f"  URL: http://127.0.0.1:8000/login/")
    print(f"\nTest Application:")
    print(f"  Applicant: testuser")
    print(f"  Business: Test Business")
    print(f"  Status: {application.status}")
    print(f"\nDashboard URL: http://127.0.0.1:8000/dashboard/")
    print(f"\nSteps to test:")
    print(f"1. Go to http://127.0.0.1:8000/login/")
    print(f"2. Login as admin/adminpass123")
    print(f"3. Go to Dashboard")
    print(f"4. Click on 'Host Applications' tab")
    print(f"5. Try Approve/Reject buttons")
    print(f"6. Check browser console and network tab for errors")

if __name__ == '__main__':
    create_test_data() 