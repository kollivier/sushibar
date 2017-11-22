import gspread
import httplib2
import json
import requests

from django.conf import settings
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseNotFound
from oauth2client.service_account import ServiceAccountCredentials
from rest_framework.views import APIView

GOOGLE_QA_TEMPLATE_ID = "11Wxms1ZcAI_stQ1L0w1G2vC9shPDf67u1VIERnz93YM"
EMAIL = "jordan@learningequality.org" # TODO: Insert your email here to give yourself access

def get_credentials():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    return ServiceAccountCredentials.from_json_keyfile_name(settings.GOOGLE_AUTH_JSON, scope)

class GoogleClient():
    def __init__(self, *args, **kwargs):
        credentials = get_credentials()
        self.client = gspread.authorize(credentials)

    def create(self, title):
        """ create: creates a spreadsheet with the given title
            Args: title (str) Title of spreadsheet
            Returns: Spreadsheet (see https://github.com/burnash/gspread/blob/master/gspread/models.py#L77)
        """
        spreadsheet = self.client.create(title)
        spreadsheet.share(self.client.auth._service_account_email, perm_type='user', role='owner')
        spreadsheet.share(EMAIL, perm_type='user', role='writer')
        self.client.insert_permission(spreadsheet._id, None, perm_type='anyone', role='reader')

        return spreadsheet

    def get(self, spreadsheet_id):
        """ get: returns spreadsheet matching id
            Args: spreadsheet_id (str) ID of spreadsheet
            Returns: Spreadsheet (see https://github.com/burnash/gspread/blob/master/gspread/models.py#L77)
        """
        return self.client.open_by_key(spreadsheet_id)

    def copy(self, template, target):
        """ copy: copies contents of template spreadsheet to target spreadsheet
            Args:
                template (Spreadsheet) Spreadsheet to copy from
                target (Spreadsheet) Spreadsheet to copy to
            Returns: None
        """

        # TODO: Use https://github.com/burnash/gspread to copy values from template to target
        # Extra reference: https://www.twilio.com/blog/2017/02/an-easy-way-to-read-and-write-to-a-google-spreadsheet-in-python.html

        pass


def generate_qa_sheet(sheet_name, qa_sheet_id=None):
    """ generate_qa_sheet: creates qa sheet copy
        Args:
            sheet_name (str) Title of QA sheet
            qa_sheet_id (str) QA sheet id if it already exists (leaving this in for testing purposes for now)
        Returns: generated spreadsheet id
    """
    client = GoogleClient()                         # Open Google client to read from
    if qa_sheet_id:
        target = client.get(qa_sheet_id)            # Get QA sheet if it exists
    else:
        target = client.create(sheet_name)          # Create new template with channel name + QA
    template = client.get(GOOGLE_QA_TEMPLATE_ID)    # Load template spreadsheet
    client.copy(template, target)                   # Copy template into spreadsheet
    return target._id
