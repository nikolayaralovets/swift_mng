from .settings import OPENSTACK_URL, GNOCCHI_URL, KEYSTONE_USER, KEYSTONE_PASS, KEYSTONE_USER_ID, KEYSTONE_EG, SWIFT_EG, RESELLER_ROLE_ID, PROTECTED_PROJECTS
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
import requests, json
from django.core.exceptions import PermissionDenied
from .forms import DateForm, ProjectForm, SwiftUserForm, ROLE_CHOICES
from django.contrib import messages
from django.http import HttpResponse, HttpResponseRedirect
from .models import Audit
from django.utils import timezone

def get_token(project):
    headers = {'content-type': 'application/json', 'accept': 'application/json'}
    payload_dict = {"auth":{"identity":{"methods":["password"],"password":{"user":{"name":KEYSTONE_USER,"domain":{"name":"Default"},"password":KEYSTONE_PASS}}},"scope":{"project":{"name":project,"domain":{"name":"Default"}}}}}
    payload = json.dumps(payload_dict)
    r = requests.post(OPENSTACK_URL + '/v3/auth/tokens', data = payload, headers=headers)
    body = r.json()
    if r.status_code == 201:
        token = {}
        token['token'] = r.headers['x-subject-token']
        token['project'] = body['token']['project']['id']
        return token
    else:
        raise PermissionDenied

@login_required
def index(request):
    return render(request, 'index.html')

@login_required
def project_list(request):
    token = get_token('admin')
    headers = {'accept':'application/json', 'x-auth-token':token['token']}
    params = {'parent_id': 'default'}
    r = requests.get(OPENSTACK_URL + '/v3/projects', headers=headers, params=params)
    prjson = r.json()
    projects = []
    for p in prjson['projects']:
        item = {'id': p['id'], 'name': p['name'], 'desc': p['description']}
        projects.append(item)
    return render(request, 'project_list.html', {'projects': projects})

@login_required
def project_view(request, pr):
    token = get_token(pr)
    admintoken = get_token('admin')
    headers = {'x-auth-token':token['token']}
    infoheaders = {'x-auth-token':admintoken['token'], 'accept':'application/json'}
    r = requests.head(OPENSTACK_URL + '/v1/AUTH_' + token['project'], headers=headers)
    usedbytes = r.headers['x-account-bytes-used']
    usedgb = round(int(usedbytes) / 1073741824)
    try:
        quotabytes = r.headers['x-account-meta-quota-bytes']
        quotagb = round(int(quotabytes) / 1073741824)
    except:
        quotagb = 'не ограничено'
    prjinfoparams = {'name': pr}
    prjinfo = requests.get(OPENSTACK_URL + '/v3/projects', headers=infoheaders, params=prjinfoparams)
    prjinfojson = prjinfo.json()
    prjid = prjinfojson['projects'][0]['id']
    prjdesc = prjinfojson['projects'][0]['description']
    prjroleparams = {'scope.project.id':prjid,'include_names':'True'}
    prjrolejson = requests.get(OPENSTACK_URL + '/v3/role_assignments', headers=infoheaders, params=prjroleparams)
    prjroledict = prjrolejson.json()
    userlist = []
    for scope in prjroledict['role_assignments']:
        userdetails = requests.get(OPENSTACK_URL + '/v3/users/' + scope['user']['id'], headers=infoheaders)
        userdetailsdict = userdetails.json()
        try:
            userdetailsdict['user']['email']
        except:
            userdetailsdict['user']['email'] = None
        user = {'name':scope['user']['name'],'role':scope['role']['name'],'email':userdetailsdict['user']['email'],'id':scope['user']['id'],'roleid':scope['role']['id']}
        userlist.append(user)
    if request.method == "POST":
        admintoken = get_token('admin')
        headers = {'x-auth-token':admintoken['token'], 'accept':'application/json'}
        r = requests.get(GNOCCHI_URL + '/v1/resource/generic/' + token['project'], headers=headers)
        gnocjson = r.json()
        dateform = DateForm(request.POST)
        startyear = dateform.data['year']
        startmonth = dateform.data['month']
        if startmonth != '12':
            stopmonth = int(startmonth) + 1
            stopyear = startyear
        else:
            stopmonth = '01'
            stopyear = int(startyear) + 1
        start = str(startyear) + '-' + str(startmonth) + '-01T00:00:00'
        stop = str(stopyear) + '-' + str(stopmonth).zfill(2) + '-01T00:00:00'
        params = {"start":start,"stop":stop,"aggregation":"sum","granularity":"86400"}
        try:
            incoming = gnocjson['metrics']['storage.objects.incoming.bytes']
            inc = requests.get(GNOCCHI_URL + '/v1/metric/' + incoming + '/measures', headers=headers, params=params)
            inclist = inc.text
            incbytes = 0
            for val in json.loads(inclist):
                incbytes += int(val[2])
        except: incbytes = 0
        try:
            outgoing = gnocjson['metrics']['storage.objects.outgoing.bytes']
            out = requests.get(GNOCCHI_URL + '/v1/metric/' + outgoing + '/measures', headers=headers, params=params)
            outlist = out.text
            outbytes = 0
            for val in json.loads(outlist):
                outbytes += int(val[2])
        except: outbytes = 0
        totalbytes = incbytes + outbytes
        totalgb = round(totalbytes / 1073741824)
    else:
        dateform = DateForm()
        totalgb = 0
    return render(request, 'project_view.html', {'name': pr, 'usedgb': usedgb, 'quotagb': quotagb, 'dateform': dateform, 'totalgb': totalgb, 'userlist': userlist, 'projectid': prjid, 'prjdesc':prjdesc})

