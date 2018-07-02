# by luffycity.com

from stark.service.stark import site,DeFaultConfigClass

from .models import *
site.register(User)
site.register(Role)


class PerConfig(DeFaultConfigClass):
    list_display = ["id","title","url","group","action"]
site.register(Permission,PerConfig)
site.register(PermissionGroup)