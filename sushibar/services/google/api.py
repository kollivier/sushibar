import gspread
import httplib2
import json
import requests

from apiclient import discovery
from django.conf import settings
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseNotFound
from oauth2client.service_account import ServiceAccountCredentials
from rest_framework.views import APIView

GOOGLE_QA_TEMPLATE_ID = settings.GOOGLE_QA_TEMPLATE_ID
TARGET_FOLDER_ID = settings.TARGET_FOLDER_ID

def get_credentials():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    return ServiceAccountCredentials.from_json_keyfile_name(settings.GOOGLE_AUTH_JSON, scope)

class GoogleClient():
    def __init__(self, *args, **kwargs):
        credentials = get_credentials()
        self.client = gspread.authorize(credentials)
        http = credentials.authorize(httplib2.Http())
        self.service = discovery.build('drive', 'v3', http=http)


    def create(self, title, template_id=None):
        """ create: creates a spreadsheet with the given title
            Args: title (str) Title of spreadsheet
            Returns: Spreadsheet (see https://github.com/burnash/gspread/blob/master/gspread/models.py#L77)
        """
        if template_id:
            spreadsheet_data = self.service.files().copy(fileId=template_id, body={'name': title}, supportsTeamDrives=True).execute()
            spreadsheet = self.get(spreadsheet_data['id'])
        else:
            spreadsheet = self.client.create(title)
        spreadsheet.share(self.client.auth._service_account_email, perm_type='user', role='owner')
        self.service.permissions().create(fileId=spreadsheet._id, body={'role': 'writer', 'type': 'anyone'}).execute()

        return spreadsheet

    def get(self, spreadsheet_id):
        """ get: returns spreadsheet matching id
            Args: spreadsheet_id (str) ID of spreadsheet
            Returns: Spreadsheet (see https://github.com/burnash/gspread/blob/master/gspread/models.py#L77)
        """
        return self.client.open_by_key(spreadsheet_id)

    def move(self, spreadsheet, target_folder_id):
        """ move: move sheet with spreadsheet_id to target folder id
            Args:
                spreadsheet_id (Spreadsheet) Spreadsheet id to move
                target_folder_id (str) Folder to move spreadsheet to
            Returns: None
        """
        # Retrieve the existing parents to remove
        file = self.service.files().get(fileId=spreadsheet._id, fields='parents').execute()
        previous_parents = ",".join(file.get('parents') or [])
        # Move the file to the new folder
        file = self.service.files().update(fileId=spreadsheet._id, addParents=target_folder_id, removeParents=previous_parents, fields='id, parents').execute()


def create_qa_sheet(sheet_name):
    """ create_qa_sheet: creates qa sheet copy
        Args:
            sheet_name (str) Title of QA sheet
            qa_sheet_id (str) QA sheet id if it already exists (leaving this in for testing purposes for now)
        Returns: generated spreadsheet id
    """
    client = GoogleClient()                                                # Open Google client to read from
    target = client.create(sheet_name, template_id=GOOGLE_QA_TEMPLATE_ID)  # Create copy of QA sheet
    client.move(target, TARGET_FOLDER_ID)                                  # Move sheet to target

    return target._id
