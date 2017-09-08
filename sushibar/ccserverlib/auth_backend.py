
from sushibar.users.models import BarUser

from .services import ccserver_authenticate_user



class ContentCurationServerAuthBackend(object):
    """
    This authentication backend uses the content curation server token (`cctoken`)
    instead of a password.

    If the `cctoken` is valid, a new BarUser will be created and returned.
    """
    def authenticate(self, request, username=None, password=None):
        print('in custom CCServer-backed authenticate method...')
        ccemail = username  # signin form's username field is actually an email
        cctoken = password  # signin form's password field is actuall the cctoken

        # Check if BarUser with this `ccemail` and `cctoken` already exists:
        try:
            existing_baruser = BarUser.objects.get(email=ccemail, cctoken=cctoken)
            return existing_baruser

        except BarUser.DoesNotExist:
            # No BarUser exists with this cctoken, let's check if token is valid
            status, data = ccserver_authenticate_user(cctoken, ccemail)
            if status == 'success':
                # We know `cctoken` and `ccemail` provided are valid, create the BarUser
                new_baruser = BarUser.objects.create(
                    username=ccemail,
                    email=ccemail,
                    cctoken=cctoken,
                    is_staff = data.get('is_admin'),
                    first_name = data.get('first_name'),
                    last_name = data.get('last_name'),
                )
                return new_baruser

            elif status == 'failure':
                print('Authentication failed:', data)
                return None

            else:
                raise ValueError('Unrecognized status from ccserver_authenticate_user')

    def get_user(self, user_id):
        try:
            return BarUser.objects.get(pk=user_id)
        except BarUser.DoesNotExist:
            return None
