from django.conf import settings

class MobileTemplatesMiddleware(object):
    """Determines which set of templates to use for a mobile site"""

    ORIG_TEMPLATE_DIRS = settings.TEMPLATE_DIRS

    def process_request(self, request):
        ua_string = request.META['HTTP_USER_AGENT'].lower()
        if 'ipad' in ua_string or 'iphone' in ua_string or 'android' in ua_string:	# FIXME Use list file
            settings.TEMPLATE_DIRS = settings.MOBILE_TEMPLATE_DIRS + self.ORIG_TEMPLATE_DIRS
            request.mobile=True
        else:
            settings.TEMPLATE_DIRS = self.ORIG_TEMPLATE_DIRS
            request.mobile=False

