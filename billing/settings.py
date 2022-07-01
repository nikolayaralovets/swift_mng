# Адрес кластера в виде https://myswift.com
OPENSTACK_URL = 'https://myswift.com'
# Параметры административной учетной записи
KEYSTONE_USER = 'admin'
KEYSTONE_PASS = 'adminpass'
KEYSTONE_USER_ID = 'admin_uuid'
# ID Endpoint groups, в которые будет добавлен созданный проект
SWIFT_EG = 'eg_uuid'
KEYSTONE_EG = 'eg_uuid'
# ID ролей в Keystone
MEMBER_ROLE_ID = 'role_uuid'
OPERATOR_ROLE_ID = 'role_uuid'
RESELLER_ROLE_ID = 'role_uuid'
# Проекты, защищенные от удаления через Веб интерфейс
PROTECTED_PROJECTS = [
'project_uuid',
'project_uuid'
]
