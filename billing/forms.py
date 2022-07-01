from django import forms
from django.forms import Select
from .settings import MEMBER_ROLE_ID, OPERATOR_ROLE_ID, RESELLER_ROLE_ID
import datetime

now = datetime.datetime.now()
curr_year = now.year
prev_year = now.year - 1

YEAR_CHOICES = [
    (curr_year, curr_year),
    (prev_year, prev_year),
]

MONTH_CHOICES = [
    ('01', 'Январь'),
    ('02', 'Февраль'),
    ('03', 'Март'),
    ('04', 'Апрель'),
    ('05', 'Май'),
    ('06', 'Июнь'),
    ('07', 'Июль'),
    ('08', 'Август'),
    ('09', 'Сентябрь'),
    ('10', 'Октябрь'),
    ('11', 'Ноябрь'),
    ('12', 'Декабрь'),
]

ROLE_CHOICES = [
    (MEMBER_ROLE_ID, 'Member'),
    (OPERATOR_ROLE_ID, 'Operator'),
    (RESELLER_ROLE_ID, 'ResellerAdmin'),
]


class DateForm(forms.Form):
    year = forms.CharField(label='Year', max_length=4, widget=Select(choices = YEAR_CHOICES))
    month = forms.CharField(label='Month', max_length=2, widget=Select(choices = MONTH_CHOICES))

class ProjectForm(forms.Form):
    name = forms.CharField(label='Project name', max_length=32, required=True)
    desc = forms.CharField(label='Project description', max_length=128, required=True)
    quota = forms.IntegerField(label='Project quota, GB', min_value=0, max_value=1048576)

class SwiftUserForm(forms.Form):
    name = forms.CharField(label='User name', max_length=32, required=True)
    role = forms.CharField(label='User role', widget=Select(choices = ROLE_CHOICES))
    email = forms.EmailField(label='User email', max_length=32)
    password = forms.CharField(label='User password', widget=forms.PasswordInput(render_value=True), required=False)
