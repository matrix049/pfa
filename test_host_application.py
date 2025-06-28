#!/usr/bin/env python
"""
Test script to verify host application flow
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pfa.settings')
django.setup()

from app.models import HostApplication, User, UserProfile
from django.contrib.auth.models import User

def test_host_application_flow():
    """Test the host application creation flow"""
    print("Testing Host Application Flow...")
    
    # Check if HostApplication model exists
    try:
        applications = HostApplication.objects.all()
        print(f"✅ HostApplication model is working. Found {applications.count()} applications.")
    except Exception as e:
        print(f"❌ HostApplication model error: {e}")
        return False
    
    # Check if we can create a test application
    try:
        # Get or create a test user
        test_user, created = User.objects.get_or_create(
            username='test_host_user',
            defaults={
                'email': 'test@example.com',
                'first_name': 'Test',
                'last_name': 'User'
            }
        )
        
        # Ensure user has a profile
        profile, created = UserProfile.objects.get_or_create(
            user=test_user,
            defaults={'role': 'user'}
        )
        
        # Create a test application
        application = HostApplication.objects.create(
            user=test_user,
            business_name='Test Business',
            business_address='123 Test Street',
            business_phone='+1234567890',
            description='Test application for verification',
            status='pending'
        )
        
        print(f"✅ Successfully created test application: {application}")
        
        # Clean up
        application.delete()
        if created:
            test_user.delete()
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating test application: {e}")
        return False

def test_admin_integration():
    """Test admin integration"""
    print("\nTesting Admin Integration...")
    
    try:
        from app.admin import HostApplicationAdmin
        print("✅ HostApplicationAdmin is properly configured")
        
        # Check admin actions
        admin = HostApplicationAdmin(HostApplication, None)
        actions = admin.get_actions(None)
        
        if 'approve_applications' in actions:
            print("✅ Approve applications action is available")
        else:
            print("❌ Approve applications action is missing")
            
        if 'reject_applications' in actions:
            print("✅ Reject applications action is available")
        else:
            print("❌ Reject applications action is missing")
            
        return True
        
    except Exception as e:
        print(f"❌ Admin integration error: {e}")
        return False

if __name__ == '__main__':
    print("=== Host Application System Test ===\n")
    
    # Test model functionality
    model_ok = test_host_application_flow()
    
    # Test admin integration
    admin_ok = test_admin_integration()
    
    print("\n=== Test Results ===")
    if model_ok and admin_ok:
        print("✅ All tests passed! Host application system is working correctly.")
    else:
        print("❌ Some tests failed. Please check the errors above.")
    
    print("\n=== Manual Testing Instructions ===")
    print("1. Start the server: python manage.py runserver")
    print("2. Go to http://localhost:8000/dashboard/")
    print("3. Click 'Become a Host' button")
    print("4. Fill out the form and submit")
    print("5. Check admin panel at http://localhost:8000/admin/app/hostapplication/")
    print("6. Verify the application appears and can be approved/rejected") 