from django.http import JsonResponse

def debug_meta(request):
    data = {k: v for k, v in request.META.items() if "IP" in k or "ADDR" in k or "FORWARDED" in k}
    return JsonResponse(data)
