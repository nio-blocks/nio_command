import base64
import requests
from enum import Enum
from urllib.parse import urlencode

from nio.properties import IntProperty, ListProperty, \
    SelectProperty, ObjectProperty, PropertyHolder, StringProperty, \
    TimeDeltaProperty, Property, VersionProperty
from nio.block.base import Block
from nio.signal.base import Signal
from nio.modules.scheduler import Job

from .oauth2_mixin.oauth2_base import OAuth2Exception
from .oauth2_mixin.oauth2_service import OAuth2ServiceAccount


class SecurityMethod(Enum):
    NONE = 'none'
    BASIC = 'basic'
    OAUTH = 'oauth'


class URLParameter(PropertyHolder):
    prop_name = Property(title="Property Name")
    prop_value = Property(title="Property Value")


class BasicAuthCreds(PropertyHolder):
    username = StringProperty(title='Username', default='')
    password = StringProperty(title='Password', default='')


class NioCommand(OAuth2ServiceAccount, Block):

    version = VersionProperty("0.1.1")
    params = ListProperty(URLParameter,
                          title="Command Parameters",
                          default=[])
    host = StringProperty(title="n.io Host", default="[[NIOHOST]]")
    port = IntProperty(title="n.io Port", default="[[NIOPORT]]")
    service_name = Property(title="Service Name", default='')
    block_name = Property(title="Block Name (optional)", default='')
    command_name = Property(title="Command Name", default='')
    security_method = SelectProperty(SecurityMethod,
                                     default=SecurityMethod.BASIC,
                                     title='Security Method')
    basic_auth_creds = ObjectProperty(BasicAuthCreds,
                                      title='Credentials (BasicAuth)')

    # We should periodically re-authenticate with Google, this is the interval
    # to do so.
    # Ideally, we use the expiry time in the OAuth token that we get back, but
    # that will require a non-backwards compatible change to the OAuth2 mixin,
    # so for now, having an extra non-visible property will have to do
    reauth_interval = TimeDeltaProperty(
        title="Reauthenticate Interval",
        visible=False,
        default={'seconds': 2400})  # Default to 40 mins

    def __init__(self):
        super().__init__()
        self._access_token = None
        self._reauth_job = None

    def configure(self, context):
        super().configure(context)
        if self.security_method() == SecurityMethod.OAUTH:
            self._init_access_token()

    def process_signals(self, signals):
        output_sigs = []
        for signal in signals:
            try:
                url, headers = self._get_url(signal)
                if url:
                    resp = requests.get(url, headers=headers)
                    sigs = self._process_response(resp)
                    output_sigs.extend(sigs)
            except Exception:
                self.logger.exception('Failed to process signals')
        if output_sigs:
            self.notify_signals(output_sigs)

    def _process_response(self, resp):
        status = resp.status_code
        if status != 200:
            self.logger.error(
                "Status {0} returned while requesting : {1}".format(
                    status, resp)
            )
        try:
            data = resp.json()
        except:
            data = resp.text
        sigs = self._build_signals(data)
        return sigs

    def _build_signals(self, data):
        sigs = []
        if isinstance(data, dict):
            sigs.append(Signal(data))
        elif isinstance(data, list):
            for d in data:
                sigs.extend(self._build_signals(d))
        else:
            sigs.append(Signal({'resp': data}))
        return sigs

    def _init_access_token(self):
        try:
            self._access_token = self.get_access_token('openid email')
            self.logger.debug("Obtained access token: {}".format(
                self._access_token))

            if self._reauth_job:
                self._reauth_job.cancel()

            # Remember to reauthenticate at a certain point if it's configured
            if self.reauth_interval().total_seconds() > 0:
                self._reauth_job = Job(
                    self._init_access_token, self.reauth_interval(), False)

        except OAuth2Exception:
            self.logger.exception('Error obtaining access token')
            self._access_token = None

    def _get_params(self, signal):
        """ Return a dictionary of any configured URL parameters """
        params = dict()
        for param in self.params():
            try:
                params[param.prop_name(signal)] = param.prop_value(signal)
            except Exception:
                self.logger.exception('Failed to evaluate command params')
        return params

    def _get_url(self, signal):
        try:
            service = self.service_name(signal)
            block = self.block_name(signal)
            command = self.command_name(signal)
        except Exception:
            self.logger.exception('Failed to evaluate command definition')
            return None, None
        if not service or not command:
            self.logger.error(
                '`Service Name` and `Command Name` are required parameters')
            return None, None
        if not block:
            url = "http://{}:{}/services/{}/{}?{}".format(
                self.host(),
                self.port(),
                service,
                command,
                urlencode(self._get_params(signal)))
        else:
            url = "http://{}:{}/services/{}/{}/{}?{}".format(
                self.host(),
                self.port(),
                service,
                block,
                command,
                urlencode(self._get_params(signal)))
        headers = self._get_headers()
        self.logger.debug('Commanding: {} {}'.format(url, headers))
        return url, headers

    def _get_headers(self):
        headers = {"Content-Type": "application/json"}
        if self.security_method() == SecurityMethod.OAUTH:
            headers.update(self.get_access_token_headers())
        if self.security_method() == SecurityMethod.BASIC:
            user = '{}:{}'.format(self.basic_auth_creds().username(),
                                  self.basic_auth_creds().password())
            b64 = base64.b64encode(user.encode('ascii')).decode('ascii')
            headers.update({'Authorization': 'Basic {}'.format(b64)})
        return headers