@login_required
def project_add(request):
    if request.method == "POST":
        projectform = ProjectForm(request.POST)
        if projectform.is_valid():
            token = get_token('admin')
            headers = {'content-type':'application/json','accept':'application/json', 'x-auth-token':token['token']}
            headerseg = {'x-auth-token':token['token']}
            true = True
            false = False
            payload_dict = {"project":{"description":projectform.data['desc'],"domain_id":"default","enabled":true,"is_domain":false,"name":projectform.data['name']}}
            payload = json.dumps(payload_dict)
            prjcrt = requests.post(OPENSTACK_URL + '/v3/projects', headers=headers, data=payload)
            prjson = prjcrt.json()
            prjegkeystone = requests.put(OPENSTACK_URL + '/v3/OS-EP-FILTER/endpoint_groups/' + KEYSTONE_EG + '/projects/' + prjson['project']['id'], headers=headerseg)
            prjegswift = requests.put(OPENSTACK_URL + '/v3/OS-EP-FILTER/endpoint_groups/' + SWIFT_EG + '/projects/' + prjson['project']['id'], headers=headerseg)
            if prjcrt.status_code == 201:
                headers = {'x-auth-token':token['token']}
                roleadd = requests.put(OPENSTACK_URL + '/v3/projects/' + prjson['project']['id'] + '/users/' + KEYSTONE_USER_ID + '/roles/' + RESELLER_ROLE_ID, headers=headers)
                if roleadd.status_code == 204:
                    swifttoken = get_token(projectform.data['name'])
                    quotabytes = int(projectform.data['quota']) * 1073741824
                    headers = {'x-auth-token':swifttoken['token'], 'x-account-meta-quota-bytes':str(quotabytes)}
                    setquota = requests.post(OPENSTACK_URL + '/v1/AUTH_' + prjson['project']['id'], headers=headers)
                    if setquota.status_code == 204:
                        audit = Audit()
                        audit.datetime = timezone.now()
                        audit.user = request.user
                        audit.type = "Создание"
                        audit.objtype = "Проект"
                        audit.object = projectform.data['name']
                        audit.details = "Создан проект " + projectform.data['name'] + ". Квота: " + projectform.data['quota'] + " ГБ. Описание: " + projectform.data['desc']
                        audit.save()
                        return redirect('project_view', pr=projectform.data['name'])
                    else:
                        messages.error(request, 'Error. Status code: ' + str(setquota.status_code) + ' ' + str(setquota.text))
                        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
                else:
                    raise PermissionDenied
            else:
                messages.error(request, 'Error ' + str(prjson))
                return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
        else:
            raise PermissionDenied
    else:
        projectform = ProjectForm()
        return render(request, 'project_add.html', {'projectform': projectform})

