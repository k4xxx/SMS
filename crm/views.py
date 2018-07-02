from django.shortcuts import render
from rbac import models
from django.views import View
from rbac.service.perssions import initial_session

# Create your views here.
def login(request):
    if request.method == 'POST':
        name = request.POST.get('username')
        pwd = request.POST.get('password')
        user = models.User.objects.filter(name=name,pwd=pwd).first()
        if user:
            request.session['user_id'] = user.pk

            # 注册权限到session中
            initial_session(user, request)

            return render(request,'admin.html')

    return render(request,'login.html')