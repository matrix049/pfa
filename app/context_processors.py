def user_language(request):
    """Add user language preference to template context"""
    user_lang = request.session.get('user_language', 'en')
    
    # Get user's language preference from profile if authenticated
    if request.user.is_authenticated:
        try:
            profile_lang = request.user.userprofile.language
            if profile_lang:
                user_lang = profile_lang
        except:
            pass
    
    return {
        'user_language': user_lang,
        'is_french': user_lang == 'fr'
    } 