@login_required
def user_add(request, pr):
    admintoken = get_token('admin')
    infoheaders = {'x-auth-token':admintoken['token'], 'accept':'application/json'}
    prjinfoparams = {'name': pr}
    prjinfo = requests.get(OPENSTACK_URL + '/v3/projects', headers=infoheaders, params=prjinfoparams)
    prjinfojson = prjinfo.json()
    prjid = prjinfojson['projects'][0]['id']
    prjdesc = prjinfojson['projects'][0]['description']
    if request.method == "POST":
        userform = SwiftUserForm(request.POST)
        if userform.is_valid():
            payload_dict = {"user":{"name":userform.data['name'],"password":userform.data['password'],"email":userform.data['email']}}
            payload = json.dumps(payload_dict)
            headers = {'x-auth-token':admintoken['token'], 'accept':'application/json', 'content-type':'application/json'}
            roleheaders = {'x-auth-token':admintoken['token']}
            usrcrt = requests.post(OPENSTACK_URL + '/v3/users', headers=headers, data=payload)
            usrcrt_dict = usrcrt.json()
            if usrcrt.status_code == 201:
                roleadd = requests.put(OPENSTACK_URL + '/v3/projects/' + prjid + '/users/' + usrcrt_dict['user']['id'] + '/roles/' + userform.data['role'], headers=headers)
                if roleadd.status_code != 204:
                    messages.error(request, 'Ошибка добавления роли: ' + str(roleadd.status_code) + '   ' + roleadd.text)
                ecred_dict = {'credential':{'user_id':usrcrt_dict['user']['id'],'type':'ec2','blob':'{"access":"' + usrcrt_dict['user']['name'] + '","secret":"' + userform.data['password'] + '"}','project_id':prjid}}
                ecred_payload = json.dumps(ecred_dict)
                ecred = requests.post(OPENSTACK_URL + '/v3/credentials', headers=headers, data=ecred_payload)
                if ecred.status_code != 201:
                    messages.error(request, 'Ошибка создания учетных данных для S3: ' + str(ecred.status_code) + '   ' + ecred.text)
                audit = Audit()
                audit.datetime = timezone.now()
                audit.user = request.user
                audit.type = "Создание"
                audit.objtype = "Пользователь"
                audit.object = userform.data['name']
                audit.details = "Создан пользователь " + userform.data['name'] + " с ролью " + dict(ROLE_CHOICES)[userform.cleaned_data['role']] + " в проекте " + pr
                audit.save()
                return redirect('project_view', pr=pr)
    token = get_token(pr)
    headers = {'x-auth-token':token['token']}
    r = requests.head(OPENSTACK_URL + '/v1/AUTH_' + token['project'], headers=headers)
    usedbytes = r.headers['x-account-bytes-used']
    usedgb = round(int(usedbytes) / 1073741824)
    try:
        quotabytes = r.headers['x-account-meta-quota-bytes']
        quotagb = round(int(quotabytes) / 1073741824)
    except:
        quotagb = 'не ограничено'
    prjroleparams = {'scope.project.id':prjid,'include_names':'True'}
    prjrolejson = requests.get(OPENSTACK_URL + '/v3/role_assignments', headers=infoheaders, params=prjroleparams)
    prjroledict = prjrolejson.json()
    userlist = []
    for scope in prjroledict['role_assignments']:
        userdetails = requests.get(OPENSTACK_URL + '/v3/users/' + scope['user']['id'], headers=infoheaders)
        userdetailsdict = userdetails.json()
        try:
            userdetailsdict['user']['email']
        except:
            userdetailsdict['user']['email'] = None
        user = {'name':scope['user']['name'],'role':scope['role']['name'],'email':userdetailsdict['user']['email'],'id':scope['user']['id']}
        userlist.append(user)
    userform = SwiftUserForm()
    totalgb = 0
    return render(request, 'user_add.html', {'name': pr, 'usedgb': usedgb, 'quotagb': quotagb, 'prjdesc':prjdesc, 'userlist': userlist, 'userform': userform})

@login_required
def user_delete(request, usr):
    if usr != KEYSTONE_USER_ID:
        admintoken = get_token('admin')
        headers = {'x-auth-token':admintoken['token']}
        user = requests.get(OPENSTACK_URL + '/v3/users/' + usr, headers=headers)
        user_dict = user.json()
        usrdel = requests.delete(OPENSTACK_URL + '/v3/users/' + usr, headers=headers)
        if usrdel.status_code == 204:
            audit = Audit()
            audit.datetime = timezone.now()
            audit.user = request.user
            audit.type = "Удаление"
            audit.objtype = "Пользователь"
            audit.object = user_dict['user']['name']
            audit.details = "Удален пользователь " + user_dict['user']['name']
            audit.save()
            messages.success(request, 'Пользователь удален')
            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
        else:
            messages.error(request, 'Ошибка: ' + str(usrdel.status_code) + '   ' + usrdel.text)
            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
    else:
        messages.error(request, 'Ошибка: Удаление этого пользователя запрещено!')
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

