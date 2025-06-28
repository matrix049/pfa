#!/usr/bin/env python
"""
Test to debug CSRF token issue
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pfa.settings')
django.setup()

from app.models import HostApplication, User, UserProfile
from django.test import Client
from django.urls import reverse
from django.contrib.auth.models import User

def test_csrf_debug():
    """Test CSRF token handling"""
    print("=== CSRF Token Debug Test ===\n")
    
    # Get existing admin user
    try:
        admin_user = User.objects.get(username='admin')
        print(f"✅ Found admin user: {admin_user.username}")
    except User.DoesNotExist:
        print("❌ Admin user not found")
        return False
    
    # Get existing test application
    try:
        application = HostApplication.objects.filter(status='pending').first()
        if application:
            print(f"✅ Found pending application: {application}")
        else:
            print("❌ No pending applications found")
            return False
    except Exception as e:
        print(f"❌ Error finding application: {e}")
        return False
    
    # Create test client
    client = Client()
    
    # Force login as admin
    client.force_login(admin_user)
    print("✅ Force logged in as admin")
    
    # Test dashboard to get CSRF token
    response = client.get(reverse('dashboard'))
    print(f"Dashboard response status: {response.status_code}")
    
    if response.status_code == 200:
        print("✅ Dashboard loads successfully")
        
        # Check if CSRF token is in the response
        content = response.content.decode('utf-8')
        if 'csrfmiddlewaretoken' in content:
            print("✅ CSRF token found in dashboard HTML")
            
            # Extract CSRF token from HTML
            import re
            csrf_match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', content)
            if csrf_match:
                csrf_token = csrf_match.group(1)
                print(f"✅ Extracted CSRF token: {csrf_token[:20]}...")
            else:
                print("❌ Could not extract CSRF token from HTML")
                return False
        else:
            print("❌ CSRF token not found in dashboard HTML")
            return False
        
        # Test approve with CSRF token
        approve_url = reverse('approve_host_application', args=[application.id])
        print(f"\nTesting approve URL: {approve_url}")
        
        # Make AJAX request with CSRF token
        headers = {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': csrf_token,
        }
        
        response = client.post(approve_url, HTTP_X_REQUESTED_WITH='XMLHttpRequest', **headers)
        print(f"Approve response status: {response.status_code}")
        print(f"Approve response content: {response.content}")
        
        if response.status_code == 200:
            print("✅ Approve endpoint works with CSRF token")
        else:
            print(f"❌ Approve endpoint failed: {response.status_code}")
            return False
        
        # Test approve without CSRF token (should fail)
        print(f"\nTesting approve without CSRF token (should fail)")
        response = client.post(approve_url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        print(f"Approve response status (no CSRF): {response.status_code}")
        
        if response.status_code == 403:
            print("✅ Approve endpoint correctly rejects request without CSRF token")
        else:
            print(f"❌ Approve endpoint should have rejected request without CSRF token")
            return False
        
    else:
        print(f"❌ Dashboard failed to load: {response.status_code}")
        return False
    
    return True

if __name__ == '__main__':
    test_csrf_debug() 