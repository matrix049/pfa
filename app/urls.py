from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.home, name='home'),
    path('properties/', views.properties, name='properties'),
    path('property/<int:pk>/', views.property_detail, name='property_detail'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('login/', views.login_view, name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
    path('register/', views.register, name='register'),
    path('property/<int:pk>/book/', views.create_booking, name='create_booking'),
    path('booking/<int:pk>/cancel/', views.cancel_booking, name='cancel_booking'),
    path('property/create/', views.create_listing, name='create_listing'),
    path('property/<int:pk>/edit/', views.edit_listing, name='edit_listing'),
    path('property/<int:pk>/delete/', views.delete_listing, name='delete_listing'),
    path('property/<int:pk>/bookings/', views.property_bookings, name='property_bookings'),
    path('review/<int:pk>/edit/', views.edit_review, name='edit_review'),
    path('review/<int:pk>/delete/', views.delete_review, name='delete_review'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('password/change/', views.change_password, name='change_password'),
    path('become-host/', views.become_host, name='become_host'),
    path('create-listing/', views.create_listing, name='create_listing'),
    path('terms/', views.terms, name='terms'),
    path('privacy/', views.privacy, name='privacy'),
    path('posts/create/', views.create_post, name='create_post'),
    path('manage/posts/', views.manage_posts, name='manage_posts'),
    path('manage/posts/<int:post_id>/approve/', views.approve_post, name='approve_post'),
    path('manage/posts/<int:post_id>/decline/', views.decline_post, name='decline_post'),
    path('manage-users/', views.manage_users, name='manage_users'),
    path('user-admin/edit-user/<int:user_id>/', views.edit_user, name='edit_user'),
    path('user-admin/delete-user/<int:user_id>/', views.delete_user, name='delete_user'),
    path('user-admin/toggle-user-status/<int:user_id>/', views.toggle_user_status, name='toggle_user_status'),
    path('user-admin/bulk-action/', views.bulk_action, name='bulk_action'),
    path('booking/success/', views.booking_success, name='booking_success'),
    path('wishlist/add/<int:property_id>/', views.add_to_wishlist, name='add_to_wishlist'),
    path('wishlist/remove/<int:property_id>/', views.remove_from_wishlist, name='remove_from_wishlist'),
]