@login_required
def project_delete(request, prjid):
    if prjid not in PROTECTED_PROJECTS:
        admintoken = get_token('admin')
        headers = {'x-auth-token':admintoken['token'], 'accept':'application\json'}
        prjinfo = requests.get(OPENSTACK_URL + '/v3/projects/' + prjid, headers=headers)
        prjinfodict = prjinfo.json()
        swifttoken = get_token(prjinfodict['project']['name'])
        headers = {'x-auth-token':swifttoken['token']}
        accountdel = requests.delete(OPENSTACK_URL + '/v1/AUTH_' + prjid, headers=headers)
        headers = {'x-auth-token':admintoken['token']}
        prjdel = requests.delete(OPENSTACK_URL + '/v3/projects/' + prjid, headers=headers)
        if prjdel.status_code == 204:
            audit = Audit()
            audit.datetime = timezone.now()
            audit.user = request.user
            audit.type = "Удаление"
            audit.objtype = "Проект"
            audit.object = prjinfodict['project']['name']
            audit.details = "Удален проект " + prjinfodict['project']['name']
            audit.save()
            messages.success(request, 'Проект удален')
            return redirect('project_list')
        else:
            messages.error(request, 'Ошибка: ' + str(prjdel.status_code) + '   ' + prjdel.text)
            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
    else:
        messages.error(request, 'Удаление этого проекта запрещено!')
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

@login_required
def user_unassign(request, prjid, usrid, roleid):
    if usrid != KEYSTONE_USER_ID:
        admintoken = get_token('admin')
        headers = {'x-auth-token':admintoken['token']}
        user = requests.get(OPENSTACK_URL + '/v3/users/' + usrid, headers=headers)
        project = requests.get(OPENSTACK_URL + '/v3/projects/' + prjid, headers=headers)
        userunassign = requests.delete(OPENSTACK_URL + '/v3/projects/' + prjid + '/users/' + usrid + '/roles/' + roleid, headers=headers)
        if userunassign.status_code == 204:
            user_dict = user.json()
            project_dict = project.json()
            audit = Audit()
            audit.datetime = timezone.now()
            audit.user = request.user
            audit.type = "Изменение"
            audit.objtype = "Пользователь"
            audit.object = user_dict['user']['name']
            audit.details = "Отозвана роль " + dict(ROLE_CHOICES)[roleid] + " у пользователя " + user_dict['user']['name'] + " в проекте " + project_dict['project']['name']
            audit.save()
            messages.success(request, 'Роль пользователя в проекте снята')
            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
        else:
            messages.error(request, 'Ошибка: ' + str(userunassign.status_code) + '   ' + userunassign.text)
            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
    else:
        messages.error(request, 'Ошибка: Нельзя снять роль администратора!')
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

