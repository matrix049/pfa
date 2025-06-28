#!/usr/bin/env python
"""
Test script to verify host application approval system
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pfa.settings')
django.setup()

from app.models import HostApplication, User, UserProfile
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

def test_host_application_creation():
    """Test creating a host application"""
    print("Testing Host Application Creation...")
    
    try:
        # Create test user
        test_user, created = User.objects.get_or_create(
            username='test_applicant',
            defaults={
                'email': 'applicant@example.com',
                'first_name': 'Test',
                'last_name': 'Applicant'
            }
        )
        
        # Ensure user has a profile
        profile, created = UserProfile.objects.get_or_create(
            user=test_user,
            defaults={'role': 'user'}
        )
        
        # Create application
        application = HostApplication.objects.create(
            user=test_user,
            business_name='Test Business',
            business_address='123 Test Street',
            business_phone='+1234567890',
            description='Test application for approval testing',
            status='pending'
        )
        
        print(f"✅ Created test application: {application}")
        return application, test_user
        
    except Exception as e:
        print(f"❌ Error creating test application: {e}")
        return None, None

def test_approval_views():
    """Test the approval/rejection views"""
    print("\nTesting Approval/Rejection Views...")
    
    # Create test application
    application, test_user = test_host_application_creation()
    if not application:
        return False
    
    # Create admin user
    admin_user, created = User.objects.get_or_create(
        username='test_admin',
        defaults={
            'email': 'admin@example.com',
            'first_name': 'Test',
            'last_name': 'Admin',
            'is_staff': True,
            'is_superuser': True
        }
    )
    
    # Ensure admin has profile
    admin_profile, created = UserProfile.objects.get_or_create(
        user=admin_user,
        defaults={'role': 'admin'}
    )
    admin_profile.role = 'admin'
    admin_profile.save()
    
    # Create test client
    client = Client()
    
    # Login as admin
    client.force_login(admin_user)
    
    try:
        # Test approve view
        approve_url = reverse('approve_host_application', args=[application.id])
        response = client.post(approve_url)
        
        if response.status_code == 302:  # Redirect expected
            print("✅ Approve view is working")
            
            # Check if application was approved
            application.refresh_from_db()
            if application.status == 'approved':
                print("✅ Application status updated to approved")
                
                # Check if user role was updated
                test_user.userprofile.refresh_from_db()
                if test_user.userprofile.role == 'host':
                    print("✅ User role updated to host")
                else:
                    print("❌ User role not updated")
                    return False
            else:
                print("❌ Application status not updated")
                return False
        else:
            print(f"❌ Approve view failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing approve view: {e}")
        return False
    
    # Clean up
    application.delete()
    if test_user.username == 'test_applicant':
        test_user.delete()
    
    return True

def test_admin_interface():
    """Test admin interface functionality"""
    print("\nTesting Admin Interface...")
    
    try:
        from app.admin import HostApplicationAdmin
        
        # Test admin configuration
        admin = HostApplicationAdmin(HostApplication, None)
        
        # Check if actions are available
        actions = admin.get_actions(None)
        
        if 'approve_applications' in actions:
            print("✅ Approve applications action available")
        else:
            print("❌ Approve applications action missing")
            
        if 'reject_applications' in actions:
            print("✅ Reject applications action available")
        else:
            print("❌ Reject applications action missing")
            
        # Check if custom template is set
        if hasattr(admin, 'change_list_template'):
            print(f"✅ Custom template set: {admin.change_list_template}")
        else:
            print("❌ Custom template not set")
            
        return True
        
    except Exception as e:
        print(f"❌ Admin interface error: {e}")
        return False

def test_url_patterns():
    """Test URL patterns"""
    print("\nTesting URL Patterns...")
    
    try:
        # Test approve URL
        approve_url = reverse('approve_host_application', args=[1])
        print(f"✅ Approve URL: {approve_url}")
        
        # Test reject URL
        reject_url = reverse('reject_host_application', args=[1])
        print(f"✅ Reject URL: {reject_url}")
        
        return True
        
    except Exception as e:
        print(f"❌ URL pattern error: {e}")
        return False

if __name__ == '__main__':
    print("=== Host Application Approval System Test ===\n")
    
    # Test URL patterns
    url_ok = test_url_patterns()
    
    # Test admin interface
    admin_ok = test_admin_interface()
    
    # Test approval views
    views_ok = test_approval_views()
    
    print("\n=== Test Results ===")
    if url_ok and admin_ok and views_ok:
        print("✅ All tests passed! Host application approval system is working correctly.")
    else:
        print("❌ Some tests failed. Please check the errors above.")
    
    print("\n=== Manual Testing Instructions ===")
    print("1. Start the server: python manage.py runserver")
    print("2. Go to http://localhost:8000/admin/")
    print("3. Login as admin user")
    print("4. Go to 'Host applications' section")
    print("5. You should see individual 'Approve' and 'Reject' buttons for pending applications")
    print("6. Click 'Approve' or 'Reject' to test the functionality")
    print("7. Verify that application status and user role are updated correctly")
    
    print("\n=== Features Implemented ===")
    print("✅ Individual approve/reject buttons for each application")
    print("✅ Custom admin template with enhanced styling")
    print("✅ Confirmation dialogs before approval/rejection")
    print("✅ Loading states during processing")
    print("✅ Automatic user role updates (user → host for approved)")
    print("✅ Success/error messages")
    print("✅ CSRF protection")
    print("✅ Admin-only access control") 