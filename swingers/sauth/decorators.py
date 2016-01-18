from django.http import HttpResponse


def crossdomain(view):
    def wrapped(request, *args, **kwargs):
        if request.method == "OPTIONS":
            response = HttpResponse()
        else:
            response = view(request, *args, **kwargs)
        if "HTTP_ORIGIN" in request.META:
            origin = request.META["HTTP_ORIGIN"]
            headers = "Content-Type, X-Requested-With"
            response["Access-Control-Allow-Origin"] = origin
            response["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
            response["Access-Control-Allow-Headers"] = headers
            response["Access-Control-Allow-Credentials"] = "true"
        return response
    return wrapped