@login_required
def user_edit(request, pr, usrid):
    admintoken = get_token('admin')
    headers = {'x-auth-token':admintoken['token'], 'accept':'application/json'}
    prjinfoparams = {'name': pr}
    prjinfo = requests.get(OPENSTACK_URL + '/v3/projects', headers=headers, params=prjinfoparams)
    prjinfojson = prjinfo.json()
    usrinfo = requests.get(OPENSTACK_URL + '/v3/users/' + usrid, headers=headers)
    usrinfo_dict = usrinfo.json()
    prjid = prjinfojson['projects'][0]['id']
    if request.method == "POST":
        userform = SwiftUserForm(request.POST)
        if userform.is_valid():
            if bool(userform.data.get('password', False)) == True:
                payload_dict = {'user':{'name':userform.data['name'],'email':userform.data['email'],'password':userform.data['password']}}
                payload = json.dumps(payload_dict)
                headers = {'x-auth-token':admintoken['token'], 'content-type':'application/json', 'accept':'application/json'}
                credparams = {'user_id':usrid,'type':'ec2'}
                useredit = requests.patch(OPENSTACK_URL + '/v3/users/' + usrid, headers=headers, data=payload)
                roleadd = requests.put(OPENSTACK_URL + '/v3/projects/' + prjid + '/users/' + usrid + '/roles/' + userform.data['role'], headers=headers)
                credget = requests.get(OPENSTACK_URL + '/v3/credentials', headers=headers, params=credparams)
                if credget.status_code == 200:
                    creddict = credget.json()
                    ecred_dict = {'credential':{'user_id':usrid,'type':'ec2','blob':'{"access":"' + userform.data['name'] + '","secret":"' + userform.data['password'] + '"}','project_id':prjid}}
                    ecred_payload = json.dumps(ecred_dict)
                    try:
                      credid = creddict['credentials'][0]['id']
                      crededit = requests.patch(OPENSTACK_URL + '/v3/credentials/' + credid, headers=headers, data=ecred_payload)
                    except:
                      crededit = requests.post(OPENSTACK_URL + '/v3/credentials', headers=headers, data=ecred_payload)
                    if crededit.status_code not in (200, 201):
                        messages.error(request, 'Ошибка: ' + str(crededit.status_code) + '   ' + crededit.text)
                else: messages.error(request, 'Ошибка: ' + str(credget.status_code) + '   ' + credget.text)
            else:
                payload_dict = {'user':{'name':userform.data['name'],'email':userform.data['email']}}
                payload = json.dumps(payload_dict)
                headers = {'x-auth-token':admintoken['token'], 'content-type':'application/json', 'accept':'application/json'}
                credparams = {'user_id':usrid,'type':'ec2'}
                useredit = requests.patch(OPENSTACK_URL + '/v3/users/' + usrid, headers=headers, data=payload)
                roleadd = requests.put(OPENSTACK_URL + '/v3/projects/' + prjid + '/users/' + usrid + '/roles/' + userform.data['role'], headers=headers)
                credget = requests.get(OPENSTACK_URL + '/v3/credentials', headers=headers, params=credparams)
                if credget.status_code == 200:
                    creddict = credget.json()
                    credid = creddict['credentials'][0]['id']
                    credblob = creddict['credentials'][0]['blob']
                    credblobdict = json.loads(credblob)
                    ecred_dict = {'credential':{'user_id':usrid,'type':'ec2','blob':'{"access":"' + userform.data['name'] + '","secret":"' + credblobdict['secret'] + '"}','project_id':prjid}}
                    ecred_payload = json.dumps(ecred_dict)
                    crededit = requests.patch(OPENSTACK_URL + '/v3/credentials/' + credid, headers=headers, data=ecred_payload)
                    if crededit.status_code != 200:
                        messages.error(request, 'Ошибка: ' + str(crededit.status_code) + '   ' + crededit.text)
                else: messages.error(request, 'Ошибка: ' + str(credget.status_code) + '   ' + credget.text)
            if useredit.status_code == 200:
                audit = Audit()
                audit.datetime = timezone.now()
                audit.user = request.user
                audit.type = "Изменение"
                audit.objtype = "Пользователь"
                audit.object = usrinfo_dict['user']['name']
                if bool(userform.data.get('password', False)) == True:
                    audit.details = "Имя пользователя: " + userform.data['name'] + ". E-Mail: " + userform.data['email'] + ". Пароль изменен"
                else:
                    audit.details = "Имя пользователя: " + userform.data['name'] + ". E-Mail: " + userform.data['email'] + ". Пароль не изменен"
                audit.save()
                messages.success(request, 'Пользователь изменен')
                return redirect('project_view', pr=pr)
            else:
                messages.error(request, 'Ошибка: ' + str(useredit.status_code) + '   ' + useredit.text)
                return redirect('project_view', pr=pr)
    else:
        user = requests.get(OPENSTACK_URL + '/v3/users/' + usrid, headers=headers)
        if user.status_code == 200:
            userdict = user.json()
        else:
            messages.error(request, 'Ошибка: ' + str(user.status_code) + '   ' + user.text)
            return redirect('project_view', pr=pr)
        try:
            userdict['user']['email']
        except:
            userdict['user']['email'] = ''
        userform = SwiftUserForm(initial={'name':userdict['user']['name'],'email':userdict['user']['email']})
        infoheaders = {'x-auth-token':admintoken['token'], 'accept':'application/json'}
        prjinfoparams = {'name': pr}
        prjinfo = requests.get(OPENSTACK_URL + '/v3/projects', headers=infoheaders, params=prjinfoparams)
        prjinfojson = prjinfo.json()
        prjid = prjinfojson['projects'][0]['id']
        prjdesc = prjinfojson['projects'][0]['description']
        swifttoken = get_token(pr)
        headers = {'x-auth-token':swifttoken['token']}
        r = requests.head(OPENSTACK_URL + '/v1/AUTH_' + swifttoken['project'], headers=headers)
        usedbytes = r.headers['x-account-bytes-used']
        usedgb = round(int(usedbytes) / 1073741824)
        try:
            quotabytes = r.headers['x-account-meta-quota-bytes']
            quotagb = round(int(quotabytes) / 1073741824)
        except:
            quotagb = 'не ограничено'
        prjroleparams = {'scope.project.id':prjid,'include_names':'True'}
        prjrolejson = requests.get(OPENSTACK_URL + '/v3/role_assignments', headers=infoheaders, params=prjroleparams)
        prjroledict = prjrolejson.json()
        userlist = []
        for scope in prjroledict['role_assignments']:
            userdetails = requests.get(OPENSTACK_URL + '/v3/users/' + scope['user']['id'], headers=infoheaders)
            userdetailsdict = userdetails.json()
            try:
                userdetailsdict['user']['email']
            except:
                userdetailsdict['user']['email'] = None
            user = {'name':scope['user']['name'],'role':scope['role']['name'],'email':userdetailsdict['user']['email'],'id':scope['user']['id']}
            userlist.append(user)
        return render(request, 'user_edit.html', {'name': pr, 'usedgb': usedgb, 'quotagb': quotagb, 'prjdesc':prjdesc, 'userlist': userlist, 'userform': userform})

