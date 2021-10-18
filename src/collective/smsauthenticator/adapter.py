import logging

from collective.smsauthenticator.helpers import extract_next_url_from_referer
from collective.smsauthenticator.helpers import sign_user_data
from collective.smsauthenticator.userdataschema import IEnhancedUserDataSchema
from plone import api
from plone.app.users.browser.userdatapanel import UserDataPanelAdapter
from Products.CMFPlone.interfaces import IRedirectAfterLogin
from Products.statusmessages import STATUSMESSAGEKEY
from zope.interface import Interface, implementer
from zope.annotation.interfaces import IAnnotations

logger = logging.getLogger(__file__)

class EnhancedUserDataPanelAdapter(UserDataPanelAdapter):
    """
    Adapter for `collective.smsauthenticator.userdataschema.IEnhancedUserDataSchema`.
    """
    schema = IEnhancedUserDataSchema

    # ****************************************************
    # ******* ``enable_two_step_verification`` *******
    # ****************************************************
    def get_enable_two_step_verification(self):
        return self.context.getProperty('enable_two_step_verification', '')

    def set_enable_two_step_verification(self, value):
        return self.context.setMemberProperties({'enable_two_step_verification': value})

    enable_two_step_verification = property(
        get_enable_two_step_verification,
        set_enable_two_step_verification
        )

    # ****************************************************
    # ***************** ``mobile_number`` ****************
    # ****************************************************
    def get_mobile_number(self):
        return self.context.getProperty('mobile_number', '')

    def set_mobile_number(self, value):
        return self.context.setMemberProperties({'mobile_number': value})

    mobile_number = property(
        get_mobile_number,
        set_mobile_number
        )

    # ****************************************************
    # ********** ``two_step_verification_secret`` ****
    # ****************************************************
    def get_two_step_verification_secret(self):
        return self.context.getProperty('two_step_verification_secret', '')

    def set_two_step_verification_secret(self, value):
        return self.context.setMemberProperties({'two_step_verification_secret': value})

    two_step_verification_secret = property(
        get_two_step_verification_secret,
        set_two_step_verification_secret
        )

    # ****************************************************
    # ********** ``mobile_number_reset_token`` ***********
    # ****************************************************
    def get_mobile_number_reset_token(self):
        return self.context.getProperty('mobile_number_reset_token', '')

    def set_mobile_number_reset_token(self, value):
        return self.context.setMemberProperties(
            {'mobile_number_reset_token': value})

    mobile_number_reset_token = property(
        get_mobile_number_reset_token,
        set_mobile_number_reset_token
        )

    # ****************************************************
    # *********** ``mobile_number_reset_code`` ***********
    # ****************************************************
    def get_mobile_number_reset_code(self):
        return self.context.getProperty('mobile_number_reset_code', '')

    def set_mobile_number_reset_code(self, value):
        return self.context.setMemberProperties(
            {'mobile_number_reset_code': value})

    mobile_number_reset_code = property(
        get_mobile_number_reset_code,
        set_mobile_number_reset_code
        )

    # ****************************************************
    # ********* ``authentication_token_valid_until`` *****
    # ****************************************************
    #def get_authentication_token_valid_until(self):
    #    return self.context.getProperty('authentication_token_valid_until', '')
    #
    #def set_authentication_token_valid_until(self, value):
    #    return # Read only
    #
    #authentication_token_valid_until = property(
    #    get_authentication_token_valid_until,
    #    set_authentication_token_valid_until
    #    )

    # ****************************************************
    # ******** ``mobile_number_authentication_code`` *****
    # ****************************************************
    def get_mobile_number_authentication_code(self):
        return self.context.getProperty('mobile_number_authentication_code', '')

    def set_mobile_number_authentication_code(self, value):
        return # Read only

    mobile_number_authentication_code = property(
        get_mobile_number_authentication_code,
        set_mobile_number_authentication_code
        )

    # ****************************************************
    # ******** ``ips`` *****
    # ****************************************************
    def get_ips(self):
        return self.context.getProperty('ips', '')

    def set_ips(self, value):
        return # Read only

    ips = property(
        get_ips,
        set_ips
        )


class ICameFrom(Interface):
    """
    Interface for getting the ``came_from`` URL.
    """


@implementer(ICameFrom)
class CameFromAdapter(object):
    """
    Came from handling.

    Plone `came_from` field had to be taken out of the login form, so that users always get the
    token validation screen, prior to being redirected to page they came from. The came_from
    is instead extracted from referer and handled in such a way, that Plone functionality stays
    intact.

    In cases your existing package smuggles with `came_from` (for example, you want users first
    to accept terms and conditions prior redirection), you would likely need to define
    a new adapter and make appropriate changes to the ``getCameFrom`` method.

    :example:
    >>> from zope.interface import implements
    >>> from plone import api
    >>> from collective.smsauthenticator.helpers import extract_next_url_from_referer
    >>> from collective.smsauthenticator.adapter import ICameFrom
    >>> 
    >>> class CameFromAdapter(object):
    >>>     implements(ICameFrom)
    >>> 
    >>>     def __init__(self, request):
    >>>         self.request = request
    >>> 
    >>>     def getCameFrom(self):
    >>>         real_referrer = extract_next_url_from_referer(self.request)
    >>>         portal = api.portal.get()
    >>>         if not real_referrer:
    >>>             real_referrer = portal.absolute_url()
    >>>         referrer = "{0}/tac-form/?came_from={1}".format(portal.portal_url(), real_referrer)
    >>>         return referrer
    """

    def __init__(self, request):
        """
        :param request ZPublisher.HTTPRequest:
        """
        self.request = request

    def getCameFrom(self):
        """
        Extracts the ``came_from`` value from the referrer (uses global request).

        :return string:
        """
        return extract_next_url_from_referer(self.request)


@implementer(IRedirectAfterLogin)
class RedirectAfterLoginAdapter(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self, came_from=None, is_initial_login=False):

        # First, we clear the status message set by handleLogin
        annotations = IAnnotations(self.request)
        self.request.cookies[STATUSMESSAGEKEY] = None
        annotations[STATUSMESSAGEKEY] = None

        user = api.user.get_current()
        msg = u"""Enter the login code sent to your mobile number.
If you have somehow lost your mobile number, request a reset by clicking the Reset Mobile Number button. If you didn't receive an SMS message, resend it by clicking the Resend SMS button below."""

        api.portal.show_message(msg, self.request)
        # Redirect to token thing...
        signed_url = sign_user_data(
            request=self.request, user=user, url='@@sms-authenticator-token')

        came_from_adapter = ICameFrom(self.request)
        # Appending possible `came_from`, but give it another name.
        came_from = came_from_adapter.getCameFrom()
        if came_from:
            signed_url = '{0}&next_url={1}'.format(signed_url, came_from)
        return signed_url

