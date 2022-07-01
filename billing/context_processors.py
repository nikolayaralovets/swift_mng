def show_user(request):
    if request.user.is_authenticated:
        return {'loggeduser': request.user.username}
    else:
        return {'none':"none"}
