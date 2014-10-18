from decimal import Decimal
import sys

from django.http import HttpResponse
from django.utils import simplejson
from django.core.mail import mail_admins
from django.utils.encoding import force_unicode
from django.utils.functional import Promise
from django.utils.translation import ugettext as _
from django.utils.cache import add_never_cache_headers
from django.views.generic.base import TemplateView


class DTEncoder(simplejson.JSONEncoder):
	"""Encodes django's lazy i18n strings and Decimals
	"""
	def default(self, obj):
		if isinstance(obj, Promise):
			return force_unicode(obj)
		elif isinstance(obj, Decimal):
			return force_unicode(obj)
		return simplejson.JSONEncoder.default(self, obj)


class JSONResponseMixin(object):
	is_clean = False

	def render_to_response(self, context):
		""" Returns a JSON response containing 'context' as payload
		"""
		return self.get_json_response(context)

	def get_json_response(self, content, **httpresponse_kwargs):
		""" Construct an `HttpResponse` object.
		"""
		response = HttpResponse(content,
							content_type='application/json',
							**httpresponse_kwargs)
		add_never_cache_headers(response)
		return response

	def post(self, *args, **kwargs):
		return self.get(*args, **kwargs)

	def get(self, request, *args, **kwargs):
		self.request = request
		response = None

		try:
			func_val = self.get_context_data(**kwargs)
			if not self.is_clean:
				assert isinstance(func_val, dict)
				response = dict(func_val)
				if 'result' not in response:
					response['result'] = 'ok'
			else:
				response = func_val
		except KeyboardInterrupt:
			# Allow keyboard interrupts through for debugging.
			raise
		except Exception as e:
			# Mail the admins with the error
			exc_info = sys.exc_info()
			subject = 'JSON view error: %s' % request.path
			try:
				request_repr = repr(request)
			except Exception as exc:
				request_repr = 'Request repr() unavailable'
			import traceback
			message = 'Traceback:\n%s\n\nRequest:\n%s' % (
				'\n'.join(traceback.format_exception(*exc_info)),
				request_repr,
			)
			mail_admins(subject, message, fail_silently=True)

			# Come what may, we're returning JSON.
			if hasattr(e, 'message'):
				msg = e.message
				msg += str(e)
			else:
				msg = _('Internal error') + ': ' + str(e)
			response = {'result': 'error',
						'text': msg}

		json = simplejson.dumps(response, cls=DTEncoder)
		return self.render_to_response(json)


class JSONResponseView(JSONResponseMixin, TemplateView):
	pass
