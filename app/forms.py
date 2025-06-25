from django import forms
from .models import HostApplication, UserProfile, Property, PropertyImage
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm

class HostApplicationForm(forms.ModelForm):
    class Meta:
        model = HostApplication
        fields = ['business_name', 'business_address', 'business_phone', 'identity_document', 'description']
        widgets = {
            'business_name': forms.TextInput(attrs={'class': 'form-control'}),
            'business_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'business_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'identity_document': forms.FileInput(attrs={'class': 'form-control'})
        }
        labels = {
            'business_name': 'Business Name',
            'business_address': 'Business Address',
            'business_phone': 'Business Phone',
            'identity_document': 'Identity Document (PDF, Image)',
            'description': 'Tell us about your hosting experience'
        }
        help_texts = {
            'identity_document': 'Please upload a valid ID document (passport, driver\'s license, etc.)',
            'description': 'Include information about your properties and hosting experience'
        }

class PropertyCreationForm(forms.ModelForm):
    # Additional fields for the become host flow
    photos = forms.FileField(
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'}),
        help_text='Select multiple images for your property',
        required=True
    )
    
    class Meta:
        model = Property
        fields = [
            'title', 'description', 'property_type', 'space_type', 'location',
            'price_per_night', 'bedrooms', 'bathrooms', 'beds', 'max_guests',
            'cleaning_fee', 'service_fee', 'highlights'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Cozy apartment in city center'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe your property, amenities, and what makes it special...'
            }),
            'property_type': forms.Select(attrs={'class': 'form-control'}),
            'space_type': forms.Select(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Full address including city and country'
            }),
            'price_per_night': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '150',
                'step': '0.01'
            }),
            'bedrooms': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'bathrooms': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'beds': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'max_guests': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'cleaning_fee': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '50',
                'step': '0.01'
            }),
            'service_fee': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '30',
                'step': '0.01'
            }),
            'highlights': forms.HiddenInput(),
        }

class ProfileForm(forms.ModelForm):
    first_name = forms.CharField(
        max_length=30, required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'})
    )
    last_name = forms.CharField(
        max_length=30, required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'})
    )
    
    class Meta:
        model = UserProfile
        fields = [
            'avatar', 'phone_number', 'bio', 'date_of_birth', 'address', 
            'city', 'country', 'language', 'currency', 'email_notifications', 
            'sms_notifications', 'marketing_emails'
        ]
        widgets = {
            'bio': forms.Textarea(attrs={
                'rows': 4, 
                'class': 'form-control', 
                'placeholder': 'Tell us a bit about yourself'
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Phone Number'
            }),
            'avatar': forms.FileInput(attrs={
                'class': 'form-control', 
                'accept': 'image/*'
            }),
            'date_of_birth': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Full address'
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'City'
            }),
            'country': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Country'
            }),
            'language': forms.Select(choices=[
                ('English', 'English'),
                ('French', 'French'),
                ('Spanish', 'Spanish'),
                ('Arabic', 'Arabic'),
                ('German', 'German'),
                ('Other', 'Other'),
            ], attrs={'class': 'form-control'}),
            'currency': forms.Select(choices=[
                ('USD', 'USD'),
                ('EUR', 'EUR'),
                ('GBP', 'GBP'),
                ('MAD', 'MAD'),
                ('CAD', 'CAD'),
            ], attrs={'class': 'form-control'}),
            'email_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sms_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'marketing_emails': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['email'].initial = self.instance.user.email
            
    def save(self, commit=True):
        profile = super().save(commit=False)
        if commit:
            # Save user info
            user = profile.user
            user.first_name = self.cleaned_data['first_name']
            user.last_name = self.cleaned_data['last_name']
            user.email = self.cleaned_data['email']
            user.save()
            profile.save()
        return profile 

class RegistrationForm(UserCreationForm):
    first_name = forms.CharField(
        max_length=30, required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'})
    )
    last_name = forms.CharField(
        max_length=30, required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'})
    )
    avatar = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'})
    )

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'avatar', 'password1', 'password2')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            avatar = self.cleaned_data.get('avatar')
            if avatar:
                profile = user.userprofile
                profile.avatar = avatar
                profile.save()
        return user