@login_required
def project_edit(request, pr):
    swifttoken = get_token(pr)
    if request.method == "POST":
        projectform = ProjectForm(request.POST)
        if projectform.is_valid():
            token = get_token('admin')
            headers = {'content-type':'application/json','accept':'application/json', 'x-auth-token':token['token']}
            quotabytes = int(projectform.data['quota']) * 1073741824
            swiftheaders = {'x-auth-token':swifttoken['token'], 'x-account-meta-quota-bytes':str(quotabytes)}
            setquota = requests.post(OPENSTACK_URL + '/v1/AUTH_' + swifttoken['project'], headers=swiftheaders)
            payload_dict = {"project":{"description":projectform.data['desc'],"name":projectform.data['name']}}
            payload = json.dumps(payload_dict)
            prjupd = requests.patch(OPENSTACK_URL + '/v3/projects/' + swifttoken['project'], headers=headers, data=payload)
            prjson = prjupd.json()
            if prjupd.status_code == 200 and setquota.status_code == 204:
                audit = Audit()
                audit.datetime = timezone.now()
                audit.user = request.user
                audit.type = "Изменение"
                audit.objtype = "Проект"
                audit.object = pr
                audit.details = "Название проекта: " + projectform.data['name'] + ". Квота: " + projectform.data['quota'] + "ГБ. Описание: " + projectform.data['desc']
                audit.save()
                messages.success(request, 'Изменения применены')
                return redirect('project_view', pr=prjson['project']['name'])
            else:
                messages.error(request, 'Ошибка: ' + prjupd.text + '   ' + setquota.text)
                return redirect('project_view', pr=pr)
    else:
        admintoken = get_token('admin')
        headers = {'x-auth-token':swifttoken['token']}
        infoheaders = {'x-auth-token':admintoken['token'], 'accept':'application/json'}
        swiftstat = requests.head(OPENSTACK_URL + '/v1/AUTH_' + swifttoken['project'], headers=headers)
        print(swiftstat.headers)
        try:
            quotabytes = swiftstat.headers['x-account-meta-quota-bytes']
            quotagb = round(int(quotabytes) / 1073741824)
        except:
            quotagb = 0
        prjinfoparams = {'name': pr}
        prjinfo = requests.get(OPENSTACK_URL + '/v3/projects', headers=infoheaders, params=prjinfoparams)
        prjinfojson = prjinfo.json()
        prjdesc = prjinfojson['projects'][0]['description']
        projectform = ProjectForm(initial={'name':pr,'quota':quotagb,'desc':prjdesc})
        return render(request, 'project_edit.html', {'projectform': projectform})

@login_required
def audit_log(request):
    audit = Audit.objects.all().order_by('-id')
    return render(request, 'audit_log.html', {'audit': audit})
