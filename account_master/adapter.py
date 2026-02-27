from allauth.account.adapter import DefaultAccountAdapter
from ipware import get_client_ip

class CustomAccountAdapter(DefaultAccountAdapter):
    def get_client_ip(self, request):
        ip, _ = get_client_ip(request)
        return ip
